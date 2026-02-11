from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.announcement import Announcement
from app.models.course import Course
from app.schemas.announcement import AnnouncementCreate, AnnouncementOut, AnnouncementUpdate


router = APIRouter(prefix="/announcements", tags=["announcements"])


@router.get("", response_model=list[AnnouncementOut])
def list_announcements(
    course_id: Optional[str] = None,
    db: Session = Depends(get_db),
    _=Depends(get_current_user)
):
    query = select(Announcement)
    if course_id:
        query = query.where(Announcement.course_id == course_id)
    return db.execute(query).scalars().all()


@router.post("", response_model=AnnouncementOut)
def create_announcement(
    payload: AnnouncementCreate,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "instructor"))
):
    if payload.course_id:
        course = db.execute(select(Course).where(Course.id == payload.course_id)).scalar_one_or_none()
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
        if user.role == "instructor" and course.instructor_id != user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    announcement = Announcement(
        title=payload.title,
        body=payload.body,
        course_id=payload.course_id,
        author_id=user.id,
        created_at=datetime.utcnow()
    )
    db.add(announcement)
    db.commit()
    db.refresh(announcement)
    return announcement


@router.patch("/{announcement_id}", response_model=AnnouncementOut)
def update_announcement(
    announcement_id: str,
    payload: AnnouncementUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "instructor"))
):
    announcement = db.execute(select(Announcement).where(Announcement.id == announcement_id)).scalar_one_or_none()
    if not announcement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")
    if user.role == "instructor" and announcement.author_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(announcement, key, value)
    db.add(announcement)
    db.commit()
    db.refresh(announcement)
    return announcement


@router.delete("/{announcement_id}")
def delete_announcement(
    announcement_id: str,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "instructor"))
):
    announcement = db.execute(select(Announcement).where(Announcement.id == announcement_id)).scalar_one_or_none()
    if not announcement:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Announcement not found")
    if user.role == "instructor" and announcement.author_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    db.delete(announcement)
    db.commit()
    return {"status": "ok"}
