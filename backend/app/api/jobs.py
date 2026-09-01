from fastapi import APIRouter, Depends, HTTPException
from ..models.dict import AiUser
from ..core.auth import get_current_user
from ..services.job_service import JobService
router = APIRouter()
@router.get("/{job_id}")
def get_job(job_id: str, user: AiUser = Depends(get_current_user)):
    job = JobService.get(job_id, user)
    if not job: raise HTTPException(404, "job not found")
    return JobService.payload(job)
@router.post("/{job_id}/cancel")
def cancel_job(job_id: str, user: AiUser = Depends(get_current_user)):
    job = JobService.cancel(job_id, user)
    if not job: raise HTTPException(409, "job cannot be cancelled")
    return JobService.payload(job)
