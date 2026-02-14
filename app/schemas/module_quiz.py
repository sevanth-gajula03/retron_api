from datetime import datetime

from pydantic import BaseModel


class ModuleQuizQuestionPublic(BaseModel):
    index: int
    prompt: str
    options: list[str]
    points: int = 1


class ModuleQuizPublicOut(BaseModel):
    module_id: str
    title: str | None = None
    questions: list[ModuleQuizQuestionPublic]
    max_score: int
    time_limit_seconds: int | None = None


class ModuleQuizAttemptStartOut(BaseModel):
    attempt_id: str
    started_at: datetime
    expires_at: datetime | None = None
    quiz: ModuleQuizPublicOut


class ModuleQuizAttemptSubmitIn(BaseModel):
    # Answers are keyed by question index (stringified for JSON): {"0": 2, "1": 0}
    answers: dict | None = None


class ModuleQuizAttemptSubmitOut(BaseModel):
    attempt_id: str
    score: int
    max_score: int
    submitted_at: datetime


class ModuleQuizAttemptReportOut(BaseModel):
    id: str
    user_id: str
    student_email: str | None = None
    student_name: str | None = None
    started_at: datetime
    submitted_at: datetime | None = None
    score: int | None = None
    max_score: int | None = None
    created_at: datetime
