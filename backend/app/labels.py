"""Display labels for every enumerated value the UI shows. Single source for the frontend (via GET /api/options),
so option lists and wording are not duplicated in React. Values without a label are shown humanized."""
from typing import get_args

from app.engine import RULES, SEVERITY_POINTS
from app.models import (
    OPPORTUNITY_STAGES, AgreementStatus, FinanceType, MilestoneStatus, PartnerStatus, RecordStatus, RenewalStatus,
    ReportCreate, SignedCopyStatus,
)
from app.documents import DocumentKind, ScopeDimension
from app.reviews import ReviewDecision

LABELS: dict[str, dict[str, str]] = {
    "partner_status": {"prospect": "Prospect", "qualification": "Qualification", "active": "Active", "on_hold": "On hold", "closed": "Closed"},
    "agreement_status": {"draft": "Draft", "under_review": "Under review", "active": "Active", "expired": "Expired", "closed": "Closed"},
    "signed_copy": {"received": "Received", "pending": "Pending", "unknown": "Not confirmed"},
    "renewal_status": {"none": "Not started", "in_progress": "Renewal in progress", "renewed": "Renewed", "not_renewing": "Not renewing"},
    "project_status": {"planned": "Planned", "active": "Active", "on_hold": "On hold", "completed": "Completed", "closed": "Closed"},
    "milestone_status": {"planned": "Planned", "in_progress": "In progress", "completed": "Completed", "missed": "Missed", "cancelled": "Cancelled"},
    # Pipeline board wording (Tata STRIVE lifecycle).
    "opportunity_stage": {"identified": "Opportunity", "qualification": "Qualification", "proposal": "Proposal", "approval": "Approval",
                          "agreement": "MOU", "active": "Implementation", "renewal": "Renewal", "closed": "Closure"},
    "finance_record_type": {"budget": "Budgets", "fund_received": "Funds received", "invoice": "Invoices",
                            "utilization_certificate": "Utilization certificates"},
    "document_kind": {"mou": "MOU", "addendum": "Addendum"},
    "report_type": {"monthly": "Monthly", "quarterly": "Quarterly", "impact": "Impact", "other": "Other"},
    "report_status": {"planned": "Planned", "due": "Due", "submitted": "Submitted", "overdue": "Overdue", "accepted": "Accepted"},
    "alert_category": {"agreements": "Agreements", "pipeline": "Pipeline", "projects": "Projects & milestones", "reporting": "Reporting",
                       "finance": "Finance", "tasks": "Tasks", "data_quality": "Data quality"},
    "alert_severity": {"overdue": "Overdue", "risk": "Risk", "due_soon": "Due soon", "missing_data": "Missing data"},
    "review_decision": {"acknowledged": "Acknowledged", "deferred": "Deferred", "dismissed": "Dismissed", "task_created": "Task created"},
}


def enums() -> dict[str, list[str]]:
    """Allowed values in their defined order, straight from the backend models and rules."""
    return {
        "partner_status": list(get_args(PartnerStatus)),
        "agreement_status": list(get_args(AgreementStatus)),
        "signed_copy": list(get_args(SignedCopyStatus)),
        "renewal_status": list(get_args(RenewalStatus)),
        "project_status": list(get_args(RecordStatus)),
        "milestone_status": list(get_args(MilestoneStatus)),
        "opportunity_stage": list(OPPORTUNITY_STAGES),
        "finance_record_type": list(get_args(FinanceType)),
        "document_kind": list(get_args(DocumentKind)),
        "scope_dimension": list(get_args(ScopeDimension)),
        "report_type": list(get_args(ReportCreate.model_fields["report_type"].annotation)),
        "report_status": list(get_args(ReportCreate.model_fields["status"].annotation)),
        "alert_category": list(dict.fromkeys(rule["category"] for rule in RULES.values())),
        "alert_severity": list(SEVERITY_POINTS),
        # Reviewer decisions, plus "task_created", which is recorded when a task is made from an alert.
        "review_decision": [*get_args(ReviewDecision), "task_created"],
    }
