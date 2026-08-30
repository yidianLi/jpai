"""领导驾驶舱接口"""
from fastapi import APIRouter, Depends
from ..models.dict import AiUser
from ..core.auth import get_current_user
from ..services.analysis_service import AnalysisService
from ..services.warning_service import WarningService
from ..services.report_service import ReportService

router = APIRouter()


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
    svc = ReportService()
    data = svc.generate_monthly_report(year, month, user.user_name)
    svc.close()
    return data


@router.get("/reports")
def report_list(type: str = None, page: int = 1, size: int = 20, user: AiUser = Depends(get_current_user)):
    svc = ReportService()
    data = svc.get_report_list(type, page, size)
    svc.close()
    return data
