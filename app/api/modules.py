from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.db.session import get_db
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.module import Module
from app.models.module_quiz_attempt import ModuleQuizAttempt
from app.models.section import Section
from app.models.sub_section import SubSection
from app.models.user import User
from app.schemas.module import ModuleCreate, ModuleOut, ModuleUpdate
from app.schemas.module_quiz import (
    ModuleQuizAttemptReportOut,
    ModuleQuizAttemptStartOut,
    ModuleQuizAttemptSubmitIn,
    ModuleQuizAttemptSubmitOut,
    ModuleQuizPublicOut,
    ModuleQuizQuestionPublic,
)


router = APIRouter(prefix="/modules", tags=["modules"])


def _ensure_module_access(db: Session, module: Module, user):
    """Raise HTTPException if user cannot access the module."""
    section = db.execute(select(Section).where(Section.id == module.section_id)).scalar_one_or_none()
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

    return course


def _normalize_quiz_data(raw_quiz_data) -> list[dict]:
    """Normalize quiz_data into a predictable list of dicts.

    Expected instructor format (stored in modules.quiz_data):
    [{
      "question": "...",
      "options": ["A", "B", "C", "D"],
      "correctOption": 0,
      "points": 1,
      "explanation": "..." (optional)
    }]
    """
    if not raw_quiz_data or not isinstance(raw_quiz_data, list):
        return []
    normalized: list[dict] = []
    for item in raw_quiz_data:
        if not isinstance(item, dict):
            continue
        prompt = str(item.get("question") or item.get("prompt") or "").strip()
        options = item.get("options")
        if not isinstance(options, list):
            options = []
        options = [str(o or "").strip() for o in options]
        points = item.get("points")
        try:
            points = int(points) if points is not None else 1
        except (TypeError, ValueError):
            points = 1
        if points < 1:
            points = 1
        correct = item.get("correctOption")
        try:
            correct = int(correct) if correct is not None else None
        except (TypeError, ValueError):
            correct = None

        normalized.append(
            {
                "question": prompt,
                "options": options,
                "points": points,
                "correctOption": correct,
                "explanation": item.get("explanation"),
            }
        )
    return normalized


def _build_public_quiz(module: Module) -> ModuleQuizPublicOut:
    questions_raw = _normalize_quiz_data(module.quiz_data)
    public_questions: list[ModuleQuizQuestionPublic] = []
    max_score = 0

    for idx, q in enumerate(questions_raw):
        points = int(q.get("points") or 1)
        max_score += points
        public_questions.append(
            ModuleQuizQuestionPublic(
                index=idx,
                prompt=str(q.get("question") or "").strip(),
                options=list(q.get("options") or []),
                points=points,
            )
        )

    return ModuleQuizPublicOut(
        module_id=module.id,
        title=module.title,
        questions=public_questions,
        max_score=max_score,
        time_limit_seconds=getattr(module, "time_limit_seconds", None),
    )


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
        quiz_data=payload.quiz_data,
        time_limit_seconds=payload.time_limit_seconds,
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
    # Never expose quiz answers to students/guests via the generic module endpoint.
    if user.role in ["student", "guest"]:
        module.quiz_data = None
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
    modules = db.execute(
        select(Module).where(Module.section_id == section_id, Module.sub_section_id.is_(None))
    ).scalars().all()

    # Never expose quiz answers to students/guests via the generic module list.
    if user.role in ["student", "guest"]:
        for mod in modules:
            mod.quiz_data = None

    return modules


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
    modules = db.execute(select(Module).where(Module.sub_section_id == sub_section_id)).scalars().all()

    # Never expose quiz answers to students/guests via the generic module list.
    if user.role in ["student", "guest"]:
        for mod in modules:
            mod.quiz_data = None

    return modules


@router.get("/{module_id}/quiz", response_model=ModuleQuizPublicOut)
def get_module_quiz_public(
    module_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "instructor", "student", "guest")),
):
    module = db.execute(select(Module).where(Module.id == module_id)).scalar_one_or_none()
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    if module.type != "quiz":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Module is not a quiz")

    _ensure_module_access(db, module, user)

    # Return sanitized quiz payload (no correct answers).
    return _build_public_quiz(module)


@router.post("/{module_id}/quiz-attempts", response_model=ModuleQuizAttemptStartOut)
def start_module_quiz_attempt(
    module_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_roles("student", "guest")),
):
    module = db.execute(select(Module).where(Module.id == module_id)).scalar_one_or_none()
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    if module.type != "quiz":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Module is not a quiz")

    _ensure_module_access(db, module, user)

    attempt = ModuleQuizAttempt(
        module_id=module.id,
        user_id=user.id,
        started_at=datetime.utcnow(),
        created_at=datetime.utcnow(),
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    time_limit_seconds = getattr(module, "time_limit_seconds", None)
    expires_at = None
    if time_limit_seconds is not None:
        try:
            limit = int(time_limit_seconds)
        except (TypeError, ValueError):
            limit = 0
        if limit > 0:
            expires_at = attempt.started_at + timedelta(seconds=limit)

    # Ensure timestamps are timezone-aware in JSON (+00:00) so JS timers
    # don't misinterpret them as local time.
    started_at_out = attempt.started_at.replace(tzinfo=timezone.utc) if attempt.started_at else None
    expires_at_out = expires_at.replace(tzinfo=timezone.utc) if expires_at else None

    return ModuleQuizAttemptStartOut(
        attempt_id=attempt.id,
        started_at=started_at_out or datetime.now(timezone.utc),
        expires_at=expires_at_out,
        quiz=_build_public_quiz(module),
    )


@router.post(
    "/{module_id}/quiz-attempts/{attempt_id}/submit",
    response_model=ModuleQuizAttemptSubmitOut,
)
def submit_module_quiz_attempt(
    module_id: str,
    attempt_id: str,
    payload: ModuleQuizAttemptSubmitIn,
    db: Session = Depends(get_db),
    user=Depends(require_roles("student", "guest")),
):
    module = db.execute(select(Module).where(Module.id == module_id)).scalar_one_or_none()
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")
    if module.type != "quiz":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Module is not a quiz")

    _ensure_module_access(db, module, user)

    attempt = db.execute(
        select(ModuleQuizAttempt).where(
            ModuleQuizAttempt.id == attempt_id,
            ModuleQuizAttempt.module_id == module.id,
            ModuleQuizAttempt.user_id == user.id,
        )
    ).scalar_one_or_none()
    if attempt is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found")
    if attempt.submitted_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Attempt already submitted")

    # Enforce optional time limit (with small grace window).
    time_limit_seconds = getattr(module, "time_limit_seconds", None)
    if time_limit_seconds is not None:
        try:
            limit = int(time_limit_seconds)
        except (TypeError, ValueError):
            limit = 0
        if limit > 0 and attempt.started_at is not None:
            grace_seconds = 5
            expires_at = attempt.started_at + timedelta(seconds=limit)
            if datetime.utcnow() > (expires_at + timedelta(seconds=grace_seconds)):
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Time limit exceeded")

    quiz = _normalize_quiz_data(module.quiz_data)
    if not quiz:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Quiz has no questions")

    raw_answers = payload.answers or {}
    if not isinstance(raw_answers, dict):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid answers")

    # Normalize answer keys to stringified indices.
    answers: dict[str, int] = {}
    for k, v in raw_answers.items():
        try:
            key_str = str(int(k))
        except (TypeError, ValueError):
            continue
        try:
            answers[key_str] = int(v)
        except (TypeError, ValueError):
            continue

    score = 0
    max_score = 0
    for idx, q in enumerate(quiz):
        points = int(q.get("points") or 1)
        max_score += points
        correct = q.get("correctOption")
        if correct is None:
            continue
        selected = answers.get(str(idx), None)
        if selected is None:
            continue
        if int(selected) == int(correct):
            score += points

    attempt.answers = answers
    attempt.score = score
    attempt.max_score = max_score
    attempt.submitted_at = datetime.utcnow()
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    submitted_at = attempt.submitted_at
    if submitted_at is None:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Submission not saved")

    return ModuleQuizAttemptSubmitOut(
        attempt_id=attempt.id,
        score=attempt.score or 0,
        max_score=attempt.max_score or 0,
        submitted_at=submitted_at,
    )


@router.get("/{module_id}/quiz-attempts", response_model=list[ModuleQuizAttemptReportOut])
def list_module_quiz_attempts(
    module_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "instructor")),
):
    module = db.execute(select(Module).where(Module.id == module_id)).scalar_one_or_none()
    if module is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")

    course = _ensure_module_access(db, module, user)
    if user.role == "instructor" and course.instructor_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    rows = db.execute(
        select(ModuleQuizAttempt, User)
        .join(User, User.id == ModuleQuizAttempt.user_id)
        .where(ModuleQuizAttempt.module_id == module.id)
        .order_by(desc(ModuleQuizAttempt.created_at))
    ).all()

    results: list[ModuleQuizAttemptReportOut] = []
    for attempt, u in rows:
        results.append(
            ModuleQuizAttemptReportOut(
                id=attempt.id,
                user_id=attempt.user_id,
                student_email=getattr(u, "email", None),
                student_name=getattr(u, "full_name", None) or getattr(u, "name", None),
                started_at=attempt.started_at,
                submitted_at=attempt.submitted_at,
                score=attempt.score,
                max_score=attempt.max_score,
                created_at=attempt.created_at,
            )
        )

    return results
