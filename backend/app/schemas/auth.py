from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, field_validator


# ─── Request Schemas ──────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ─── Response Schemas ─────────────────────────────────────────────────────────

class UserOut(BaseModel):
    user_id: str
    email: str
    full_name: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: UserOut


class MeResponse(BaseModel):
    user_id: str
    email: str
    full_name: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
