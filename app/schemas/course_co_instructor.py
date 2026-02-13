from datetime import datetime

from pydantic import BaseModel


class CourseCoInstructorCreate(BaseModel):
    course_id: str
    user_id: str
    role: str | None = None


class CourseCoInstructorUpdate(BaseModel):
    role: str | None = None
    status: str | None = None


class CourseCoInstructorOut(BaseModel):
    id: str
    course_id: str
    user_id: str
    role: str | None = None
    status: str
    added_by: str | None = None
    created_at: datetime
    updated_at: datetime
