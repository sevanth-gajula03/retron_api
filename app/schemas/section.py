from datetime import datetime

from pydantic import BaseModel


class SectionCreate(BaseModel):
    course_id: str
    title: str
    order: int | None = None


class SectionUpdate(BaseModel):
    title: str | None = None
    order: int | None = None


class SectionOut(BaseModel):
    id: str
    course_id: str
    title: str
    order: int
    created_at: datetime
    updated_at: datetime
