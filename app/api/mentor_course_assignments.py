from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.course import Course
from app.models.mentor_course_assignment import MentorCourseAssignment
from app.models.user import User
from app.schemas.mentor_course_assignment import (
    MentorCourseAssignmentCreate,
    MentorCourseAssignmentOut,
    MentorCourseAssignmentUpdate,
)


router = APIRouter(prefix="/mentor-course-assignments", tags=["mentor-course-assignments"])


@router.get("", response_model=list[MentorCourseAssignmentOut])
def list_mentor_course_assignments(
    mentor_id: str | None = None,
    course_id: str | None = None,
    status_filter: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    query = select(MentorCourseAssignment)

    if user.role == "partner_instructor":
        query = query.where(MentorCourseAssignment.mentor_id == user.id)
    elif user.role in ["student", "guest"]:
        query = query.where(MentorCourseAssignment.status == "active")

    if mentor_id:
        query = query.where(MentorCourseAssignment.mentor_id == mentor_id)
    if course_id:
        query = query.where(MentorCourseAssignment.course_id == course_id)
    if status_filter:
        query = query.where(MentorCourseAssignment.status == status_filter)

    return db.execute(query).scalars().all()


@router.post("", response_model=MentorCourseAssignmentOut)
def create_mentor_course_assignment(
    payload: MentorCourseAssignmentCreate,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "instructor")),
):
    mentor = db.execute(select(User).where(User.id == payload.mentor_id)).scalar_one_or_none()
    course = db.execute(select(Course).where(Course.id == payload.course_id)).scalar_one_or_none()
    if not mentor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mentor not found")
    if not course:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

    if mentor.role not in ["instructor", "partner_instructor"]:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid mentor role")

    if user.role == "instructor" and course.instructor_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    existing = db.execute(
        select(MentorCourseAssignment).where(
            MentorCourseAssignment.mentor_id == payload.mentor_id,
            MentorCourseAssignment.course_id == payload.course_id,
        )
    ).scalar_one_or_none()
    institution_match = payload.institution_match
    if institution_match is None and mentor.institution_id and course.institution_id:
        institution_match = mentor.institution_id == course.institution_id

    if existing:
        existing.status = "active"
        existing.institution_match = institution_match
        existing.unassigned_at = None
        existing.updated_at = datetime.utcnow()
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    assignment = MentorCourseAssignment(
        mentor_id=payload.mentor_id,
        course_id=payload.course_id,
        assigned_by=user.id,
        status="active",
        institution_match=institution_match,
        assigned_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.post("/assign", response_model=MentorCourseAssignmentOut)
def assign_course_compat(
    payload: MentorCourseAssignmentCreate,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "instructor")),
):
    return create_mentor_course_assignment(payload=payload, db=db, user=user)


@router.patch("/{assignment_id}", response_model=MentorCourseAssignmentOut)
def update_mentor_course_assignment(
    assignment_id: str,
    payload: MentorCourseAssignmentUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    assignment = db.execute(
        select(MentorCourseAssignment).where(MentorCourseAssignment.id == assignment_id)
    ).scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    if user.role == "partner_instructor":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    if user.role == "instructor":
        course = db.execute(select(Course).where(Course.id == assignment.course_id)).scalar_one_or_none()
        if not course or course.instructor_id != user.id:
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


@router.post("/{assignment_id}/unassign", response_model=MentorCourseAssignmentOut)
def unassign_course(
    assignment_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "instructor")),
):
    payload = MentorCourseAssignmentUpdate(status="inactive", unassigned_at=datetime.utcnow())
    return update_mentor_course_assignment(assignment_id=assignment_id, payload=payload, db=db, user=user)


@router.delete("/{assignment_id}")
def delete_mentor_course_assignment(
    assignment_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "instructor")),
):
    assignment = db.execute(
        select(MentorCourseAssignment).where(MentorCourseAssignment.id == assignment_id)
    ).scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    db.delete(assignment)
    db.commit()
    return {"status": "ok"}
