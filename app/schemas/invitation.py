from datetime import datetime

from pydantic import BaseModel, EmailStr


class InvitationCreate(BaseModel):
    course_id: str
    invitee_email: EmailStr
    invitee_id: str | None = None
    role: str | None = None


class InvitationUpdate(BaseModel):
    status: str | None = None
    invitee_id: str | None = None
    role: str | None = None


class InvitationOut(BaseModel):
    id: str
    course_id: str
    inviter_id: str
    invitee_id: str | None = None
    invitee_email: EmailStr
    role: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime
