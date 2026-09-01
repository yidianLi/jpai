"""Persistent job state with idempotent submission and bounded worker execution."""
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from threading import Lock
from uuid import uuid4
from ..database import AiSessionLocal
from ..models.job import AiJob


class JobService:
    _executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="ai-job")
    _lock = Lock()

    @classmethod
    def submit(cls, job_type, payload, owner, idempotency_key, handler, timeout_seconds=900):
        db = AiSessionLocal()
        try:
            existing = db.query(AiJob).filter(AiJob.idempotency_key == idempotency_key).first()
            if existing and existing.status not in {"failed", "cancelled"}:
                return existing
            if existing:
                existing.status, existing.progress, existing.error = "queued", 0, None
                existing.retry_count += 1
                job = existing
            else:
                now = datetime.now()
                job = AiJob(id=f"job-{uuid4().hex}", job_type=job_type, idempotency_key=idempotency_key,
                            status="queued", payload=json.dumps(payload or {}, ensure_ascii=False, default=str),
                            owner_user_id=getattr(owner, "user_id", None), owner_name=getattr(owner, "user_name", None),
                            created_at=now, updated_at=now, timeout_seconds=timeout_seconds)
                db.add(job)
            db.commit(); db.refresh(job)
            cls._executor.submit(cls._run, job.id, handler)
            return job
        finally:
            db.close()

    @classmethod
    def get(cls, job_id, owner=None):
        db = AiSessionLocal()
        try:
            query = db.query(AiJob).filter(AiJob.id == job_id)
            if owner is not None and getattr(owner, "is_admin", 0) != 1:
                query = query.filter(AiJob.owner_user_id == owner.user_id)
            return query.first()
        finally:
            db.close()

    @classmethod
    def cancel(cls, job_id, owner):
        db = AiSessionLocal()
        try:
            query = db.query(AiJob).filter(AiJob.id == job_id)
            if getattr(owner, "is_admin", 0) != 1: query = query.filter(AiJob.owner_user_id == owner.user_id)
            job = query.first()
            if not job or job.status not in {"queued", "running"}: return None
            job.status, job.error, job.updated_at, job.finished_at = "cancelled", "cancelled by user", datetime.now(), datetime.now()
            db.commit(); return job
        finally: db.close()

    @classmethod
    def retry(cls, job_id, owner, handler):
        db = AiSessionLocal()
        try:
            query = db.query(AiJob).filter(AiJob.id == job_id)
            if getattr(owner, "is_admin", 0) != 1: query = query.filter(AiJob.owner_user_id == owner.user_id)
            old = query.first()
            if not old or old.status not in {"failed", "cancelled"}: return None
            key, payload, job_type, timeout = old.idempotency_key, json.loads(old.payload or "{}"), old.job_type, old.timeout_seconds
        finally: db.close()
        return cls.submit(job_type, payload, owner, key, handler, timeout)

    @classmethod
    def payload(cls, job):
        return {"job_id": job.id, "job_type": job.job_type, "status": job.status, "progress": job.progress,
                "result": json.loads(job.result) if job.result else None, "error": job.error,
                "retry_count": job.retry_count, "created_at": job.created_at, "updated_at": job.updated_at}

    @classmethod
    def _run(cls, job_id, handler):
        db = AiSessionLocal()
        try:
            job = db.query(AiJob).filter(AiJob.id == job_id).first()
            if not job or job.status == "cancelled": return
            job.status, job.progress, job.started_at, job.updated_at = "running", 5, datetime.now(), datetime.now(); db.commit()
            payload = json.loads(job.payload or "{}")
        finally: db.close()
        try:
            result = handler(payload)
            db = AiSessionLocal(); job = db.query(AiJob).filter(AiJob.id == job_id).first()
            if job and job.status != "cancelled":
                job.status, job.progress, job.result, job.finished_at, job.updated_at = "succeeded", 100, json.dumps(result, ensure_ascii=False, default=str), datetime.now(), datetime.now(); db.commit()
            db.close()
        except Exception as exc:
            db = AiSessionLocal(); job = db.query(AiJob).filter(AiJob.id == job_id).first()
            if job:
                job.status, job.error, job.finished_at, job.updated_at = "failed", str(exc), datetime.now(), datetime.now(); db.commit()
            db.close()


def report_handler(payload):
    from .report_service import ReportService
    service = ReportService()
    try:
        return service.generate_monthly_report(int(payload["year"]), int(payload["month"]), payload["user_name"])
    finally:
        service.close()
