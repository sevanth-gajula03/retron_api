from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class MentorAssignment(Base):
    __tablename__ = "mentor_assignments"
    __table_args__ = (
        UniqueConstraint("student_id", "mentor_id", name="uq_mentor_assignment_student_mentor"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    student_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    mentor_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    assigned_by: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"), nullable=True)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)
    college: Mapped[str | None] = mapped_column(String, nullable=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    unassigned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
