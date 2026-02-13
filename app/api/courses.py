from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.course import Course
from app.models.course_co_instructor import CourseCoInstructor
from app.models.announcement import Announcement
from app.models.assessment import Assessment, AssessmentQuestion, AssessmentSubmission
from app.models.enrollment import Enrollment
from app.models.module import Module
from app.models.sub_section import SubSection
from app.models.section import Section
from app.schemas.course import CourseCreate, CourseOut, CourseUpdate


router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("", response_model=list[CourseOut])
def list_courses(db: Session = Depends(get_db), user=Depends(get_current_user)):
    if user.role == "admin":
        return db.execute(select(Course)).scalars().all()
    if user.role in ["instructor", "partner_instructor"]:
        return db.execute(
            select(Course)
            .outerjoin(CourseCoInstructor, CourseCoInstructor.course_id == Course.id)
            .where(
                (Course.instructor_id == user.id)
                | (
                    (CourseCoInstructor.user_id == user.id)
                    & (CourseCoInstructor.status == "active")
                )
            )
            .distinct()
        ).scalars().all()
    return db.execute(
        select(Course)
        .outerjoin(Enrollment, Enrollment.course_id == Course.id)
        .where((Course.status == "published") | (Enrollment.user_id == user.id))
        .distinct()
    ).scalars().all()


@router.post("", response_model=CourseOut)
def create_course(
    payload: CourseCreate,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "instructor"))
):
    course = Course(
        title=payload.title,
        description=payload.description,
        thumbnail_url=payload.thumbnail_url,
        instructor_id=user.id,
        status="draft",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@router.get("/{course_id}", response_model=CourseOut)
def get_course(course_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    course = db.execute(select(Course).where(Course.id == course_id)).scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    if user.role not in ["admin", "instructor", "partner_instructor"] and course.status != "published":
        enrolled = db.execute(
            select(Enrollment).where(Enrollment.course_id == course_id, Enrollment.user_id == user.id)
        ).scalar_one_or_none()
        if not enrolled:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if user.role in ["instructor", "partner_instructor"] and course.instructor_id != user.id:
        assigned = db.execute(
            select(CourseCoInstructor).where(
                CourseCoInstructor.course_id == course_id,
                CourseCoInstructor.user_id == user.id,
                CourseCoInstructor.status == "active",
            )
        ).scalar_one_or_none()
        if not assigned:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return course


@router.get("/{course_id}/sections")
def list_sections_for_course(course_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    course = db.execute(select(Course).where(Course.id == course_id)).scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    if user.role in ["instructor", "partner_instructor"] and course.instructor_id != user.id:
        assigned = db.execute(
            select(CourseCoInstructor).where(
                CourseCoInstructor.course_id == course_id,
                CourseCoInstructor.user_id == user.id,
                CourseCoInstructor.status == "active",
            )
        ).scalar_one_or_none()
        if not assigned:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if user.role not in ["admin", "instructor", "partner_instructor"] and course.status != "published":
        enrolled = db.execute(
            select(Enrollment).where(Enrollment.course_id == course_id, Enrollment.user_id == user.id)
        ).scalar_one_or_none()
        if not enrolled:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return db.execute(select(Section).where(Section.course_id == course_id)).scalars().all()


@router.patch("/{course_id}", response_model=CourseOut)
def update_course(
    course_id: str,
    payload: CourseUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "instructor"))
):
    course = db.execute(select(Course).where(Course.id == course_id)).scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    if user.role in ["instructor", "partner_instructor"] and course.instructor_id != user.id:
        assigned = db.execute(
            select(CourseCoInstructor).where(
                CourseCoInstructor.course_id == course_id,
                CourseCoInstructor.user_id == user.id,
                CourseCoInstructor.status == "active",
            )
        ).scalar_one_or_none()
        if not assigned:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(course, key, value)
    course.updated_at = datetime.utcnow()
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


@router.delete("/{course_id}")
def delete_course(
    course_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "instructor"))
):
    course = db.execute(select(Course).where(Course.id == course_id)).scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    if user.role == "instructor" and course.instructor_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    section_ids = [row[0] for row in db.execute(
        select(Section.id).where(Section.course_id == course_id)
    ).all()]
    if section_ids:
        sub_section_ids = [row[0] for row in db.execute(
            select(SubSection.id).where(SubSection.section_id.in_(section_ids))
        ).all()]
        if sub_section_ids:
            db.execute(delete(Module).where(Module.sub_section_id.in_(sub_section_ids)))
            db.execute(delete(SubSection).where(SubSection.id.in_(sub_section_ids)))
        db.execute(delete(Module).where(Module.section_id.in_(section_ids)))
        db.execute(delete(Section).where(Section.id.in_(section_ids)))

    assessment_ids = [row[0] for row in db.execute(
        select(Assessment.id).where(Assessment.course_id == course_id)
    ).all()]
    if assessment_ids:
        db.execute(delete(AssessmentSubmission).where(AssessmentSubmission.assessment_id.in_(assessment_ids)))
        db.execute(delete(AssessmentQuestion).where(AssessmentQuestion.assessment_id.in_(assessment_ids)))
        db.execute(delete(Assessment).where(Assessment.id.in_(assessment_ids)))

    db.execute(delete(Enrollment).where(Enrollment.course_id == course_id))
    db.execute(delete(Announcement).where(Announcement.course_id == course_id))
    db.delete(course)
    db.commit()
    return {"status": "ok"}
