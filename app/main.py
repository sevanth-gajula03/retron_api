from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.announcements import router as announcements_router
from app.api.assessment_access import router as assessment_access_router
from app.api.audit_logs import router as audit_logs_router
from app.api.analytics import router as analytics_router
from app.api.assessments import router as assessments_router
from app.api.auth import router as auth_router
from app.api.course_progress import router as course_progress_router
from app.api.courses import router as courses_router
from app.api.enrollments import router as enrollments_router
from app.api.health import router as health_router
from app.api.institutions import router as institutions_router
from app.api.invitations import router as invitations_router
from app.api.mentor_assignments import router as mentor_assignments_router
from app.api.mentor_course_assignments import router as mentor_course_assignments_router
from app.api.modules import router as modules_router
from app.api.sections import router as sections_router
from app.api.sub_sections import router as sub_sections_router
from app.api.users import router as users_router
from app.core.config import settings


app = FastAPI(title="LMS Backend")


cors_origins = settings.cors_origin_list or ["http://localhost:5173"]
if cors_origins == ["*"]:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=".*",
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )


app.include_router(health_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(courses_router)
app.include_router(sections_router)
app.include_router(modules_router)
app.include_router(sub_sections_router)
app.include_router(announcements_router)
app.include_router(audit_logs_router)
app.include_router(analytics_router)
app.include_router(assessments_router)
app.include_router(assessment_access_router)
app.include_router(course_progress_router)
app.include_router(enrollments_router)
app.include_router(institutions_router)
app.include_router(invitations_router)
app.include_router(mentor_assignments_router)
app.include_router(mentor_course_assignments_router)
