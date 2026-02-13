from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.mentor_assignment import MentorAssignment
from app.models.user import User
from app.schemas.mentor_assignment import MentorAssignmentCreate, MentorAssignmentOut, MentorAssignmentUpdate


router = APIRouter(prefix="/mentor-assignments", tags=["mentor-assignments"])


@router.get("", response_model=list[MentorAssignmentOut])
def list_mentor_assignments(
    student_id: str | None = None,
    mentor_id: str | None = None,
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    query = select(MentorAssignment)

    if user.role in ["student", "guest"]:
        query = query.where(MentorAssignment.student_id == user.id)
    elif user.role == "partner_instructor":
        query = query.where(MentorAssignment.mentor_id == user.id)

    if student_id:
        query = query.where(MentorAssignment.student_id == student_id)
    if mentor_id:
        query = query.where(MentorAssignment.mentor_id == mentor_id)
    if status_filter:
        query = query.where(MentorAssignment.status == status_filter)

    return db.execute(query).scalars().all()


@router.post("", response_model=MentorAssignmentOut)
def create_mentor_assignment(
    payload: MentorAssignmentCreate,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "instructor")),
):
    student = db.execute(select(User).where(User.id == payload.student_id)).scalar_one_or_none()
    mentor = db.execute(select(User).where(User.id == payload.mentor_id)).scalar_one_or_none()
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    if not mentor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mentor not found")

    if student.role not in ["student", "guest"]:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid student role")
    if mentor.role not in ["instructor", "partner_instructor"]:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid mentor role")

    existing = db.execute(
        select(MentorAssignment).where(
            MentorAssignment.student_id == payload.student_id,
            MentorAssignment.mentor_id == payload.mentor_id,
        )
    ).scalar_one_or_none()

    if existing:
        existing.status = "active"
        existing.college = payload.college if payload.college is not None else existing.college
        existing.unassigned_at = None
        existing.updated_at = datetime.utcnow()
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    assignment = MentorAssignment(
        student_id=payload.student_id,
        mentor_id=payload.mentor_id,
        assigned_by=user.id,
        status="active",
        college=payload.college,
        assigned_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.post("/assign", response_model=MentorAssignmentOut)
def assign_mentor_compat(
    payload: MentorAssignmentCreate,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "instructor")),
):
    return create_mentor_assignment(payload=payload, db=db, user=user)


@router.patch("/{assignment_id}", response_model=MentorAssignmentOut)
def update_mentor_assignment(
    assignment_id: str,
    payload: MentorAssignmentUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    assignment = db.execute(select(MentorAssignment).where(MentorAssignment.id == assignment_id)).scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    is_manager = user.role in ["admin", "instructor"]
    is_mentor = user.role == "partner_instructor" and assignment.mentor_id == user.id
    if not (is_manager or is_mentor):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(assignment, key, value)
    assignment.updated_at = datetime.utcnow()

    if assignment.status != "active" and assignment.unassigned_at is None:
        assignment.unassigned_at = datetime.utcnow()

    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.post("/{assignment_id}/unassign", response_model=MentorAssignmentOut)
def unassign_mentor(
    assignment_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "instructor")),
):
    payload = MentorAssignmentUpdate(status="inactive", unassigned_at=datetime.utcnow())
    return update_mentor_assignment(assignment_id=assignment_id, payload=payload, db=db, user=user)


@router.delete("/{assignment_id}")
def delete_mentor_assignment(
    assignment_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "instructor")),
):
    assignment = db.execute(select(MentorAssignment).where(MentorAssignment.id == assignment_id)).scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    db.delete(assignment)
    db.commit()
    return {"status": "ok"}
