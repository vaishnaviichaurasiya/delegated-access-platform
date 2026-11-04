from datetime import timedelta
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.audit import deny, log_action
from app.database import get_db
from app.delegation import ALLOWED_SCOPES, GRANTOR_ROLES
from app.deps import get_current_user
from app.models import User, DelegationGrant, utcnow

router = APIRouter(prefix="/delegations", tags=["delegations"])


class GrantIn(BaseModel):
    grantee_id: int
    scopes: list[str] = ["expense_approval"]
    max_amount: float = Field(gt=0)
    expires_in_hours: int = Field(default=24, ge=1, le=168)


def grant_to_dict(g: DelegationGrant) -> dict:
    return {
        "id": g.id, "grantor_id": g.grantor_id, "grantee_id": g.grantee_id,
        "scopes": g.scopes.split(","), "max_amount": g.max_amount,
        "expires_at": g.expires_at.isoformat(), "status": g.status,
    }


@router.post("")
def create_grant(body: GrantIn, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    resource = f"grantee:{body.grantee_id}"
    if user.role not in GRANTOR_ROLES:
        deny(db, user.id, user.id, "grant_create", resource,
             "Only BU Heads, Delivery Heads and Project Managers can delegate")
    if body.grantee_id == user.id:
        deny(db, user.id, user.id, "grant_create", resource,
             "You cannot delegate to yourself", status_code=400)
    grantee = db.get(User, body.grantee_id)
    if not grantee:
        deny(db, user.id, user.id, "grant_create", resource,
             "Grantee not found", status_code=404)
    if grantee.role == "admin":
        deny(db, user.id, user.id, "grant_create", resource,
             "You cannot delegate to an admin")
    if not body.scopes or not set(body.scopes) <= ALLOWED_SCOPES:
        deny(db, user.id, user.id, "grant_create", resource,
             f"Invalid scope. Allowed: {sorted(ALLOWED_SCOPES)}", status_code=400)

    grant = DelegationGrant(
        grantor_id=user.id, grantee_id=grantee.id,
        scopes=",".join(sorted(set(body.scopes))), max_amount=body.max_amount,
        expires_at=utcnow() + timedelta(hours=body.expires_in_hours))
    db.add(grant)
    db.commit()
    db.refresh(grant)
    log_action(db, user.id, user.id, "grant_create", f"grant:{grant.id}")
    return grant_to_dict(grant)


@router.get("")
def list_grants(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    given = db.query(DelegationGrant).filter(DelegationGrant.grantor_id == user.id).all()
    received = db.query(DelegationGrant).filter(DelegationGrant.grantee_id == user.id).all()
    return {"given": [grant_to_dict(g) for g in given],
            "received": [grant_to_dict(g) for g in received]}


@router.delete("/{grant_id}")
def revoke_grant(grant_id: int, user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    grant = db.get(DelegationGrant, grant_id)
    resource = f"grant:{grant_id}"
    if not grant:
        deny(db, user.id, user.id, "grant_revoke", resource,
             "Grant not found", status_code=404)
    if grant.grantor_id != user.id:
        deny(db, user.id, user.id, "grant_revoke", resource,
             "Only the grantor can revoke this delegation")
    grant.status = "revoked"
    grant.revoked_at = utcnow()
    db.commit()
    log_action(db, user.id, user.id, "grant_revoke", resource)
    return {"message": "Delegation revoked. It takes effect immediately."}
