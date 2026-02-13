from datetime import datetime

from pydantic import BaseModel


class AssessmentAccessCreate(BaseModel):
    student_id: str
    assessment_id: str
    mentor_id: str | None = None
    granted_by: str | None = None
    granted_by_name: str | None = None
    assessment_title: str | None = None
    status: str | None = "active"
    granted_at: datetime | None = None
    expires_at: datetime | None = None


class AssessmentAccessUpdate(BaseModel):
    mentor_id: str | None = None
    granted_by: str | None = None
    granted_by_name: str | None = None
    assessment_title: str | None = None
    status: str | None = None
    granted_at: datetime | None = None
    expires_at: datetime | None = None


class AssessmentAccessOut(BaseModel):
    id: str
    student_id: str
    assessment_id: str
    mentor_id: str | None = None
    granted_by: str | None = None
    granted_by_name: str | None = None
    assessment_title: str | None = None
    status: str
    granted_at: datetime | None = None
    expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
