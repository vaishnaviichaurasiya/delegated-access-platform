from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models import AuditLog


def log_action(db: Session, actor_id, effective_user_id, action, resource, result="success"):
    db.add(AuditLog(actor_id=actor_id, effective_user_id=effective_user_id,
                    action=action, resource=resource, result=result))
    db.commit()


def deny(db: Session, actor_id, effective_user_id, action, resource, detail, status_code=403):
    """Record a denied attempt, then reject the request."""
    log_action(db, actor_id, effective_user_id, action, resource, result="denied")
    raise HTTPException(status_code=status_code, detail=detail)