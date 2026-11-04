from datetime import timedelta
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.audit import deny, log_action
from app.database import get_db
from app.deps import AuthContext, get_auth_context
from app.models import User, ImpersonationSession, utcnow
from app.security import create_token

router = APIRouter(prefix="/impersonation", tags=["impersonation"])
SESSION_MINUTES = 30


class ViewAsIn(BaseModel):
    target_id: int


@router.post("/view-as")
def start_view_as(body: ViewAsIn, ctx: AuthContext = Depends(get_auth_context),
                  db: Session = Depends(get_db)):
    actor = ctx.actor
    resource = f"user:{body.target_id}"

    if ctx.mode is not None:
        deny(db, actor.id, ctx.effective.id, "view_as_start", resource,
             "Chained impersonation is not allowed")
    if actor.role != "admin":
        deny(db, actor.id, actor.id, "view_as_start", resource,
             "Only admins can use View-As")
    if body.target_id == actor.id:
        deny(db, actor.id, actor.id, "view_as_start", resource,
             "You cannot view as yourself", status_code=400)

    target = db.get(User, body.target_id)
    if not target:
        deny(db, actor.id, actor.id, "view_as_start", resource,
             "Target user not found", status_code=404)
    if target.role == "admin":
        deny(db, actor.id, actor.id, "view_as_start", resource,
             "You cannot impersonate an admin")

    session = ImpersonationSession(
        actor_id=actor.id, target_id=target.id, mode="view_as",
        expires_at=utcnow() + timedelta(minutes=SESSION_MINUTES))
    db.add(session)
    db.commit()
    db.refresh(session)

    log_action(db, actor.id, target.id, "view_as_start", resource)
    token = create_token(
        {"sub": str(actor.id), "act_as": str(target.id), "mode": "view_as", "sid": session.id},
        minutes=SESSION_MINUTES)
    return {
        "access_token": token,
        "token_type": "bearer",
        "message": f"Viewing as {target.name} ({target.role}), read-only, {SESSION_MINUTES} minutes",
    }


@router.post("/end")
def end_session(ctx: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    if ctx.session is None:
        deny(db, ctx.actor.id, ctx.actor.id, "view_as_end", "-",
             "You are not impersonating anyone", status_code=400)
    ctx.session.ended_at = utcnow()
    db.commit()
    log_action(db, ctx.actor.id, ctx.effective.id, "view_as_end", f"session:{ctx.session.id}")
    return {"message": "View-As session ended. Log in again or use your original token."}
