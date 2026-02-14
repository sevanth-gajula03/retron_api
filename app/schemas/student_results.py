from datetime import datetime

from pydantic import BaseModel


class StudentModuleQuizAttemptOut(BaseModel):
    attempt_id: str
    module_id: str
    module_title: str | None = None
    course_id: str
    course_title: str | None = None
    started_at: datetime
    submitted_at: datetime | None = None
    score: int | None = None
    max_score: int | None = None
    created_at: datetime


class StudentAssessmentSubmissionOut(BaseModel):
    submission_id: str
    assessment_id: str
    assessment_title: str | None = None
    course_id: str
    course_title: str | None = None
    created_at: datetime
    score: int | None = None
    answer_count: int
