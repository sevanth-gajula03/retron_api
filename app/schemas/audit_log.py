from datetime import datetime

from pydantic import BaseModel


class AuditLogOut(BaseModel):
    id: str
    type: str
    admin_email: str | None = None
    target_user_email: str | None = None
    old_role: str | None = None
    new_role: str | None = None
    reason: str | None = None
    created_at: datetime
