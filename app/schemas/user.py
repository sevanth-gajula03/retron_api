from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserOut(BaseModel):
    id: str
    email: EmailStr
    role: str
    status: str
    name: str | None = None
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    role: str | None = None
    status: str | None = None
    name: str | None = None
