from datetime import datetime, timedelta, timezone
import hashlib
from typing import Any

from jose import jwt

from app.core.config import get_settings


ALGORITHM = "HS256"


def create_access_token(subject: str) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.app_secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.app_secret_key, algorithms=[ALGORITHM])


def hash_otp(email: str, code: str) -> str:
    settings = get_settings()
    raw = f"{email.lower()}::{code}::{settings.app_secret_key}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

