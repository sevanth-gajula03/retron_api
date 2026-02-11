from datetime import datetime

from pydantic import BaseModel


class AnnouncementCreate(BaseModel):
    title: str
    body: str
    course_id: str | None = None


class AnnouncementUpdate(BaseModel):
    title: str | None = None
    body: str | None = None


class AnnouncementOut(BaseModel):
    id: str
    title: str
    body: str
    course_id: str | None = None
    author_id: str
    created_at: datetime
