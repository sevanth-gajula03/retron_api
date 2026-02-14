from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.assessment import Assessment, AssessmentQuestion, AssessmentSubmission
from app.models.assessment_access import AssessmentAccess
from app.models.course import Course
from app.schemas.assessment import (
    AssessmentCreate,
    AssessmentOut,
    AssessmentQuestionCreate,
    AssessmentQuestionOut,
    AssessmentSubmissionCreate,
    AssessmentSubmissionOut,
    AssessmentUpdate
)


router = APIRouter(prefix="/assessments", tags=["assessments"])


@router.get("", response_model=list[AssessmentOut])
def list_assessments(db: Session = Depends(get_db), user=Depends(get_current_user)):
    query = select(Assessment)
    if user.role == "instructor":
        query = query.where((Assessment.created_by == user.id) | (Assessment.instructor_id == user.id))
    if user.role == "partner_instructor":
        query = query.where(Assessment.created_by == user.id)
    if user.role in ["student", "guest"]:
        query = query.join(AssessmentAccess, AssessmentAccess.assessment_id == Assessment.id).where(
            AssessmentAccess.student_id == user.id,
            AssessmentAccess.status == "active",
        )
    return db.execute(query).scalars().all()


@router.post("", response_model=AssessmentOut)
def create_assessment(
    payload: AssessmentCreate,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "instructor", "partner_instructor"))
):
    course = db.execute(
        select(Course).where(Course.id == payload.course_id)
    ).scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    if user.role in ["instructor", "partner_instructor"] and course.instructor_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    assessment = Assessment(
        course_id=payload.course_id,
        title=payload.title,
        description=payload.description,
        created_by=user.id,
        instructor_id=user.id,
        instructor_name=getattr(user, "full_name", None) or getattr(user, "name", None),
        course_title=course.title,
        status="draft",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


@router.get("/{assessment_id}", response_model=AssessmentOut)
def get_assessment(assessment_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    assessment = db.execute(
        select(Assessment).where(Assessment.id == assessment_id)
    ).scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    if user.role in ["student", "guest"]:
        access = db.execute(
            select(AssessmentAccess).where(
                AssessmentAccess.assessment_id == assessment_id,
                AssessmentAccess.student_id == user.id,
                AssessmentAccess.status == "active",
            )
        ).scalar_one_or_none()
        if not access:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return assessment


@router.patch("/{assessment_id}", response_model=AssessmentOut)
def update_assessment(
    assessment_id: str,
    payload: AssessmentUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "instructor", "partner_instructor"))
):
    assessment = db.execute(
        select(Assessment).where(Assessment.id == assessment_id)
    ).scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    if user.role != "admin" and assessment.created_by and assessment.created_by != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(assessment, key, value)
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


@router.delete("/{assessment_id}")
def delete_assessment(
    assessment_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "instructor", "partner_instructor"))
):
    assessment = db.execute(
        select(Assessment).where(Assessment.id == assessment_id)
    ).scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    if user.role != "admin" and assessment.created_by and assessment.created_by != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    db.delete(assessment)
    db.commit()
    return {"status": "ok"}


@router.get("/{assessment_id}/questions", response_model=list[AssessmentQuestionOut])
def list_questions(assessment_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    if user.role in ["student", "guest"]:
        access = db.execute(
            select(AssessmentAccess).where(
                AssessmentAccess.assessment_id == assessment_id,
                AssessmentAccess.student_id == user.id,
                AssessmentAccess.status == "active",
            )
        ).scalar_one_or_none()
        if not access:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return db.execute(
        select(AssessmentQuestion).where(AssessmentQuestion.assessment_id == assessment_id)
    ).scalars().all()


@router.post("/{assessment_id}/questions", response_model=AssessmentQuestionOut)
def add_question(
    assessment_id: str,
    payload: AssessmentQuestionCreate,
    db: Session = Depends(get_db),
    _=Depends(require_roles("admin", "instructor", "partner_instructor"))
):
    question = AssessmentQuestion(
        assessment_id=assessment_id,
        prompt=payload.prompt,
        options=payload.options,
        answer=payload.answer
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


@router.post("/{assessment_id}/submit", response_model=AssessmentSubmissionOut)
def submit_assessment(
    assessment_id: str,
    payload: AssessmentSubmissionCreate,
    db: Session = Depends(get_db),
    user=Depends(require_roles("student", "guest"))
):
    access = db.execute(
        select(AssessmentAccess).where(
            AssessmentAccess.assessment_id == assessment_id,
            AssessmentAccess.student_id == user.id,
            AssessmentAccess.status == "active",
        )
    ).scalar_one_or_none()
    if not access:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    submission = AssessmentSubmission(
        assessment_id=assessment_id,
        user_id=user.id,
        student_email=getattr(user, "email", None),
        student_name=getattr(user, "full_name", None) or getattr(user, "name", None),
        answers=payload.answers,
        submitted_at=datetime.utcnow(),
        created_at=datetime.utcnow()
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


@router.get("/{assessment_id}/submissions", response_model=list[AssessmentSubmissionOut])
def list_submissions(
    assessment_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_roles("admin", "instructor", "partner_instructor"))
):
    return db.execute(
        select(AssessmentSubmission).where(AssessmentSubmission.assessment_id == assessment_id)
    ).scalars().all()
