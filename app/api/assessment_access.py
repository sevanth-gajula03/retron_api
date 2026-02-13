from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.assessment import Assessment
from app.models.assessment_access import AssessmentAccess
from app.models.user import User
from app.schemas.assessment_access import AssessmentAccessCreate, AssessmentAccessOut, AssessmentAccessUpdate


router = APIRouter(prefix="/assessment-access", tags=["assessment-access"])


class BulkAssessmentAccessCreate(BaseModel):
    student_ids: list[str]
    assessment_ids: list[str]
    mentor_id: str | None = None
    status: str = "active"


@router.get("", response_model=list[AssessmentAccessOut])
def list_assessment_access(
    student_id: str | None = None,
    assessment_id: str | None = None,
    mentor_id: str | None = None,
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    query = select(AssessmentAccess)

    if user.role in ["student", "guest"]:
        query = query.where(AssessmentAccess.student_id == user.id)
    elif user.role == "partner_instructor":
        query = query.where(
            (AssessmentAccess.mentor_id == user.id) | (AssessmentAccess.granted_by == user.id)
        )

    if student_id:
        query = query.where(AssessmentAccess.student_id == student_id)
    if assessment_id:
        query = query.where(AssessmentAccess.assessment_id == assessment_id)
    if mentor_id:
        query = query.where(AssessmentAccess.mentor_id == mentor_id)
    if status_filter:
        query = query.where(AssessmentAccess.status == status_filter)

    return db.execute(query).scalars().all()


@router.post("", response_model=AssessmentAccessOut)
def grant_assessment_access(
    payload: AssessmentAccessCreate,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "instructor", "partner_instructor")),
):
    student = db.execute(select(User).where(User.id == payload.student_id)).scalar_one_or_none()
    assessment = db.execute(select(Assessment).where(Assessment.id == payload.assessment_id)).scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    if not assessment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")

    if student.role not in ["student", "guest"]:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid student role")

    existing = db.execute(
        select(AssessmentAccess).where(
            AssessmentAccess.student_id == payload.student_id,
            AssessmentAccess.assessment_id == payload.assessment_id,
        )
    ).scalar_one_or_none()

    effective_mentor_id = payload.mentor_id
    if user.role == "partner_instructor":
        effective_mentor_id = user.id

    if existing:
        existing.mentor_id = effective_mentor_id
        existing.granted_by = payload.granted_by or user.id
        existing.granted_by_name = payload.granted_by_name
        existing.assessment_title = payload.assessment_title or assessment.title
        existing.status = payload.status or "active"
        existing.granted_at = payload.granted_at or datetime.utcnow()
        existing.expires_at = payload.expires_at
        existing.updated_at = datetime.utcnow()
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    access = AssessmentAccess(
        student_id=payload.student_id,
        assessment_id=payload.assessment_id,
        mentor_id=effective_mentor_id,
        granted_by=payload.granted_by or user.id,
        granted_by_name=payload.granted_by_name,
        assessment_title=payload.assessment_title or assessment.title,
        status=payload.status or "active",
        granted_at=payload.granted_at or datetime.utcnow(),
        expires_at=payload.expires_at,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(access)
    db.commit()
    db.refresh(access)
    return access


@router.post("/bulk-grant")
def bulk_grant_assessment_access(
    payload: BulkAssessmentAccessCreate,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "instructor", "partner_instructor")),
):
    if not payload.student_ids or not payload.assessment_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="student_ids and assessment_ids are required",
        )

    created = 0
    updated = 0
    for student_id in payload.student_ids:
        for assessment_id in payload.assessment_ids:
            existing = db.execute(
                select(AssessmentAccess).where(
                    AssessmentAccess.student_id == student_id,
                    AssessmentAccess.assessment_id == assessment_id,
                )
            ).scalar_one_or_none()

            assessment = db.execute(select(Assessment).where(Assessment.id == assessment_id)).scalar_one_or_none()
            if not assessment:
                continue

            mentor_id = payload.mentor_id
            if user.role == "partner_instructor":
                mentor_id = user.id

            if existing:
                existing.mentor_id = mentor_id
                existing.status = payload.status
                existing.granted_by = user.id
                existing.assessment_title = assessment.title
                existing.granted_at = datetime.utcnow()
                existing.updated_at = datetime.utcnow()
                db.add(existing)
                updated += 1
            else:
                db.add(
                    AssessmentAccess(
                        student_id=student_id,
                        assessment_id=assessment_id,
                        mentor_id=mentor_id,
                        granted_by=user.id,
                        assessment_title=assessment.title,
                        status=payload.status,
                        granted_at=datetime.utcnow(),
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                    )
                )
                created += 1

    db.commit()
    return {"status": "ok", "created": created, "updated": updated}


@router.patch("/{access_id}", response_model=AssessmentAccessOut)
def update_assessment_access(
    access_id: str,
    payload: AssessmentAccessUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    access = db.execute(select(AssessmentAccess).where(AssessmentAccess.id == access_id)).scalar_one_or_none()
    if not access:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment access not found")

    if user.role in ["student", "guest"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if user.role == "partner_instructor" and access.mentor_id != user.id and access.granted_by != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(access, key, value)
    access.updated_at = datetime.utcnow()
    db.add(access)
    db.commit()
    db.refresh(access)
    return access


@router.delete("/{access_id}")
def delete_assessment_access(
    access_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    access = db.execute(select(AssessmentAccess).where(AssessmentAccess.id == access_id)).scalar_one_or_none()
    if not access:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment access not found")

    if user.role == "partner_instructor" and access.mentor_id != user.id and access.granted_by != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if user.role in ["student", "guest"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    db.delete(access)
    db.commit()
    return {"status": "ok"}
