from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.models.user import User


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.execute(select(User).where(User.email == email)).scalar_one_or_none()


def get_user_by_id(db: Session, user_id: str) -> User | None:
    return db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()


def create_user(
    db: Session,
    email: str,
    password: str,
    name: str | None,
    role: str | None,
    password_setup_completed: bool = True,
) -> User:
    user = User(
        email=email,
        hashed_password=hash_password(password),
        name=name,
        role=role or "student",
        status="active",
        password_setup_completed=password_setup_completed,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
