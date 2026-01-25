from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.schemas.department import DepartmentCreate, DepartmentResponse
from app.models.company_db.department import Department
from app.db.company_session import get_company_db
from app.models.company_db.site import Site
from app.core.dependencies import get_current_user
from app.core.permissions import require_admin
from app.models.user import User

router = APIRouter(prefix="/department", tags=["Department"], dependencies=[Depends(get_current_user)])

@router.post("/create")
def create_department(
    data: DepartmentCreate,
    _: User = Depends(require_admin),
    db: Session = Depends(get_company_db)
):

    # 🔥 Validate site existence
    site = db.query(Site).filter(Site.id == data.site_id).first()
    if not site:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid site_id: Site does not exist")

    # Check for duplicate name in same site
    existing = db.query(Department).filter(
        Department.site_id == data.site_id,
        Department.name == data.name
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Department with this name already exists in this site")

    new_dep = Department(
        name=data.name,
        site_id=data.site_id
    )

    db.add(new_dep)
    db.commit()
    db.refresh(new_dep)

    return new_dep

@router.get("/all", response_model=list[DepartmentResponse])
def get_departments(db: Session = Depends(get_company_db)):
    deps = db.query(Department).all()
    
    # Check for findings usage
    # Ideally we'd do a join/count query, but for now simple loop is fine given department count is usually low
    from app.models.company_db.finding import Finding
    
    results = []
    for d in deps:
        has_findings = db.query(Finding).filter(Finding.area == d.name).count() > 0
        results.append(DepartmentResponse(
            id=d.id, 
            name=d.name, 
            site_id=d.site_id, 
            has_findings=has_findings
        ))
        
    return results


@router.delete("/{dep_id}")
def delete_department(
    dep_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_company_db)
):
    dep = db.query(Department).filter(Department.id == dep_id).first()
    if not dep:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Department not found")

    # 🔒 Check dependencies: Findings (by area name match)
    from app.models.company_db.finding import Finding
    if db.query(Finding).filter(Finding.area == dep.name).count() > 0:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Cannot delete department with active findings (area match)")

    db.delete(dep)
    db.commit()
    return {"message": "Department deleted"}
