from datetime import datetime

from pydantic import BaseModel


class InstitutionCreate(BaseModel):
    name: str
    location: str
    contact_email: str
    contact_phone: str


class InstitutionUpdate(BaseModel):
    name: str | None = None
    location: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None


class InstitutionOut(BaseModel):
    id: str
    name: str
    location: str
    contact_email: str
    contact_phone: str
    created_by: str | None = None
    created_at: datetime
    updated_at: datetime
