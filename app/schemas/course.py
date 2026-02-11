from datetime import datetime

from pydantic import BaseModel


class CourseCreate(BaseModel):
    title: str
    description: str | None = None
    thumbnail_url: str | None = None


class CourseUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    thumbnail_url: str | None = None


class CourseOut(BaseModel):
    id: str
    title: str
    description: str | None = None
    thumbnail_url: str | None = None
    instructor_id: str
    status: str
    created_at: datetime
    updated_at: datetime
