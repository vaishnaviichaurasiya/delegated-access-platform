from dataclasses import dataclass
import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from app.audit import deny
from app.database import get_db
from app.models import User, ImpersonationSession, utcnow
from app.security import decode_token

bearer = HTTPBearer()
SAFE_METHODS = ("GET", "HEAD", "OPTIONS")


@dataclass
class AuthContext:
    actor: User                                  # the real person who logged in
    effective: User                              # whose view we are using
    mode: str | None                             # None or "view_as"
    session: ImpersonationSession | None


def get_auth_context(creds=Depends(bearer), db: Session = Depends(get_db)) -> AuthContext:
    try:
        payload = decode_token(creds.credentials)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    actor = db.get(User, int(payload["sub"]))
    if not actor:
        raise HTTPException(status_code=401, detail="User not found")

    if "act_as" in payload:
        session = db.get(ImpersonationSession, payload.get("sid"))
        valid = (
            session is not None
            and session.ended_at is None
            and session.expires_at > utcnow()
            and session.actor_id == actor.id
            and session.target_id == int(payload["act_as"])
        )
        if not valid:
            raise HTTPException(status_code=401, detail="Impersonation session ended or expired")
        return AuthContext(actor, db.get(User, session.target_id), session.mode, session)

    return AuthContext(actor, actor, None, None)


def get_current_user(request: Request, ctx: AuthContext = Depends(get_auth_context),
                     db: Session = Depends(get_db)) -> User:
    """Returns the EFFECTIVE user. Blocks all writes during View-As."""
    if ctx.mode == "view_as" and request.method not in SAFE_METHODS:
        deny(db, ctx.actor.id, ctx.effective.id, "write_blocked_in_view_as",
             f"{request.method} {request.url.path}", "View-As sessions are read-only")
    return ctx.effective
