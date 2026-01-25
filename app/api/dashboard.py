from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.company_session import get_company_db
from app.models.company_db.site import Site
from app.models.company_db.department import Department
from app.models.company_db.audit import Audit
from app.models.company_db.finding import Finding

from sqlalchemy import func
from app.models.company_db.audit_team import AuditTeam
from app.models.user import User
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/stats")
def dashboard_stats(
    db: Session = Depends(get_company_db),
    current_user: User = Depends(get_current_user)
):
    stats = {
        "sites": 0,
        "departments": 0,
        "audits": {
            "total": 0,
            "by_status": {}
        },
        "findings": {
            "total": 0,
            "by_status": {},
            "by_risk": {"high": 0, "medium": 0, "low": 0}
        }
    }

    # 1. Base Queries
    audit_q = db.query(Audit)
    finding_q = db.query(Finding)

    # 2. Basic Counts (Always global for Admin, but maybe filtered for Auditor?)
    # Requirement: "Auditor: Focused view on assigned tasks". 
    # But usually dashboard also shows context. 
    # Let's stick to plan: Admin = Global, Auditor = Assigned Only for ACTIONABLE items.
    # Sites/Depts are global context, so Auditor sees total count usually.
    stats["sites"] = db.query(Site).count()
    stats["departments"] = db.query(Department).count()

    # 3. Role Filtering
    if current_user.role != "admin":
        # Filter Audits: Assigned via AuditTeam
        assigned_audit_ids = db.query(AuditTeam.audit_id).filter(
            AuditTeam.auditor_id == current_user.id
        ).subquery()
        audit_q = audit_q.filter(Audit.id.in_(assigned_audit_ids))
        
        # Filter Findings: Assigned directly OR belonging to assigned audits?
        # "Auditor View: Show 'My Tasks' (Assigned Audits/Findings)"
        # Usually implies findings assigned TO ME.
        # But if I am an auditor on an audit, do I see all its findings?
        # Current finding.py logic: "Auditors only see findings from assigned audits".
        # So we filter findings by audit assignment access + potentially direct assignment for "My Tasks".
        # Let's count findings from assigned audits as "Visible Findings".
        # And maybe a separate metric for "Assigned To Me".
        # For simplicity of this task, let's filter findings by the same assigned_audit_ids rule 
        # (matching list_findings behavior).
        finding_q = finding_q.filter(Finding.audit_id.in_(assigned_audit_ids))

    # 4. Aggregations (Audits)
    audit_counts = audit_q.with_entities(Audit.status, func.count(Audit.status)).group_by(Audit.status).all()
    stats["audits"]["total"] = sum(c for _, c in audit_counts)
    stats["audits"]["by_status"] = {s: c for s, c in audit_counts if s}

    # 5. Aggregations (Findings)
    finding_counts = finding_q.with_entities(Finding.status, func.count(Finding.status)).group_by(Finding.status).all()
    stats["findings"]["total"] = sum(c for _, c in finding_counts)
    stats["findings"]["by_status"] = {s: c for s, c in finding_counts if s}
    
    # Risk Profile (Open findings only?) - Let's do all for heatmap
    # Simplify risk buckets: Low(1-4), Med(5-12), High(15-25)
    # Risk score = likelihood(1-5) * severity(1-5). Max 25.
    # We can query specific ranges.
    # Or just fetch risk scores and bucket in python if volume is low. 
    # For optimization, let's do SQL case or ranges. 
    # Since sqlite/postgres differences in CASE syntax can be annoying in raw SQL, 
    # let's just count > threshold.
    # High: >= 15
    # Med: 5 <= x < 15
    # Low: < 5
    
    stats["findings"]["by_risk"]["high"] = finding_q.filter(Finding.risk_score >= 15).count()
    stats["findings"]["by_risk"]["medium"] = finding_q.filter(Finding.risk_score >= 5, Finding.risk_score < 15).count()
    stats["findings"]["by_risk"]["low"] = finding_q.filter(Finding.risk_score < 5).count()
    
    # 6. Auditor Specific Extras (Assigned directly to user)
    if current_user.role != "admin":
        my_findings = db.query(Finding).filter(Finding.assigned_to_id == current_user.id, Finding.status != "closed").count()
        stats["my_pending_findings"] = my_findings

    return stats
