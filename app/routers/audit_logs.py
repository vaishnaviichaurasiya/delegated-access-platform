from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import get_current_user
from app.models import User, AuditLog

router = APIRouter(tags=["audit"])


@router.get("/audit-logs")
def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admins only")
    q = db.query(AuditLog).order_by(AuditLog.id.desc())
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": q.count(),
        "items": [
            {"id": r.id, "actor_id": r.actor_id, "effective_user_id": r.effective_user_id,
             "action": r.action, "resource": r.resource, "result": r.result,
             "timestamp": r.timestamp.isoformat()}
            for r in rows
        ],
    }