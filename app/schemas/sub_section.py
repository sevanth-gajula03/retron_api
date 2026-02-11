from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class SubSectionCreate(BaseModel):
    section_id: str
    title: str
    description: Optional[str] = None
    objectives: Optional[list] = None
    duration: Optional[str] = None
    order: Optional[int] = None


class SubSectionUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    objectives: Optional[list] = None
    duration: Optional[str] = None
    order: Optional[int] = None


class SubSectionOut(BaseModel):
    id: str
    section_id: str
    title: str
    description: Optional[str] = None
    objectives: Optional[list] = None
    duration: Optional[str] = None
    order: int
    created_at: datetime
    updated_at: datetime
