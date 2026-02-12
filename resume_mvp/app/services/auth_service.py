from datetime import datetime, timedelta

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_otp
from app.db.models import AuthOtp, User


def issue_otp(db: Session, email: str) -> None:
    settings = get_settings()
    otp = settings.dev_otp
    record = AuthOtp(
        email=email.lower(),
        code_hash=hash_otp(email, otp),
        expired_at=datetime.utcnow() + timedelta(minutes=10),
    )
    db.add(record)
    db.commit()


def verify_otp(db: Session, email: str, otp: str) -> bool:
    stmt = (
        select(AuthOtp)
        .where(AuthOtp.email == email.lower(), AuthOtp.used_at.is_(None))
        .order_by(desc(AuthOtp.id))
    )
    record = db.execute(stmt).scalars().first()
    if not record:
        return False
    if record.expired_at < datetime.utcnow():
        return False
    if record.code_hash != hash_otp(email, otp):
        return False
    record.used_at = datetime.utcnow()
    db.commit()
    return True


def get_or_create_user(db: Session, email: str) -> User:
    stmt = select(User).where(User.email == email.lower())
    user = db.execute(stmt).scalars().first()
    if user:
        return user
    user = User(email=email.lower())
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

