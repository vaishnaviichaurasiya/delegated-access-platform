from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.deps import AuthContext, get_auth_context
from app.models import User
from app.schemas import LoginIn
from app.security import verify_password, create_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"access_token": create_token({"sub": str(user.id)}), "token_type": "bearer"}


@router.get("/me")
def me(ctx: AuthContext = Depends(get_auth_context)):
    return {
        "id": ctx.effective.id,
        "name": ctx.effective.name,
        "role": ctx.effective.role,
        "impersonating": ctx.mode is not None,
        "actor": {"id": ctx.actor.id, "name": ctx.actor.name, "role": ctx.actor.role},
    }
