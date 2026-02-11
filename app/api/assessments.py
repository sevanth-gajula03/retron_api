from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.assessment import Assessment, AssessmentQuestion, AssessmentSubmission
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
def list_assessments(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.execute(select(Assessment)).scalars().all()


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
        created_at=datetime.utcnow()
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return assessment


@router.get("/{assessment_id}", response_model=AssessmentOut)
def get_assessment(assessment_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
    assessment = db.execute(
        select(Assessment).where(Assessment.id == assessment_id)
    ).scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    return assessment


@router.patch("/{assessment_id}", response_model=AssessmentOut)
def update_assessment(
    assessment_id: str,
    payload: AssessmentUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_roles("admin", "instructor", "partner_instructor"))
):
    assessment = db.execute(
        select(Assessment).where(Assessment.id == assessment_id)
    ).scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
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
    _=Depends(require_roles("admin", "instructor", "partner_instructor"))
):
    assessment = db.execute(
        select(Assessment).where(Assessment.id == assessment_id)
    ).scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
    db.delete(assessment)
    db.commit()
    return {"status": "ok"}


@router.get("/{assessment_id}/questions", response_model=list[AssessmentQuestionOut])
def list_questions(assessment_id: str, db: Session = Depends(get_db), _=Depends(get_current_user)):
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
    submission = AssessmentSubmission(
        assessment_id=assessment_id,
        user_id=user.id,
        answers=payload.answers,
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
