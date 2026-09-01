"""Small append-only audit writer shared by API routes."""
import json
from datetime import datetime
from fastapi import Request
from ..models.audit import AiAuditEvent


def record(db, user, action, resource=None, result="success", before=None, after=None, request: Request | None = None):
    headers = request.headers if request else {}
    event = AiAuditEvent(
        actor_user_id=getattr(user, "user_id", None), actor_name=getattr(user, "user_name", None),
        action=action, resource=resource, result=result,
        before_snapshot=json.dumps(before, ensure_ascii=False, default=str) if before is not None else None,
        after_snapshot=json.dumps(after, ensure_ascii=False, default=str) if after is not None else None,
        request_id=headers.get("x-request-id"), ip=(request.client.host if request and request.client else None),
        user_agent=headers.get("user-agent"), created_at=datetime.now(),
    )
    db.add(event)
