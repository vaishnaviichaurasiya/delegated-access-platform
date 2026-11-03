from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import get_current_user
from app.models import User, Project, ApprovalRequest
from app.scope import scoped_approvals

router = APIRouter(prefix="/approvals", tags=["approvals"])


@router.get("")
def list_approvals(
    status: str | None = Query(None, description="pending, approved or rejected"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = scoped_approvals(db, user)
    if status:
        q = q.filter(ApprovalRequest.status == status)
    total = q.count()
    rows = (
        q.order_by(ApprovalRequest.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    names = {u.id: u.name for u in db.query(User).filter(User.id.in_({r.requester_id for r in rows})).all()}
    projects = {p.id: p.name for p in db.query(Project).filter(Project.id.in_({r.project_id for r in rows})).all()}
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": r.id,
                "type": r.type,
                "amount": r.amount,
                "status": r.status,
                "requester": names.get(r.requester_id),
                "project": projects.get(r.project_id),
            }
            for r in rows
        ],
    }