from datetime import datetime, timedelta
import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy import desc, delete, select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.announcement import Announcement
from app.models.assessment import Assessment, AssessmentSubmission
from app.models.assessment_access import AssessmentAccess
from app.models.course import Course
from app.models.course_co_instructor import CourseCoInstructor
from app.models.course_progress import CourseProgress
from app.models.enrollment import Enrollment
from app.models.invitation import Invitation
from app.models.mentor_assignment import MentorAssignment
from app.models.mentor_course_assignment import MentorCourseAssignment
from app.models.password_setup_token import PasswordSetupToken
from app.models.section import Section
from app.models.user import User
from app.models.module import Module
from app.models.module_quiz_attempt import ModuleQuizAttempt
from app.schemas.user import UserOut, UserProvisionRequest, UserProvisionResponse, UserUpdate
from app.schemas.student_results import StudentAssessmentSubmissionOut, StudentModuleQuizAttemptOut
from app.services.email_service import send_password_setup_email
from app.services.user_service import create_user, get_user_by_email


router = APIRouter(prefix="/users", tags=["users"])

ALLOWED_PROVISION_ROLES = {"student", "instructor", "partner_instructor", "guest"}


def _hash_setup_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _send_setup_link(db: Session, user: User) -> None:
    raw_token = secrets.token_urlsafe(48)
    token_row = PasswordSetupToken(
        user_id=user.id,
        token_hash=_hash_setup_token(raw_token),
        expires_at=datetime.utcnow() + timedelta(minutes=settings.password_setup_token_expire_minutes),
    )
    db.add(token_row)
    db.commit()

    setup_link = f"{settings.frontend_base_url.rstrip('/')}/reset-password?token={raw_token}"
    try:
        send_password_setup_email(user.email, setup_link)
    except HTTPException:
        db.delete(token_row)
        db.commit()
        raise


@router.get("", response_model=list[UserOut])
def list_users(
    role: str | None = None,
    ids: str | None = Query(default=None, description="Comma-separated user ids"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    query = select(User)

    if user.role != "admin":
        allowed_roles = {"student", "instructor", "partner_instructor", "guest"}
        if role and role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    if role:
        query = query.where(User.role == role)

    if ids:
        parsed = [item.strip() for item in ids.split(",") if item.strip()]
        if parsed:
            query = query.where(User.id.in_(parsed))

    return db.execute(query).scalars().all()


@router.get("/me", response_model=UserOut)
def get_me(user=Depends(get_current_user)):
    return user


@router.patch("/me", response_model=UserOut)
def update_me(payload: UserUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    data = payload.model_dump(exclude_unset=True)
    if "role" in data or "status" in data:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot update role/status")
    for key, value in data.items():
        setattr(user, key, value)
    user.updated_at = datetime.utcnow()
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/provision", response_model=UserProvisionResponse)
def provision_user(
    payload: UserProvisionRequest,
    db: Session = Depends(get_db),
    _=Depends(require_roles("admin")),
):
    email = str(payload.email).strip().lower()
    role = payload.role.strip().lower()

    if not email.endswith("@gmail.com"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only @gmail.com email addresses are allowed",
        )

    if role not in ALLOWED_PROVISION_ROLES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid role",
        )

    existing = get_user_by_email(db, email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = create_user(
        db,
        email=email,
        password=secrets.token_urlsafe(24),
        name=payload.name,
        role=role,
        password_setup_completed=False,
    )

    try:
        _send_setup_link(db, user)
    except HTTPException:
        db.delete(user)
        db.commit()
        raise

    return UserProvisionResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        status=user.status,
        message="User created and password setup email sent",
    )


@router.post("/{user_id}/resend-setup-email")
def resend_setup_email(user_id: str, db: Session = Depends(get_db), _=Depends(require_roles("admin"))):
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    _send_setup_link(db, user)
    return {"status": "ok", "message": "Password setup email resent"}


@router.patch("/{user_id}", response_model=UserOut)
def update_user(user_id: str, payload: UserUpdate, db: Session = Depends(get_db), actor=Depends(get_current_user)):
    target = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    data = payload.model_dump(exclude_unset=True)

    if actor.role != "admin":
        if actor.role != "instructor":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

        allowed_fields = {"banned_from"}
        if any(key not in allowed_fields for key in data.keys()):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

        if target.role not in ["student", "guest"]:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Can only update students")

        if data.get("banned_from"):
            instructor_course_ids = [
                row[0]
                for row in db.execute(select(Course.id).where(Course.instructor_id == actor.id)).all()
            ]
            if any(course_id not in instructor_course_ids for course_id in data["banned_from"]):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

            enrollment_course_ids = [
                row[0]
                for row in db.execute(
                    select(Enrollment.course_id).where(Enrollment.user_id == target.id)
                ).all()
            ]
            missing = [course_id for course_id in data["banned_from"] if course_id not in enrollment_course_ids]
            if missing:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Student is not enrolled in one or more courses",
                )

    for key, value in data.items():
        setattr(target, key, value)
    target.updated_at = datetime.utcnow()
    db.add(target)
    db.commit()
    db.refresh(target)
    return target


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: str, db: Session = Depends(get_db), user=Depends(get_current_user)):
    target = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.role != "admin" and user.id != target.id:
        if user.role not in ["instructor", "partner_instructor"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    return target


@router.get("/{user_id}/module-quiz-attempts", response_model=list[StudentModuleQuizAttemptOut])
def list_student_module_quiz_attempts(
    user_id: str,
    db: Session = Depends(get_db),
    actor=Depends(require_roles("admin", "instructor")),
):
    target = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    query = (
        select(ModuleQuizAttempt, Module, Course)
        .join(Module, Module.id == ModuleQuizAttempt.module_id)
        .join(Section, Section.id == Module.section_id)
        .join(Course, Course.id == Section.course_id)
        .where(ModuleQuizAttempt.user_id == user_id)
        .order_by(desc(ModuleQuizAttempt.created_at))
    )
    if actor.role == "instructor":
        query = query.where(Course.instructor_id == actor.id)

    rows = db.execute(query).all()
    results: list[StudentModuleQuizAttemptOut] = []
    for attempt, module, course in rows:
        results.append(
            StudentModuleQuizAttemptOut(
                attempt_id=attempt.id,
                module_id=module.id,
                module_title=module.title,
                course_id=course.id,
                course_title=course.title,
                started_at=attempt.started_at,
                submitted_at=attempt.submitted_at,
                score=attempt.score,
                max_score=attempt.max_score,
                created_at=attempt.created_at,
            )
        )
    return results


@router.get("/{user_id}/assessment-submissions", response_model=list[StudentAssessmentSubmissionOut])
def list_student_assessment_submissions(
    user_id: str,
    db: Session = Depends(get_db),
    actor=Depends(require_roles("admin", "instructor", "partner_instructor")),
):
    target = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # IMPORTANT: Do not select the Assessment ORM entity here.
    # This codebase has an Assessment model that may include columns not present
    # in older DBs. Selecting the entity would attempt to load all mapped columns.
    query = (
        select(
            AssessmentSubmission,
            Assessment.id.label("assessment_id"),
            Assessment.title.label("assessment_title"),
            Assessment.course_id.label("course_id"),
            Course.title.label("course_title"),
        )
        .join(Assessment, Assessment.id == AssessmentSubmission.assessment_id)
        .join(Course, Course.id == Assessment.course_id)
        .where(AssessmentSubmission.user_id == user_id)
        .order_by(desc(AssessmentSubmission.created_at))
    )
    if actor.role in ["instructor", "partner_instructor"]:
        query = query.where(Course.instructor_id == actor.id)

    rows = db.execute(query).all()
    results: list[StudentAssessmentSubmissionOut] = []
    for submission, assessment_id, assessment_title, course_id, course_title in rows:
        answers = submission.answers if isinstance(submission.answers, dict) else {}
        results.append(
            StudentAssessmentSubmissionOut(
                submission_id=submission.id,
                assessment_id=assessment_id,
                assessment_title=assessment_title,
                course_id=course_id,
                course_title=course_title,
                created_at=submission.created_at,
                score=submission.score,
                answer_count=len(list(answers.keys())),
            )
        )
    return results


@router.delete("/{user_id}")
def delete_user(user_id: str, db: Session = Depends(get_db), _=Depends(require_roles("admin"))):
    user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    has_owned_courses = db.execute(
        select(Course.id).where(Course.instructor_id == user.id).limit(1)
    ).scalar_one_or_none()
    if has_owned_courses:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete user who owns courses. Reassign or delete their courses first.",
        )

    try:
        now = datetime.utcnow()
        db.execute(delete(PasswordSetupToken).where(PasswordSetupToken.user_id == user.id))
        db.execute(delete(Enrollment).where(Enrollment.user_id == user.id))
        db.execute(delete(CourseProgress).where(CourseProgress.user_id == user.id))
        db.execute(delete(AssessmentSubmission).where(AssessmentSubmission.user_id == user.id))
        db.execute(delete(AssessmentAccess).where(AssessmentAccess.student_id == user.id))
        db.execute(
            update(AssessmentAccess)
            .where(AssessmentAccess.mentor_id == user.id)
            .values(mentor_id=None, updated_at=now)
        )
        db.execute(
            update(AssessmentAccess)
            .where(AssessmentAccess.granted_by == user.id)
            .values(granted_by=None, updated_at=now)
        )
        db.execute(
            delete(MentorAssignment).where(
                (MentorAssignment.student_id == user.id) | (MentorAssignment.mentor_id == user.id)
            )
        )
        db.execute(
            update(MentorAssignment)
            .where(MentorAssignment.assigned_by == user.id)
            .values(assigned_by=None, updated_at=now)
        )
        db.execute(delete(MentorCourseAssignment).where(MentorCourseAssignment.mentor_id == user.id))
        db.execute(
            update(MentorCourseAssignment)
            .where(MentorCourseAssignment.assigned_by == user.id)
            .values(assigned_by=None, updated_at=now)
        )
        db.execute(delete(CourseCoInstructor).where(CourseCoInstructor.user_id == user.id))
        db.execute(
            update(CourseCoInstructor)
            .where(CourseCoInstructor.added_by == user.id)
            .values(added_by=None, updated_at=now)
        )
        db.execute(
            delete(Invitation).where(
                (Invitation.inviter_id == user.id) | (Invitation.invitee_id == user.id)
            )
        )
        db.execute(delete(Announcement).where(Announcement.author_id == user.id))
        db.execute(
            update(User)
            .where(User.mentor_id == user.id)
            .values(mentor_id=None, updated_at=now)
        )

        db.delete(user)
        db.commit()
        return {"status": "ok"}
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User cannot be deleted due to remaining linked records",
        )
