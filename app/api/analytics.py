from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.user import User


router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/admin")
def admin_analytics(db: Session = Depends(get_db), _=Depends(require_roles("admin"))):
    total_students = db.execute(
        select(func.count()).select_from(User).where(User.role == "student")
    ).scalar_one()
    total_instructors = db.execute(
        select(func.count()).select_from(User).where(User.role.in_(["instructor", "partner_instructor"]))
    ).scalar_one()
    total_courses = db.execute(select(func.count()).select_from(Course)).scalar_one()
    total_enrollments = db.execute(select(func.count()).select_from(Enrollment)).scalar_one()

    return {
        "totalStudents": total_students,
        "totalInstructors": total_instructors,
        "totalCourses": total_courses,
        "totalEnrollments": total_enrollments
    }


@router.get("/instructor")
def instructor_analytics(db: Session = Depends(get_db), user=Depends(require_roles("instructor", "partner_instructor"))):
    total_courses = db.execute(
        select(func.count()).select_from(Course).where(Course.instructor_id == user.id)
    ).scalar_one()
    total_enrollments = db.execute(
        select(func.count()).select_from(Enrollment).join(Course, Course.id == Enrollment.course_id)
        .where(Course.instructor_id == user.id)
    ).scalar_one()
    total_students = db.execute(
        select(func.count(func.distinct(Enrollment.user_id))).select_from(Enrollment)
        .join(Course, Course.id == Enrollment.course_id)
        .where(Course.instructor_id == user.id)
    ).scalar_one()

    return {
        "totalCourses": total_courses,
        "totalStudents": total_students,
        "totalEnrollments": total_enrollments,
        "avgCompletion": 0
    }


@router.get("/guest")
def guest_analytics(_user=Depends(get_current_user)):
    return {
        "students": {"total": 0, "active": 0, "suspended": 0, "newThisMonth": 0, "growth": 0},
        "instructors": {"total": 0, "active": 0, "suspended": 0, "newThisMonth": 0, "growth": 0},
        "courses": {"total": 0, "published": 0, "draft": 0, "archived": 0},
        "assessments": {"total": 0, "active": 0, "completed": 0, "averageScore": 0, "submissions": 0},
        "announcements": {"total": 0, "pinned": 0, "views": 0}
    }
