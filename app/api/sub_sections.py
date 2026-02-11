from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.section import Section
from app.models.module import Module
from app.models.sub_section import SubSection
from app.schemas.sub_section import SubSectionCreate, SubSectionOut, SubSectionUpdate


router = APIRouter(prefix="/subsections", tags=["subsections"])


@router.get("/section/{section_id}", response_model=list[SubSectionOut])
def list_subsections(
    section_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    section = db.execute(select(Section).where(Section.id == section_id)).scalar_one_or_none()
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    course = db.execute(select(Course).where(Course.id == section.course_id)).scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    if user.role == "instructor" and course.instructor_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if user.role in ["student", "guest"] and course.status != "published":
        enrolled = db.execute(
            select(Enrollment).where(Enrollment.course_id == course.id, Enrollment.user_id == user.id)
        ).scalar_one_or_none()
        if not enrolled:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return db.execute(select(SubSection).where(SubSection.section_id == section_id)).scalars().all()


@router.post("", response_model=SubSectionOut)
def create_subsection(
    payload: SubSectionCreate,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "instructor"))
):
    section = db.execute(select(Section).where(Section.id == payload.section_id)).scalar_one_or_none()
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    course = db.execute(select(Course).where(Course.id == section.course_id)).scalar_one_or_none()
    if user.role == "instructor" and course and course.instructor_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    subsection = SubSection(
        section_id=payload.section_id,
        title=payload.title,
        description=payload.description,
        objectives=payload.objectives,
        duration=payload.duration,
        order=payload.order or 0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(subsection)
    db.commit()
    db.refresh(subsection)
    return subsection


@router.get("/{subsection_id}", response_model=SubSectionOut)
def get_subsection(subsection_id: str, db: Session = Depends(get_db), _=Depends(require_roles("admin", "instructor"))):
    subsection = db.execute(select(SubSection).where(SubSection.id == subsection_id)).scalar_one_or_none()
    if not subsection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sub-section not found")
    return subsection


@router.patch("/{subsection_id}", response_model=SubSectionOut)
def update_subsection(
    subsection_id: str,
    payload: SubSectionUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_roles("admin", "instructor"))
):
    subsection = db.execute(select(SubSection).where(SubSection.id == subsection_id)).scalar_one_or_none()
    if not subsection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sub-section not found")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(subsection, key, value)
    subsection.updated_at = datetime.utcnow()
    db.add(subsection)
    db.commit()
    db.refresh(subsection)
    return subsection


@router.delete("/{subsection_id}")
def delete_subsection(
    subsection_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_roles("admin", "instructor"))
):
    subsection = db.execute(select(SubSection).where(SubSection.id == subsection_id)).scalar_one_or_none()
    if not subsection:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sub-section not found")
    db.execute(delete(Module).where(Module.sub_section_id == subsection_id))
    db.delete(subsection)
    db.commit()
    return {"status": "ok"}
