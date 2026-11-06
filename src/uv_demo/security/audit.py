from sqlalchemy.orm import Session

from uv_demo.models.user import AuditLog


def log_audit(
    db: Session,
    action: str,
    entity_type: str,
    user_id: int | None = None,
    entity_id: int | None = None,
    details: str | None = None,
    ip_address: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        action=action,
        entity_type=entity_type,
        user_id=user_id,
        entity_id=entity_id,
        details=details,
        ip_address=ip_address,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
