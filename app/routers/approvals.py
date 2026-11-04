from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.audit import deny, log_action
from app.database import get_db
from app.delegation import find_valid_grant
from app.deps import AuthContext, get_auth_context, get_current_user
from app.models import User, Project, ApprovalRequest, utcnow
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
    user_ids = set()
    for r in rows:
        user_ids.update(i for i in (r.requester_id, r.decided_by_id, r.on_behalf_of_id) if i)
    names = {u.id: u.name for u in db.query(User).filter(User.id.in_(user_ids)).all()}
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
                "decided_by": names.get(r.decided_by_id),
                "on_behalf_of": names.get(r.on_behalf_of_id),
            }
            for r in rows
        ],
    }


@router.post("/{approval_id}/approve")
def approve(
    approval_id: int,
    ctx: AuthContext = Depends(get_auth_context),
    user: User = Depends(get_current_user),   # blocks this call during View-As
    db: Session = Depends(get_db),
):
    resource = f"approval:{approval_id}"
    req = db.get(ApprovalRequest, approval_id)
    if not req:
        deny(db, ctx.actor.id, user.id, "approve", resource,
             "Approval request not found", status_code=404)
    if req.status != "pending":
        deny(db, ctx.actor.id, user.id, "approve", resource,
             f"Request is already {req.status}", status_code=409)
    if req.requester_id == user.id:
        deny(db, ctx.actor.id, user.id, "approve", resource,
             "You cannot approve your own request")

    grant = None
    if req.approver_id != user.id:
        grant, reason = find_valid_grant(db, user, req)
        if grant is None:
            deny(db, ctx.actor.id, user.id, "approve_on_behalf", resource, reason)

    req.status = "approved"
    req.decided_by_id = user.id
    req.decided_at = utcnow()
    if grant:
        req.on_behalf_of_id = req.approver_id
        req.grant_id = grant.id
    db.commit()

    if grant:
        approver = db.get(User, req.approver_id)
        log_action(db, ctx.actor.id, user.id, "approve_on_behalf",
                   f"{resource} grant:{grant.id} for user:{approver.id}")
        message = f"Approved by {user.name} on behalf of {approver.name}"
    else:
        log_action(db, ctx.actor.id, user.id, "approve", resource)
        message = f"Approved by {user.name}"
    return {"id": req.id, "status": req.status, "message": message}
