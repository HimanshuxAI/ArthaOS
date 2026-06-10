from sqlalchemy.orm import Session

from app.models import AuditLog


def log_audit(db: Session, user_id: int | None, action: str, resource: str, meta: dict | None = None) -> None:
    db.add(AuditLog(user_id=user_id, action=action, resource=resource, meta=meta or {}))
