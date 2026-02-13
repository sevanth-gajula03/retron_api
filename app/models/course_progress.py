from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CourseProgress(Base):
    __tablename__ = "course_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "course_id", name="uq_course_progress_user_course"),
    )

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    course_id: Mapped[str] = mapped_column(String, ForeignKey("courses.id"), nullable=False)
    completed_modules: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    completed_sections: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    module_progress_percentage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    section_progress_percentage: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_module_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_section_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    enrolled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_accessed: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
