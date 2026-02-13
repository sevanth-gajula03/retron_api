from datetime import datetime

from pydantic import BaseModel


class CourseProgressCreate(BaseModel):
    user_id: str | None = None
    course_id: str
    completed_modules: list[str] | None = None
    completed_sections: list[str] | None = None
    module_progress_percentage: int | None = 0
    section_progress_percentage: int | None = 0
    completed_module_count: int | None = 0
    completed_section_count: int | None = 0
    enrolled_at: datetime | None = None
    last_accessed: datetime | None = None


class CourseProgressUpdate(BaseModel):
    completed_modules: list[str] | None = None
    completed_sections: list[str] | None = None
    module_progress_percentage: int | None = None
    section_progress_percentage: int | None = None
    completed_module_count: int | None = None
    completed_section_count: int | None = None
    last_accessed: datetime | None = None


class CourseProgressOut(BaseModel):
    id: str
    user_id: str
    course_id: str
    completed_modules: list[str] | None = None
    completed_sections: list[str] | None = None
    module_progress_percentage: int
    section_progress_percentage: int
    completed_module_count: int
    completed_section_count: int
    enrolled_at: datetime | None = None
    last_accessed: datetime | None = None
    created_at: datetime
    updated_at: datetime
