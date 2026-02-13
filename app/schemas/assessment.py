from datetime import datetime

from pydantic import BaseModel


class AssessmentCreate(BaseModel):
    course_id: str
    title: str
    description: str | None = None


class AssessmentUpdate(BaseModel):
    title: str | None = None
    description: str | None = None


class AssessmentOut(BaseModel):
    id: str
    course_id: str
    title: str
    description: str | None = None
    created_by: str | None = None
    instructor_id: str | None = None
    instructor_name: str | None = None
    status: str | None = None
    created_at: datetime


class AssessmentQuestionCreate(BaseModel):
    prompt: str
    options: list[str] | dict | None = None
    answer: str | None = None


class AssessmentQuestionOut(BaseModel):
    id: str
    assessment_id: str
    prompt: str
    options: list[str] | dict | None = None
    answer: str | None = None


class AssessmentSubmissionCreate(BaseModel):
    answers: dict | None = None


class AssessmentSubmissionOut(BaseModel):
    id: str
    assessment_id: str
    user_id: str
    answers: dict | None = None
    score: int | None = None
    created_at: datetime
