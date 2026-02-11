from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.db.session import get_db
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.module import Module
from app.models.section import Section
from app.models.sub_section import SubSection
from app.schemas.module import ModuleCreate, ModuleOut, ModuleUpdate


router = APIRouter(prefix="/modules", tags=["modules"])


@router.post("", response_model=ModuleOut)
def create_module(
    payload: ModuleCreate,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "instructor"))
):
    section = db.execute(select(Section).where(Section.id == payload.section_id)).scalar_one_or_none()
    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    course = db.execute(select(Course).where(Course.id == section.course_id)).scalar_one_or_none()
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    if user.role == "instructor" and course and course.instructor_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if payload.sub_section_id:
        sub_section = db.execute(
            select(SubSection).where(SubSection.id == payload.sub_section_id)
        ).scalar_one_or_none()
        if not sub_section:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sub-section not found")
    module = Module(
        section_id=payload.section_id,
        sub_section_id=payload.sub_section_id,
        title=payload.title,
        type=payload.type,
        content=payload.content,
        order=payload.order or 0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(module)
    db.commit()
    db.refresh(module)
    return module


@router.patch("/{module_id}", response_model=ModuleOut)
def update_module(
    module_id: str,
    payload: ModuleUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "instructor"))
):
    module = db.execute(select(Module).where(Module.id == module_id)).scalar_one_or_none()
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    section = db.execute(select(Section).where(Section.id == module.section_id)).scalar_one_or_none()
    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    course = db.execute(select(Course).where(Course.id == section.course_id)).scalar_one_or_none()
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    if user.role == "instructor" and course and course.instructor_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    data = payload.model_dump(exclude_unset=True)
    if data.get("sub_section_id"):
        sub_section = db.execute(
            select(SubSection).where(SubSection.id == data["sub_section_id"])
        ).scalar_one_or_none()
        if not sub_section:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sub-section not found")
    for key, value in data.items():
        setattr(module, key, value)
    module.updated_at = datetime.utcnow()
    db.add(module)
    db.commit()
    db.refresh(module)
    return module


@router.delete("/{module_id}")
def delete_module(
    module_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "instructor"))
):
    module = db.execute(select(Module).where(Module.id == module_id)).scalar_one_or_none()
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    section = db.execute(select(Section).where(Section.id == module.section_id)).scalar_one_or_none()
    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    course = db.execute(select(Course).where(Course.id == section.course_id)).scalar_one_or_none()
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    if user.role == "instructor" and course and course.instructor_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    db.delete(module)
    db.commit()
    return {"status": "ok"}
@router.get("/{module_id}", response_model=ModuleOut)
def get_module(module_id: str, db: Session = Depends(get_db), user=Depends(require_roles("admin", "instructor", "student", "guest"))):
    module = db.execute(select(Module).where(Module.id == module_id)).scalar_one_or_none()
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    return module


@router.get("/section/{section_id}", response_model=list[ModuleOut])
def list_modules_for_section(
    section_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "instructor", "student", "guest"))
):
    section = db.execute(select(Section).where(Section.id == section_id)).scalar_one_or_none()
    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    course = db.execute(select(Course).where(Course.id == section.course_id)).scalar_one_or_none()
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    if user.role == "instructor" and course.instructor_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if user.role in ["student", "guest"] and course.status != "published":
        enrolled = db.execute(
            select(Enrollment).where(Enrollment.course_id == course.id, Enrollment.user_id == user.id)
        ).scalar_one_or_none()
        if not enrolled:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return db.execute(
        select(Module).where(Module.section_id == section_id, Module.sub_section_id.is_(None))
    ).scalars().all()


@router.get("/subsection/{sub_section_id}", response_model=list[ModuleOut])
def list_modules_for_subsection(
    sub_section_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "instructor", "student", "guest"))
):
    sub_section = db.execute(select(SubSection).where(SubSection.id == sub_section_id)).scalar_one_or_none()
    if sub_section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sub-section not found")
    section = db.execute(select(Section).where(Section.id == sub_section.section_id)).scalar_one_or_none()
    if section is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    course = db.execute(select(Course).where(Course.id == section.course_id)).scalar_one_or_none()
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    if user.role == "instructor" and course and course.instructor_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if user.role in ["student", "guest"] and course and course.status != "published":
        enrolled = db.execute(
            select(Enrollment).where(Enrollment.course_id == course.id, Enrollment.user_id == user.id)
        ).scalar_one_or_none()
        if not enrolled:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return db.execute(select(Module).where(Module.sub_section_id == sub_section_id)).scalars().all()
