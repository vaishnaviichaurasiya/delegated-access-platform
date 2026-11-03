from sqlalchemy.orm import Session
from app.models import DelegationGrant, ApprovalRequest, User, utcnow

ALLOWED_SCOPES = {"expense_approval"}
SCOPE_FOR_TYPE = {"expense": "expense_approval"}
GRANTOR_ROLES = {"bu_head", "delivery_head", "project_manager"}


def find_valid_grant(db: Session, grantee: User, req: ApprovalRequest):
    """Return (grant, "") if the grantee may approve this request, else (None, reason)."""
    grants = (
        db.query(DelegationGrant)
        .filter(DelegationGrant.grantee_id == grantee.id,
                DelegationGrant.grantor_id == req.approver_id)
        .all()
    )
    if not grants:
        return None, "No delegation from the approver to you"

    needed_scope = SCOPE_FOR_TYPE.get(req.type)
    reason = "No valid delegation"
    for g in grants:
        if g.status != "active":
            reason = "Delegation was revoked"
        elif g.expires_at <= utcnow():
            reason = "Delegation has expired"
        elif needed_scope not in g.scopes.split(","):
            reason = "Request type is outside the delegated scope"
        elif req.amount > g.max_amount:
            reason = f"Amount exceeds the delegated limit of {g.max_amount:g}"
        else:
            return g, ""
    return None, reason