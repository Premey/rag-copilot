"""
Auth service: business logic for user signup and login.
"""
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User
from app.schemas.auth import SignupRequest, UserOut


def create_user(db: Session, req: SignupRequest) -> UserOut:
    """
    Register a new user.
    Raises 409 if email already exists.
    """
    existing = db.query(User).filter(User.email == req.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        email=req.email,
        password_hash=hash_password(req.password),
        full_name=req.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return UserOut(
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        created_at=user.created_at,
    )


def authenticate_user(db: Session, email: str, password: str) -> User:
    """
    Verify credentials. Returns the User row on success.
    Raises 401 on invalid email or wrong password.
    """
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
