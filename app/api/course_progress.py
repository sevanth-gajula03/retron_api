from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.course import Course
from app.models.course_progress import CourseProgress
from app.models.enrollment import Enrollment
from app.schemas.course_progress import CourseProgressCreate, CourseProgressOut, CourseProgressUpdate


router = APIRouter(prefix="/course-progress", tags=["course-progress"])


def _can_access_progress(user, target_user_id: str) -> bool:
    if user.role == "admin":
        return True
    if user.id == target_user_id:
        return True
    return user.role in ["instructor", "partner_instructor"]


@router.get("", response_model=list[CourseProgressOut])
def list_progress(
    user_id: str | None = None,
    course_id: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    query = select(CourseProgress)

    if user.role in ["student", "guest"]:
        query = query.where(CourseProgress.user_id == user.id)
    elif user.role == "instructor":
        query = query.join(Course, Course.id == CourseProgress.course_id).where(Course.instructor_id == user.id)

    if user_id:
        if not _can_access_progress(user, user_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        query = query.where(CourseProgress.user_id == user_id)

    if course_id:
        query = query.where(CourseProgress.course_id == course_id)

    return db.execute(query).scalars().all()


@router.post("", response_model=CourseProgressOut)
def create_or_upsert_progress(
    payload: CourseProgressCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    target_user_id = payload.user_id or user.id

    if user.role in ["student", "guest"] and target_user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    course = db.execute(select(Course).where(Course.id == payload.course_id)).scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    if user.role == "instructor" and course.instructor_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    existing = db.execute(
        select(CourseProgress).where(
            CourseProgress.user_id == target_user_id,
            CourseProgress.course_id == payload.course_id,
        )
    ).scalar_one_or_none()

    if existing:
        data = payload.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(existing, key, value)
        existing.updated_at = datetime.utcnow()
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    enrolled = db.execute(
        select(Enrollment).where(Enrollment.user_id == target_user_id, Enrollment.course_id == payload.course_id)
    ).scalar_one_or_none()
    if not enrolled:
        db.add(Enrollment(user_id=target_user_id, course_id=payload.course_id, created_at=datetime.utcnow()))

    progress = CourseProgress(
        user_id=target_user_id,
        course_id=payload.course_id,
        completed_modules=payload.completed_modules or [],
        completed_sections=payload.completed_sections or [],
        module_progress_percentage=payload.module_progress_percentage or 0,
        section_progress_percentage=payload.section_progress_percentage or 0,
        completed_module_count=payload.completed_module_count or 0,
        completed_section_count=payload.completed_section_count or 0,
        enrolled_at=payload.enrolled_at,
        last_accessed=payload.last_accessed,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(progress)
    db.commit()
    db.refresh(progress)
    return progress


@router.patch("/{progress_id}", response_model=CourseProgressOut)
def update_progress(
    progress_id: str,
    payload: CourseProgressUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    progress = db.execute(select(CourseProgress).where(CourseProgress.id == progress_id)).scalar_one_or_none()
    if not progress:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Progress not found")

    if user.role in ["student", "guest"] and progress.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    if user.role == "instructor":
        course = db.execute(select(Course).where(Course.id == progress.course_id)).scalar_one_or_none()
        if not course or course.instructor_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(progress, key, value)
    progress.updated_at = datetime.utcnow()
    db.add(progress)
    db.commit()
    db.refresh(progress)
    return progress


@router.get("/{progress_id}", response_model=CourseProgressOut)
def get_progress(
    progress_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    progress = db.execute(select(CourseProgress).where(CourseProgress.id == progress_id)).scalar_one_or_none()
    if not progress:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Progress not found")

    if user.role in ["student", "guest"] and progress.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    if user.role == "instructor":
        course = db.execute(select(Course).where(Course.id == progress.course_id)).scalar_one_or_none()
        if not course or course.instructor_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    return progress


@router.delete("/{progress_id}")
def delete_progress(
    progress_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    progress = db.execute(select(CourseProgress).where(CourseProgress.id == progress_id)).scalar_one_or_none()
    if not progress:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Progress not found")

    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    db.delete(progress)
    db.commit()
    return {"status": "ok"}
