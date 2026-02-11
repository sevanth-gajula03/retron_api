from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.db.session import get_db
from app.models.course import Course
from app.models.section import Section
from app.schemas.section import SectionCreate, SectionOut, SectionUpdate


router = APIRouter(prefix="/sections", tags=["sections"])


@router.post("", response_model=SectionOut)
def create_section(
    payload: SectionCreate,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "instructor"))
):
    course = db.execute(select(Course).where(Course.id == payload.course_id)).scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    if user.role == "instructor" and course.instructor_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    section = Section(
        course_id=payload.course_id,
        title=payload.title,
        order=payload.order or 0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(section)
    db.commit()
    db.refresh(section)
    return section


@router.patch("/{section_id}", response_model=SectionOut)
def update_section(
    section_id: str,
    payload: SectionUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "instructor"))
):
    section = db.execute(select(Section).where(Section.id == section_id)).scalar_one_or_none()
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    course = db.execute(select(Course).where(Course.id == section.course_id)).scalar_one_or_none()
    if user.role == "instructor" and course and course.instructor_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(section, key, value)
    section.updated_at = datetime.utcnow()
    db.add(section)
    db.commit()
    db.refresh(section)
    return section


@router.delete("/{section_id}")
def delete_section(
    section_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "instructor"))
):
    section = db.execute(select(Section).where(Section.id == section_id)).scalar_one_or_none()
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    course = db.execute(select(Course).where(Course.id == section.course_id)).scalar_one_or_none()
    if user.role == "instructor" and course and course.instructor_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    db.delete(section)
    db.commit()
    return {"status": "ok"}
