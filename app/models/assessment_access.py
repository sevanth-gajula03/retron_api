from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AssessmentAccess(Base):
    __tablename__ = "assessment_access"
    __table_args__ = (
        UniqueConstraint("student_id", "assessment_id", name="uq_assessment_access_student_assessment"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    student_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    assessment_id: Mapped[str] = mapped_column(String, ForeignKey("assessments.id"), nullable=False)
    mentor_id: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"), nullable=True)
    granted_by: Mapped[str | None] = mapped_column(String, ForeignKey("users.id"), nullable=True)
    granted_by_name: Mapped[str | None] = mapped_column(String, nullable=True)
    assessment_title: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="active", nullable=False)
    granted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
