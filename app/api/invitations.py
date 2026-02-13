from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.course import Course
from app.models.course_co_instructor import CourseCoInstructor
from app.models.invitation import Invitation
from app.schemas.invitation import InvitationCreate, InvitationOut, InvitationUpdate


router = APIRouter(prefix="/invitations", tags=["invitations"])


def _can_manage_course(db: Session, user, course_id: str) -> bool:
    if user.role == "admin":
        return True
    course = db.execute(select(Course).where(Course.id == course_id)).scalar_one_or_none()
    if not course:
        return False
    if course.instructor_id == user.id:
        return True
    co_instructor = db.execute(
        select(CourseCoInstructor).where(
            CourseCoInstructor.course_id == course_id,
            CourseCoInstructor.user_id == user.id,
            CourseCoInstructor.status == "active",
        )
    ).scalar_one_or_none()
    return co_instructor is not None


@router.get("", response_model=list[InvitationOut])
def list_invitations(
    course_id: str | None = None,
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    query = select(Invitation)

    if user.role != "admin":
        query = query.where(
            (Invitation.inviter_id == user.id)
            | (Invitation.invitee_id == user.id)
            | (Invitation.invitee_email == user.email)
        )

    if course_id:
        query = query.where(Invitation.course_id == course_id)
    if status_filter:
        query = query.where(Invitation.status == status_filter)

    return db.execute(query).scalars().all()


@router.post("", response_model=InvitationOut)
def create_invitation(
    payload: InvitationCreate,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "instructor", "partner_instructor")),
):
    course = db.execute(select(Course).where(Course.id == payload.course_id)).scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    if not _can_manage_course(db, user, payload.course_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    existing = db.execute(
        select(Invitation).where(
            Invitation.course_id == payload.course_id,
            Invitation.invitee_email == str(payload.invitee_email),
            Invitation.status == "pending",
        )
    ).scalar_one_or_none()
    if existing:
        return existing

    invitation = Invitation(
        course_id=payload.course_id,
        inviter_id=user.id,
        invitee_id=payload.invitee_id,
        invitee_email=str(payload.invitee_email),
        role=payload.role,
        status="pending",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return invitation


@router.patch("/{invitation_id}", response_model=InvitationOut)
def update_invitation(
    invitation_id: str,
    payload: InvitationUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    invitation = db.execute(select(Invitation).where(Invitation.id == invitation_id)).scalar_one_or_none()
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    is_inviter = invitation.inviter_id == user.id
    is_invitee = invitation.invitee_id == user.id or invitation.invitee_email == user.email
    is_admin = user.role == "admin"
    if not (is_admin or is_inviter or is_invitee):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    data = payload.model_dump(exclude_unset=True)

    if not is_admin and not is_inviter:
        blocked = {"invitee_id", "role"}
        for key in blocked:
            if key in data:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Cannot update {key}",
                )
        if "status" in data and data["status"] not in ["accepted", "rejected"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invitee can only accept or reject",
            )

    for key, value in data.items():
        setattr(invitation, key, value)

    if invitation.status == "accepted":
        invitee_id = invitation.invitee_id or user.id
        existing = db.execute(
            select(CourseCoInstructor).where(
                CourseCoInstructor.course_id == invitation.course_id,
                CourseCoInstructor.user_id == invitee_id,
            )
        ).scalar_one_or_none()
        if existing:
            existing.status = "active"
            existing.role = invitation.role
            existing.updated_at = datetime.utcnow()
            db.add(existing)
        else:
            db.add(
                CourseCoInstructor(
                    course_id=invitation.course_id,
                    user_id=invitee_id,
                    role=invitation.role,
                    status="active",
                    added_by=invitation.inviter_id,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )
            )

    invitation.updated_at = datetime.utcnow()

    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    return invitation


@router.delete("/{invitation_id}")
def delete_invitation(
    invitation_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    invitation = db.execute(select(Invitation).where(Invitation.id == invitation_id)).scalar_one_or_none()
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found")

    if user.role != "admin" and invitation.inviter_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    db.delete(invitation)
    db.commit()
    return {"status": "ok"}
