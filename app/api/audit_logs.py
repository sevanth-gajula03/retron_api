from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import require_roles
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogOut


router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@router.get("", response_model=list[AuditLogOut])
def list_audit_logs(db: Session = Depends(get_db), _=Depends(require_roles("admin"))):
    return db.execute(select(AuditLog).order_by(AuditLog.created_at.desc())).scalars().all()
