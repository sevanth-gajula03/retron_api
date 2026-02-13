from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.user import User
from app.schemas.user import UserOut, UserUpdate


router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(
    role: str | None = None,
    ids: str | None = Query(default=None, description="Comma-separated user ids"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    query = select(User)

    if user.role != "admin":
        allowed_roles = {"student", "instructor", "partner_instructor", "guest"}
        if role and role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    if role:
        query = query.where(User.role == role)

    if ids:
        parsed = [item.strip() for item in ids.split(",") if item.strip()]
        if parsed:
            query = query.where(User.id.in_(parsed))

    return db.execute(query).scalars().all()


@router.get("/me", response_model=UserOut)
def get_me(user=Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserOut)
def update_me(payload: UserUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    data = payload.model_dump(exclude_unset=True)
    if "role" in data or "status" in data:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot update role/status")
    for key, value in data.items():
        setattr(user, key, value)
    user.updated_at = datetime.utcnow()
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: str, payload: UserUpdate, db: Session = Depends(get_db), actor=Depends(get_current_user)):
    target = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    data = payload.model_dump(exclude_unset=True)

    if actor.role != "admin":
        if actor.role != "instructor":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

        allowed_fields = {"banned_from"}
        if any(key not in allowed_fields for key in data.keys()):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

        if target.role not in ["student", "guest"]:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Can only update students")

        if data.get("banned_from"):
            instructor_course_ids = [
                row[0]
                for row in db.execute(select(Course.id).where(Course.instructor_id == actor.id)).all()
            ]
            if any(course_id not in instructor_course_ids for course_id in data["banned_from"]):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

            enrollment_course_ids = [
                row[0]
                for row in db.execute(
                    select(Enrollment.course_id).where(Enrollment.user_id == target.id)
                ).all()
            ]
            missing = [course_id for course_id in data["banned_from"] if course_id not in enrollment_course_ids]
            if missing:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Student is not enrolled in one or more courses",
                )

    for key, value in data.items():
        setattr(target, key, value)
    target.updated_at = datetime.utcnow()
    db.add(target)
    db.commit()
    db.refresh(target)
    return target


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    target = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.role != "admin" and user.id != target.id:
        if user.role not in ["instructor", "partner_instructor"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    return target


@router.delete("/{user_id}")
def delete_user(user_id: str, db: Session = Depends(get_db), _=Depends(require_roles("admin"))):
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    db.delete(user)
    db.commit()
    return {"status": "ok"}
