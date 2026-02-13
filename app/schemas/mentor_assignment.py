from datetime import datetime

from pydantic import BaseModel


class MentorAssignmentCreate(BaseModel):
    student_id: str
    mentor_id: str
    college: str | None = None


class MentorAssignmentUpdate(BaseModel):
    status: str | None = None
    unassigned_at: datetime | None = None


class MentorAssignmentOut(BaseModel):
    id: str
    student_id: str
    mentor_id: str
    assigned_by: str | None = None
    status: str
    college: str | None = None
    assigned_at: datetime
    unassigned_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
