from fastapi import APIRouter, Depends, HTTPException
from ..core.auth import require_admin
from ..core.orchestration import orchestration_config

router = APIRouter()


@router.get("/config")
def get_orchestration_config(user=Depends(require_admin)):
    return orchestration_config.collaboration()


@router.get("/workflow/{workflow_id}")
def get_workflow(workflow_id: str, user=Depends(require_admin)):
    try:
        return orchestration_config.workflow(workflow_id)
    except FileNotFoundError:
        raise HTTPException(404, "工作流不存在")


@router.get("/health")
def orchestration_health(user=Depends(require_admin)):
    return orchestration_config.health()


@router.post("/dispatch")
def dispatch_tasks(user=Depends(require_admin)):
    """手动执行一次项目经理巡检，便于验证或补派任务。"""
    return orchestration_config.dispatch_project_manager_tasks()


@router.get("/tasks")
def list_tasks(user=Depends(require_admin)):
    path = orchestration_config.root / "runtime" / "orchestration-tasks.json"
    if not path.exists():
        return []
    import json
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/notifications")
def list_notifications(user=Depends(require_admin)):
    from ..core.notifications import recent_notifications
    return recent_notifications()

@router.get("/jobs/{job_id}")
def job_status(job_id: str, user=Depends(require_admin)):
    """返回指定作业的最近一次状态，供前端轮询。"""
    from ..core.notifications import recent_notifications
    events = [event for event in recent_notifications() if event.get("job_id") == job_id]
    if not events:
        raise HTTPException(404, "作业不存在")
    latest = events[-1]
    return {"job_id": job_id, "status": latest.get("status"), "result": latest.get("result"),
            "error": latest.get("error", ""), "updated_at": latest.get("created_at"), "events": events}


@router.post("/run")
def run_workflow(user=Depends(require_admin)):
    from ..core.orchestrator import run_workflow_sync
    return run_workflow_sync()
