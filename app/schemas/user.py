from datetime import datetime

from pydantic import BaseModel, EmailStr


class UserOut(BaseModel):
    id: str
    email: EmailStr
    role: str
    status: str
    name: str | None = None
    full_name: str | None = None
    phone: str | None = None
    college: str | None = None
    roll_number: str | None = None
    institution_id: str | None = None
    mentor_id: str | None = None
    banned_from: list[str] | None = None
    permissions: dict | None = None
    guest_access_expiry: datetime | None = None
    password_setup_completed: bool
    created_at: datetime
    updated_at: datetime


class UserUpdate(BaseModel):
    role: str | None = None
    status: str | None = None
    name: str | None = None
    full_name: str | None = None
    phone: str | None = None
    college: str | None = None
    roll_number: str | None = None
    institution_id: str | None = None
    mentor_id: str | None = None
    banned_from: list[str] | None = None
    permissions: dict | None = None
    guest_access_expiry: datetime | None = None


class UserProvisionRequest(BaseModel):
    email: EmailStr
    role: str
    name: str | None = None


class UserProvisionResponse(BaseModel):
    id: str
    email: EmailStr
    role: str
    status: str
    message: str
