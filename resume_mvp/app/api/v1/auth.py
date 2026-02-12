from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.security import create_access_token
from app.db.models import User
from app.db.session import get_db
from app.schemas.auth import LoginOtpIn, SendOtpIn
from app.services.auth_service import get_or_create_user, issue_otp, verify_otp


router = APIRouter()


@router.post("/send-otp")
def send_otp(payload: SendOtpIn, db: Session = Depends(get_db)):
    issue_otp(db, payload.email)
    return {"code": 0, "message": "ok", "data": {"dev_otp": get_settings().dev_otp}}


@router.post("/login-otp")
def login_otp(payload: LoginOtpIn, db: Session = Depends(get_db)):
    if not verify_otp(db, payload.email, payload.otp):
        raise HTTPException(status_code=400, detail="invalid otp")
    user = get_or_create_user(db, payload.email)
    token = create_access_token(str(user.id))
    return {"code": 0, "message": "ok", "data": {"access_token": token, "token_type": "bearer"}}


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {
        "code": 0,
        "message": "ok",
        "data": {"id": current_user.id, "email": current_user.email, "display_name": current_user.display_name},
    }

