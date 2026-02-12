from pydantic import BaseModel, EmailStr


class SendOtpIn(BaseModel):
    email: EmailStr


class LoginOtpIn(BaseModel):
    email: EmailStr
    otp: str

