"""领导驾驶舱接口"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from pathlib import Path
from ..models.dict import AiUser
from ..models.report import AiReport
from ..core.auth import get_current_user
from ..services.analysis_service import AnalysisService
from ..services.warning_service import WarningService
from ..services.report_service import ReportService
from ..services.report_job_service import ReportJobService
from ..database import get_ai_db
from ..models.asset import AiAsset
from ..models.transfer import AiTransferSuggestion
from ..models.warning import AiWarning
from ..services.lifecycle_service import LifecycleService
from ..core.data_scope import apply_data_scope
from ..core.audit import record as record_audit

router = APIRouter()

@router.get("/action-items")
def action_items(db: Session = Depends(get_ai_db), user: AiUser = Depends(get_current_user)):
    """Permission-scoped action queue used by the dashboard workbench."""
    items = []
    warning_query = db.query(AiWarning).join(AiAsset, AiAsset.asset_id == AiWarning.asset_id)
    warning_query = apply_data_scope(warning_query, user).filter(AiWarning.status == 0)
    warnings = warning_query.order_by(AiWarning.warning_level.asc(), AiWarning.create_time.desc()).limit(10).all()
    for warning in warnings:
        items.append({"id": f"warning-{warning.id}", "category": "warning",
                      "title": warning.warning_content,
                      "priority": "high" if warning.warning_level == 1 else "medium",
                      "amount": None, "link": "/dashboard", "source_id": warning.id})

    query = db.query(AiTransferSuggestion, AiAsset).join(
        AiAsset, AiAsset.asset_id == AiTransferSuggestion.asset_id
    )
    query = apply_data_scope(query, user)
    rows = query.filter(AiTransferSuggestion.status.in_(["pending_receiver", "confirmed"])).order_by(
        AiTransferSuggestion.updated_at.asc()).limit(10).all()
    for suggestion, asset in rows:
        waiting = suggestion.status == "pending_receiver"
        items.append({"id": f"transfer-{suggestion.id}", "category": "transfer",
                      "title": f"{asset.asset_name or asset.barcode or '资产'}待{'接收确认' if waiting else '执行'}",
                      "priority": "high" if waiting else "medium",
                      "amount": float(suggestion.estimated_saving) if suggestion.estimated_saving is not None else None,
                      "link": "/transfer", "source_id": suggestion.id})

    lifecycle = LifecycleService()
    try:
        quality = lifecycle.get_data_quality_report()
    finally:
        lifecycle.close()
    abnormal = quality.get("abnormal", 0)
    if abnormal:
        items.append({"id": "quality-abnormal", "category": "quality",
                      "title": f"{abnormal} 条资产数据质量问题待处理", "priority": "medium",
                      "amount": None, "link": "/lifecycle/quality", "source_id": None})
    order = {"high": 0, "medium": 1, "low": 2}
    items.sort(key=lambda row: order.get(row["priority"], 9))
    return {"total": len(items), "high_count": sum(1 for row in items if row["priority"] == "high"),
            "estimated_saving": round(sum(row["amount"] or 0 for row in items), 2),
            "items": items[:20]}


@router.get("/overview")
def overview(user: AiUser = Depends(get_current_user)):
    svc = AnalysisService()
    data = svc.get_overview()
    svc.close()
    return data


@router.get("/class-distribution")
def class_distribution(user: AiUser = Depends(get_current_user)):
    svc = AnalysisService()
    data = svc.get_class_distribution()
    svc.close()
    return data


@router.get("/state-distribution")
def state_distribution(user: AiUser = Depends(get_current_user)):
    svc = AnalysisService()
    data = svc.get_state_distribution()
    svc.close()
    return data


@router.get("/monthly-trend")
def monthly_trend(months: int = 12, user: AiUser = Depends(get_current_user)):
    svc = AnalysisService()
    data = svc.get_monthly_trend(months)
    svc.close()
    return data


@router.get("/dept-ranking")
def dept_ranking(user: AiUser = Depends(get_current_user)):
    svc = AnalysisService()
    data = svc.get_dept_ranking()
    svc.close()
    return data


@router.get("/warnings")
def warnings(type: str = None, level: int = None, status: int = 0, page: int = 1, size: int = 20, user: AiUser = Depends(get_current_user)):
    svc = WarningService()
    data = svc.get_warning_list(type, level, status, page, size)
    svc.close()
    return data


@router.post("/warnings/{warning_id}/handle")
def handle_warning(warning_id: int, status: int, remark: str = "", user: AiUser = Depends(get_current_user)):
    svc = WarningService()
    data = svc.handle_warning(warning_id, status, remark, user.user_name)
    svc.close()
    return {"message": "处理成功"}


@router.post("/report/generate-monthly")
def generate_monthly_report(year: int, month: int, user: AiUser = Depends(get_current_user)):
    if not 1 <= month <= 12:
        raise HTTPException(422, "month must be between 1 and 12")
    job = ReportJobService.submit(year, month, user.user_name)
    return ReportJobService.payload(job)


@router.get("/report-jobs/{job_id}")
def get_report_job(job_id: str, user: AiUser = Depends(get_current_user)):
    job = ReportJobService.get(job_id, user.user_name)
    if not job:
        raise HTTPException(404, "report job not found")
    return ReportJobService.payload(job)


@router.post("/report-jobs/{job_id}/cancel")
def cancel_report_job(job_id: str, user: AiUser = Depends(get_current_user)):
    job = ReportJobService.cancel(job_id, user.user_name)
    if not job:
        raise HTTPException(409, "only queued report jobs can be cancelled")
    return ReportJobService.payload(job)


@router.post("/report-jobs/{job_id}/retry")
def retry_report_job(job_id: str, user: AiUser = Depends(get_current_user)):
    job = ReportJobService.retry(job_id, user.user_name)
    if not job:
        raise HTTPException(409, "only failed or cancelled report jobs can be retried")
    return ReportJobService.payload(job)


@router.get("/reports")
def report_list(type: str = None, page: int = 1, size: int = 20, user: AiUser = Depends(get_current_user)):
    svc = ReportService()
    data = svc.get_report_list(type, page, size)
    svc.close()
    return data

@router.get("/operational-effectiveness")
def operational_effectiveness(months: int = 12, dept_id: int = None, user: AiUser = Depends(get_current_user)):
    if months < 1 or months > 24 or (dept_id is not None and dept_id < 1):
        raise HTTPException(422, "months must be between 1 and 24 and dept_id must be positive")
    svc = AnalysisService()
    try:
        return svc.get_operational_effectiveness(months, dept_id)
    finally:
        svc.close()

@router.get('/reports/id/{report_id}')
def download_report_by_id(report_id: int, request: Request, db: Session = Depends(get_ai_db), user: AiUser = Depends(get_current_user)):
    report = db.query(AiReport).filter(AiReport.id == report_id).first()
    if not report or (user.is_admin != 1 and report.create_user != user.user_name):
        raise HTTPException(404, '鎶ュ憡涓嶅瓨鍦ㄦ垨鏃犳潈璁块棶')
    safe_name = Path(report.file_path or '').name
    path = Path('reports') / safe_name
    if safe_name != report.file_path or path.suffix.lower() != '.docx' or not path.is_file():
        raise HTTPException(404, 'report file not found')
    if path.stat().st_size > 20 * 1024 * 1024:
        raise HTTPException(413, '鎶ュ憡鏂囦欢瓒呭嚭澶у皬闄愬埗')
    record_audit(db, user, "report.download", f"report:{report_id}", after={"filename": safe_name}, request=request)
    db.commit()
    return FileResponse(path, filename=safe_name, media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')

@router.get('/reports/{filename}')
def download_report(filename: str, user: AiUser = Depends(get_current_user)):
    # Only files generated in the reports directory are downloadable.
    safe_name = Path(filename).name
    path = Path('reports') / safe_name
    if safe_name != filename or not path.is_file():
        raise HTTPException(404, '报告文件不存在')
    return FileResponse(path, filename=safe_name, media_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
