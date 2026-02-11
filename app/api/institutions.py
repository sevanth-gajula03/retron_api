from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.db.session import get_db
from app.models.institution import Institution
from app.schemas.institution import InstitutionCreate, InstitutionOut, InstitutionUpdate


router = APIRouter(prefix="/institutions", tags=["institutions"])


@router.get("", response_model=list[InstitutionOut])
def list_institutions(db: Session = Depends(get_db), _=Depends(require_roles("admin"))):
    return db.execute(select(Institution)).scalars().all()


@router.post("", response_model=InstitutionOut)
def create_institution(
    payload: InstitutionCreate,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin"))
):
    institution = Institution(
        name=payload.name,
        location=payload.location,
        contact_email=payload.contact_email,
        contact_phone=payload.contact_phone,
        created_by=user.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(institution)
    db.commit()
    db.refresh(institution)
    return institution


@router.patch("/{institution_id}", response_model=InstitutionOut)
def update_institution(
    institution_id: str,
    payload: InstitutionUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_roles("admin"))
):
    institution = db.execute(
        select(Institution).where(Institution.id == institution_id)
    ).scalar_one_or_none()
    if not institution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution not found")
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(institution, key, value)
    institution.updated_at = datetime.utcnow()
    db.add(institution)
    db.commit()
    db.refresh(institution)
    return institution


@router.delete("/{institution_id}")
def delete_institution(
    institution_id: str,
    db: Session = Depends(get_db),
    _=Depends(require_roles("admin"))
):
    institution = db.execute(
        select(Institution).where(Institution.id == institution_id)
    ).scalar_one_or_none()
    if not institution:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Institution not found")
    db.delete(institution)
    db.commit()
    return {"status": "ok"}
