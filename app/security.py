from datetime import datetime, timedelta, timezone
import bcrypt
import jwt
from app.config import SECRET_KEY, ALGORITHM, TOKEN_MINUTES


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_token(claims: dict, minutes: int = TOKEN_MINUTES) -> str:
    payload = {**claims, "exp": datetime.now(timezone.utc) + timedelta(minutes=minutes)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
