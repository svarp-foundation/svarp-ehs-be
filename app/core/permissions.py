from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user
from app.models.user import User

def require_admin(user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return user


def require_admin_or_auditor(user: User = Depends(get_current_user)):
    if user.role not in ["admin", "auditor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    return user


def check_audit_access(user: User, audit_id: int, db: Session) -> bool:
    """
    Returns True if user is admin OR is assigned to the audit.
    Used to enforce auditor-level access control.
    """
    if user.role == "admin":
        return True
    from app.models.company_db.audit_team import AuditTeam
    return db.query(AuditTeam).filter(
        AuditTeam.audit_id == audit_id,
        AuditTeam.auditor_id == user.id
    ).first() is not None

