from datetime import datetime

from pydantic import BaseModel


class MentorCourseAssignmentCreate(BaseModel):
    mentor_id: str
    course_id: str
    institution_match: bool | None = None


class MentorCourseAssignmentUpdate(BaseModel):
    status: str | None = None
    unassigned_at: datetime | None = None
    institution_match: bool | None = None


class MentorCourseAssignmentOut(BaseModel):
    id: str
    mentor_id: str
    course_id: str
    assigned_by: str | None = None
    status: str
    institution_match: bool | None = None
    assigned_at: datetime
    unassigned_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
