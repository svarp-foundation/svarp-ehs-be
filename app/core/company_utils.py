from fastapi import HTTPException, status
from app.models.user import User

def verify_company_access(resource, user: User):
    """
    Verifies that the resource belongs to the same company as the user.
    Raises 403 Forbidden if not.
    """
    if hasattr(resource, "company_id"):
        if resource.company_id != user.company_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access to this resource is forbidden (Cross-company)"
            )
    return True
