from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class ModuleCreate(BaseModel):
    section_id: str
    sub_section_id: Optional[str] = None
    title: Optional[str] = None
    type: str
    content: Optional[str] = None
    order: Optional[int] = None


class ModuleUpdate(BaseModel):
    title: Optional[str] = None
    type: Optional[str] = None
    content: Optional[str] = None
    order: Optional[int] = None
    sub_section_id: Optional[str] = None


class ModuleOut(BaseModel):
    id: str
    section_id: str
    sub_section_id: Optional[str] = None
    title: Optional[str] = None
    type: str
    content: Optional[str] = None
    order: int
    created_at: datetime
    updated_at: datetime
