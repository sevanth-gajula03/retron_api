from datetime import datetime
import hashlib

from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user
from app.core.security import create_access_token, create_refresh_token, hash_password
from app.db.session import get_db
from app.models.password_setup_token import PasswordSetupToken
from app.models.user import User
from app.schemas.auth import LoginRequest, RefreshRequest, SetPasswordRequest, SignupRequest, TokenResponse
from app.schemas.user import UserOut
from app.services.user_service import authenticate_user, create_user, get_user_by_email

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=TokenResponse)
def signup(payload: SignupRequest, db: Session = Depends(get_db)):
    if not settings.bootstrap_admin_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Self signup is disabled. Please contact an administrator.",
        )

    email = str(payload.email).strip().lower()

    if settings.bootstrap_admin_email:
        allowed = settings.bootstrap_admin_email.strip().lower()
        if email != allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Signup is restricted.",
            )

    requested_role = (payload.role or "admin").strip().lower()
    if requested_role != "admin":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only admin bootstrap signup is allowed.",
        )

    if len(payload.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 8 characters",
        )

    existing_admin_id = db.execute(
        select(User.id).where(User.role == "admin").limit(1)
    ).scalar_one_or_none()
    if existing_admin_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin already exists; bootstrap signup is disabled.",
        )

    existing = get_user_by_email(db, email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = create_user(
        db,
        email=email,
        password=payload.password,
        name=payload.name,
        role="admin",
        password_setup_completed=True,
    )

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id)
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest):
    try:
        decoded = jwt.decode(payload.refresh_token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        subject = decoded.get("sub")
        token_type = decoded.get("type")
        if not subject or token_type != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    return TokenResponse(
        access_token=create_access_token(subject),
        refresh_token=create_refresh_token(subject)
    )


@router.post("/logout")
def logout():
    return {"status": "ok"}


@router.get("/me", response_model=UserOut)
def me(user=Depends(get_current_user)):
    return user


def _hash_setup_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@router.post("/set-password")
def set_password(payload: SetPasswordRequest, db: Session = Depends(get_db)):
    token_hash = _hash_setup_token(payload.token)
    token_row = db.execute(
        select(PasswordSetupToken).where(PasswordSetupToken.token_hash == token_hash)
    ).scalar_one_or_none()

    if not token_row:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid token")

    if token_row.used_at is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token already used")

    if token_row.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token expired")

    user_row = db.execute(select(User).where(User.id == token_row.user_id)).scalar_one_or_none()
    if not user_row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if len(payload.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password must be at least 8 characters",
        )

    user_row.hashed_password = hash_password(payload.new_password)
    user_row.password_setup_completed = True
    user_row.updated_at = datetime.utcnow()
    token_row.used_at = datetime.utcnow()

    db.add(user_row)
    db.add(token_row)
    db.commit()

    return {"status": "ok"}
