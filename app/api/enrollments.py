from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.course import Course
from app.models.enrollment import Enrollment


router = APIRouter(prefix="/enrollments", tags=["enrollments"])


@router.get("")
def list_enrollments(
    course_id: str | None = None,
    user_id: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    query = select(Enrollment)

    if user.role in ["student", "guest", "partner_instructor"]:
        query = query.where(Enrollment.user_id == user.id)
    elif user.role == "instructor":
        query = query.join(Course, Course.id == Enrollment.course_id).where(Course.instructor_id == user.id)

    if course_id:
        query = query.where(Enrollment.course_id == course_id)
    if user_id:
        if user.role not in ["admin", "instructor"] and user_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        query = query.where(Enrollment.user_id == user_id)

    enrollments = db.execute(query).scalars().all()
    return [{"course_id": e.course_id, "user_id": e.user_id, "id": e.id} for e in enrollments]


@router.post("/assign")
def assign_course(
    payload: dict,
    db: Session = Depends(get_db),
    _=Depends(require_roles("admin"))
):
    course_id = payload.get("course_id")
    user_id = payload.get("user_id")
    if not course_id or not user_id:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="course_id and user_id required")
    course = db.execute(select(Course).where(Course.id == course_id)).scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    existing = db.execute(
        select(Enrollment).where(Enrollment.course_id == course_id, Enrollment.user_id == user_id)
    ).scalar_one_or_none()
    if existing:
        return {"status": "ok"}
    enrollment = Enrollment(course_id=course_id, user_id=user_id, created_at=datetime.utcnow())
    db.add(enrollment)
    db.commit()
    return {"status": "ok"}


@router.post("/{course_id}")
def enroll_course(
    course_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_roles("student", "guest"))
):
    course = db.execute(select(Course).where(Course.id == course_id)).scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    existing = db.execute(
        select(Enrollment).where(Enrollment.course_id == course_id, Enrollment.user_id == user.id)
    ).scalar_one_or_none()
    if existing:
        return {"status": "ok"}
    enrollment = Enrollment(course_id=course_id, user_id=user.id, created_at=datetime.utcnow())
    db.add(enrollment)
    db.commit()
    return {"status": "ok"}


@router.delete("/{course_id}")
def unenroll_course(
    course_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    enrollment = db.execute(
        select(Enrollment).where(Enrollment.course_id == course_id, Enrollment.user_id == user.id)
    ).scalar_one_or_none()
    if not enrollment:
        return {"status": "ok"}
    db.delete(enrollment)
    db.commit()
    return {"status": "ok"}
