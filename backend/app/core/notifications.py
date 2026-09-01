"""定时任务通知：本地审计日志 + 可选 Webhook。"""
import json
import logging
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[3]


def notify(job_id: str, status: str, result=None, error: str = "") -> dict:
    config_path = ROOT / "config" / "notifications.json"
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    event = {"job_id": job_id, "status": status, "result": result, "error": error, "created_at": datetime.now().isoformat(timespec="seconds")}
    runtime = ROOT / "runtime"
    runtime.mkdir(exist_ok=True)
    log_path = runtime / "notifications.json"
    try:
        history = json.loads(log_path.read_text(encoding="utf-8")) if log_path.exists() else []
    except json.JSONDecodeError:
        history = []
    history.append(event)
    log_path.write_text(json.dumps(history[-int(config.get("retain", 500)):], ensure_ascii=False, indent=2), encoding="utf-8")
    webhook = config.get("webhook_url", "")
    if config.get("enabled", True) and webhook:
        try:
            body = json.dumps({"text": f"AI资产管理定时任务 {job_id}: {status}", "event": event}, ensure_ascii=False).encode("utf-8")
            request = Request(webhook, data=body, headers={"Content-Type": "application/json"}, method="POST")
            with urlopen(request, timeout=float(config.get("timeout_seconds", 10))):
                pass
        except Exception as exc:
            logger.warning("通知 Webhook 发送失败: %s", exc)
    return event


def recent_notifications() -> list[dict]:
    path = ROOT / "runtime" / "notifications.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
