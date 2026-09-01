"""定时任务调度：数据同步、预警计算、闲置识别"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import logging

logger = logging.getLogger(__name__)
_scheduler = None


def orchestration_health():
    """Validate collaboration configuration on the daily schedule."""
    from .orchestration import orchestration_config
    result = orchestration_config.health()
    if result["ok"]:
        logger.info("orchestration configuration is healthy")
    else:
        logger.error("orchestration configuration errors: %s", result["errors"])


def project_manager_hourly_dispatch():
    """每小时巡检进度并派发下一阶段智能体任务。"""
    from .orchestration import orchestration_config
    from .notifications import notify
    notify("project-manager-hourly-dispatch", "started")
    try:
        from .orchestrator import run_workflow_sync
        result = orchestration_config.dispatch_project_manager_tasks()
        if result.get("created"):
            result["execution"] = run_workflow_sync()
        logger.info("项目经理巡检: %s", result)
        notify("project-manager-hourly-dispatch", "completed", result=result)
        return result
    except Exception as exc:
        logger.exception("项目经理巡检失败: %s", exc)
        notify("project-manager-hourly-dispatch", "failed", error=str(exc))


def sync_all_data():
    """全量数据同步任务"""
    from ..services.sync_service import SyncService
    try:
        service = SyncService()
        service.sync_dictionaries()
        service.sync_assets()
        service.sync_transfers()
        service.sync_check_records()
        service.sync_users()
        logger.info("数据同步完成")
    except Exception as e:
        logger.error(f"数据同步失败: {e}")


def compute_warnings():
    """预警计算任务"""
    from ..services.warning_service import WarningService
    try:
        service = WarningService()
        service.compute_expire_warnings()
        service.compute_idle_warnings()
        service.compute_overdue_warnings()
        logger.info("预警计算完成")
    except Exception as e:
        logger.error(f"预警计算失败: {e}")


def compute_idle_pool():
    """闲置资产池更新"""
    from ..services.idle_service import IdleService
    try:
        service = IdleService()
        service.refresh_idle_pool()
        logger.info("闲置池更新完成")
    except Exception as e:
        logger.error(f"闲置池更新失败: {e}")


def start_scheduler():
    global _scheduler
    if _scheduler:
        return
    _scheduler = BackgroundScheduler(timezone="Asia/Shanghai")
    def notified(job_id, fn):
        def run():
            from .notifications import notify
            notify(job_id, "started")
            try:
                result = fn()
                notify(job_id, "completed", result=result)
                return result
            except Exception as exc:
                notify(job_id, "failed", error=str(exc))
                raise
        return run
    # 每日凌晨2点同步
    _scheduler.add_job(notified("sync_data", sync_all_data), CronTrigger(hour=2, minute=0), id="sync_data")
    # 每日凌晨3点计算预警
    _scheduler.add_job(notified("compute_warnings", compute_warnings), CronTrigger(hour=3, minute=0), id="compute_warnings")
    # 每日凌晨3点半更新闲置池
    _scheduler.add_job(notified("compute_idle", compute_idle_pool), CronTrigger(hour=3, minute=30), id="compute_idle")
    _scheduler.add_job(notified("orchestration_health", orchestration_health), CronTrigger(hour=4, minute=0), id="orchestration_health")
    _scheduler.add_job(project_manager_hourly_dispatch, CronTrigger(hour="*", minute=0), id="project_manager_hourly_dispatch", max_instances=1, coalesce=True)
    _scheduler.start()
    logger.info("定时任务调度器已启动")


def get_scheduler():
    return _scheduler
