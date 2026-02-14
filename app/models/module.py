from datetime import datetime
from uuid import uuid4

from typing import Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Module(Base):
    __tablename__ = "modules"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid4()))
    section_id: Mapped[str] = mapped_column(String, ForeignKey("sections.id"), nullable=False)
    sub_section_id: Mapped[Optional[str]] = mapped_column(String, ForeignKey("sub_sections.id"), nullable=True)
    title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    type: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # For quiz modules, this stores the full quiz (including correct answers).
    # Student-facing APIs must not return the correct answers.
    quiz_data: Mapped[Optional[list[dict]]] = mapped_column(JSON, nullable=True)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
