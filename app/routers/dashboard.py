from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import get_current_user
from app.models import User, ApprovalRequest
from app.scope import team_user_ids, scoped_projects, scoped_approvals

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard")
def dashboard(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    approvals = scoped_approvals(db, user)
    pending = approvals.filter(ApprovalRequest.status == "pending")
    pending_amount = pending.with_entities(func.coalesce(func.sum(ApprovalRequest.amount), 0)).scalar()
    return {
        "viewing_as": {"id": user.id, "name": user.name, "role": user.role},
        "projects": scoped_projects(db, user).count(),
        "team_size": len(team_user_ids(db, user)),
        "total_requests": approvals.count(),
        "pending_requests": pending.count(),
        "pending_amount": pending_amount,
    }