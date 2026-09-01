"""In-process job coordinator for report generation."""
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from threading import Lock
from typing import Any
from uuid import uuid4

from ..core.notifications import notify
from .report_service import ReportService


@dataclass
class ReportJob:
    job_id: str
    year: int
    month: int
    user_name: str
    status: str = "queued"
    result: dict[str, Any] | None = None
    error: str = ""
    created_at: str = ""
    updated_at: str = ""
    future: Future | None = None


class ReportJobService:
    """Coordinates report jobs for the current application process."""

    _executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="report-job")
    _jobs: dict[str, ReportJob] = {}
    _active_periods: dict[tuple[str, int, int], str] = {}
    _lock = Lock()

    @classmethod
    def submit(cls, year: int, month: int, user_name: str) -> ReportJob:
        key = (user_name, year, month)
        with cls._lock:
            existing_id = cls._active_periods.get(key)
            if existing_id and (existing := cls._jobs.get(existing_id)):
                return existing
            now = datetime.now().isoformat(timespec="seconds")
            job = ReportJob(
                job_id=f"report-monthly-{uuid4().hex}", year=year, month=month,
                user_name=user_name, created_at=now, updated_at=now,
            )
            cls._jobs[job.job_id] = job
            cls._active_periods[key] = job.job_id
            notify(job.job_id, "queued", result=cls._payload(job))
            job.future = cls._executor.submit(cls._run, job.job_id)
            return job

    @classmethod
    def get(cls, job_id: str, user_name: str) -> ReportJob | None:
        with cls._lock:
            job = cls._jobs.get(job_id)
            return job if job and job.user_name == user_name else None

    @classmethod
    def cancel(cls, job_id: str, user_name: str) -> ReportJob | None:
        with cls._lock:
            job = cls._jobs.get(job_id)
            if not job or job.user_name != user_name or job.status != "queued" or not job.future or not job.future.cancel():
                return None
            job.status = "cancelled"
            job.updated_at = datetime.now().isoformat(timespec="seconds")
            cls._active_periods.pop((job.user_name, job.year, job.month), None)
            notify(job.job_id, "cancelled", result=cls._payload(job))
            return job

    @classmethod
    def retry(cls, job_id: str, user_name: str) -> ReportJob | None:
        with cls._lock:
            job = cls._jobs.get(job_id)
            if not job or job.user_name != user_name or job.status not in {"failed", "cancelled"}:
                return None
            year, month = job.year, job.month
        return cls.submit(year, month, user_name)

    @classmethod
    def payload(cls, job: ReportJob) -> dict[str, Any]:
        with cls._lock:
            return cls._payload(job)

    @staticmethod
    def _payload(job: ReportJob) -> dict[str, Any]:
        return {
            "job_id": job.job_id, "status": job.status, "year": job.year,
            "month": job.month, "result": job.result, "error": job.error,
            "created_at": job.created_at, "updated_at": job.updated_at,
        }

    @classmethod
    def _run(cls, job_id: str) -> None:
        with cls._lock:
            job = cls._jobs.get(job_id)
            if not job or job.status == "cancelled":
                return
            job.status = "running"
            job.updated_at = datetime.now().isoformat(timespec="seconds")
            notify(job.job_id, "running", result=cls._payload(job))
        try:
            service = ReportService()
            try:
                result = service.generate_monthly_report(job.year, job.month, job.user_name)
            finally:
                service.close()
            with cls._lock:
                job.status = "succeeded"
                job.result = result
                job.updated_at = datetime.now().isoformat(timespec="seconds")
                cls._active_periods.pop((job.user_name, job.year, job.month), None)
                notify(job.job_id, "succeeded", result=cls._payload(job))
        except Exception as exc:
            with cls._lock:
                job.status = "failed"
                job.error = str(exc)
                job.updated_at = datetime.now().isoformat(timespec="seconds")
                cls._active_periods.pop((job.user_name, job.year, job.month), None)
                notify(job.job_id, "failed", result=cls._payload(job), error=job.error)
