"""Deterministic-shape, fictional records for the explicitly enabled demo store.

Dates move relative to the IST business date. No synthetic document claims to have a
source PDF, a real extraction, or page-level evidence.
"""
from datetime import datetime, timedelta, timezone

from app.models import (
    ActionItem, Agreement, FinanceRecord, Milestone, Opportunity, Partner, Project, ReportRecord,
)
from app.rules import business_today

SYNTHETIC_WARNING = "Synthetic demo value only; no source PDF, actual extraction, or source evidence exists."


def _record(model):
    return model.model_dump(mode="json")


def build_demo_collections() -> dict[str, dict[str, dict]]:
    today = business_today()
    days = lambda count: today + timedelta(days=count)
    uploaded_at = datetime.now(timezone.utc)
    timestamp = uploaded_at.isoformat()
    partners = {
        f"demo-partner-{number:03}": _record(Partner(
            id=f"demo-partner-{number:03}",
            name=name,
            category=category,
            contribution_types=contributions,
            status=status,
            owner=owner,
            updated_at=today,
            summary="Fictional organisation and illustrative information for ObliGOT demo mode only.",
            contact_name="Synthetic demo contact",
            contact_email=f"contact{number}@example.org",
            source_label="demo",
        ))
        for number, (name, category, contributions, status, owner) in enumerate([
            ("Northstar Learning Collective", "Training & curriculum", ["curriculum", "training"], "active", "Partnerships Team"),
            ("Harbourlight Community Network", "Community implementation", ["implementation"], "active", "Regional Team"),
            ("Cedarbridge Skills Lab", "Industry collaboration", ["mentoring", "placements"], "qualification", "Partnerships Team"),
            ("Bluehaven Access Foundation", "Community development", ["outreach"], "prospect", "Programme Team"),
            ("Meridian Practice Institute", "Training & assessment", ["assessment", "training"], "on_hold", "Regional Team"),
        ], start=1)
    }

    project_specs = [
        ("Retail readiness cohort", "active", -120, 150),
        ("Digital access pilot", "active", -80, 100),
        ("Mentor bridge programme", "planned", 12, 190),
        ("Community outreach cycle", "on_hold", -40, 110),
        ("Practice-based assessment", "completed", -260, -12),
    ]
    projects = {}
    for number, (name, status, start_offset, end_offset) in enumerate(project_specs, start=1):
        partner_id = f"demo-partner-{number:03}"
        record = _record(Project(
            id=f"demo-project-{number:03}", partner_id=partner_id, name=f"{name} (demo)",
            status=status, owner="Synthetic Programme Team", start_date=days(start_offset), end_date=days(end_offset),
            milestone_summary="Illustrative milestone summary; not a real programme commitment.",
            source_label="demo",
        ))
        projects[record["id"]] = record

    agreement_specs = [
        (1, "Retail readiness collaboration (demo)", "active", -170, 190, "received", "none", 1),
        (2, "Digital access partnership (demo)", "active", -340, 18, "received", "in_progress", 2),
        (3, "Mentor bridge agreement (demo)", "active", -60, None, "unknown", "none", 3),
        (4, "Community outreach draft (demo)", "under_review", None, None, "pending", "none", 4),
        (5, "Assessment programme agreement (demo)", "active", -150, 180, "received", "none", 5),
        (5, "Practice assessment agreement (demo)", "expired", -500, -10, "received", "not_renewing", 5),
    ]
    agreements = {}
    for number, (partner_no, title, status, start_offset, expiry_offset, signed, renewal, project_no) in enumerate(agreement_specs, start=1):
        record = _record(Agreement(
            id=f"demo-agreement-{number:03}", partner_id=f"demo-partner-{partner_no:03}", title=title,
            reference_number=f"SYN-MOU-{number:03}", status=status,
            start_date=days(start_offset) if start_offset is not None else None,
            expiry_date=days(expiry_offset) if expiry_offset is not None else None,
            owner="Synthetic Partnerships Team", signed_copy=signed, renewal_status=renewal,
            project_id=f"demo-project-{project_no:03}", source_label="demo",
        ))
        agreements[record["id"]] = record

    actions = {}
    for number, title, status, priority, due_offset, partner_no in [
        (1, "Follow up on the overdue sample report", "open", "high", -4, 1),
        (2, "Confirm renewal planning date", "in_review", "medium", 5, 2),
        (3, "Close completed cohort check-in", "done", "low", -2, 1),
    ]:
        record = _record(ActionItem(
            id=f"demo-action-{number:03}", title=f"{title} (demo)", status=status, priority=priority,
            due_date=days(due_offset), evidence=["Synthetic demo scenario; not evidence about a real partner."],
            recommended_action="Use this fictional record to demonstrate the existing task workflow.",
            related_partner_id=f"demo-partner-{partner_no:03}", owner="Synthetic Programme Team", source_label="demo",
        ))
        actions[record["id"]] = record

    followups = {
        "demo-followup-001": {
            "id": "demo-followup-001", "title": "Request a fictional schedule update (demo)",
            "owner": "Synthetic Partnerships Team", "due_date": days(3).isoformat(),
            "related_partner_id": "demo-partner-002", "status": "open", "source_label": "demo",
        },
        "demo-followup-002": {
            "id": "demo-followup-002", "title": "Record completed introductory call (demo)",
            "owner": "Synthetic Regional Team", "due_date": days(-1).isoformat(),
            "related_partner_id": "demo-partner-004", "status": "done", "source_label": "demo",
        },
    }

    finance = {}
    for model in [
        FinanceRecord(id="demo-finance-001", partner_id="demo-partner-001", project_id="demo-project-001",
            record_type="budget", title="Illustrative programme budget (demo)", amount=1500000, currency="INR",
            status="approved", source_label="demo"),
        FinanceRecord(id="demo-finance-002", partner_id="demo-partner-001", project_id="demo-project-001",
            record_type="fund_received", title="Illustrative tranche received (demo)", amount=600000, currency="INR",
            received_date=days(-40), status="received", reference_number="SYN-RECEIPT-001", source_label="demo"),
        FinanceRecord(id="demo-finance-003", partner_id="demo-partner-001", project_id="demo-project-001",
            record_type="invoice", title="Illustrative invoice due soon (demo)", amount=450000, currency="INR",
            issue_date=days(-10), due_date=days(4), status="raised", reference_number="SYN-INVOICE-001", source_label="demo"),
        FinanceRecord(id="demo-finance-004", partner_id="demo-partner-002", project_id="demo-project-002",
            record_type="utilization_certificate", title="Illustrative utilization certificate (demo)", currency="INR",
            due_date=days(9), status="pending", source_label="demo"),
    ]:
        record = _record(model)
        finance[record["id"]] = record

    reports = {}
    for model in [
        ReportRecord(id="demo-report-001", partner_id="demo-partner-001", project_id="demo-project-001",
            title="Synthetic monthly progress report (demo)", report_type="monthly", due_date=days(-5),
            status="due", owner="Synthetic Programme Team", source_label="demo"),
        ReportRecord(id="demo-report-002", partner_id="demo-partner-002", project_id="demo-project-002",
            title="Synthetic quarterly progress report (demo)", report_type="quarterly", due_date=days(-35),
            submitted_date=days(-37), status="submitted", owner="Synthetic Programme Team", source_label="demo"),
        ReportRecord(id="demo-report-003", partner_id="demo-partner-003", project_id="demo-project-003",
            title="Synthetic impact report (demo)", report_type="impact", due_date=days(14),
            status="planned", owner="Synthetic Programme Team", source_label="demo"),
    ]:
        record = _record(model)
        reports[record["id"]] = record

    opportunities = {}
    for number, stage, step, date_offset in [
        (1, "renewal", "Review fictional renewal timeline", 8),
        (2, "active", "Record synthetic programme check-in", 3),
        (3, "proposal", "Review illustrative proposal", 10),
        (4, "identified", "Schedule a fictional introduction", 14),
        (5, "closed", "No next step; example opportunity is closed", None),
    ]:
        record = _record(Opportunity(
            id=f"demo-opportunity-{number:03}", partner_id=f"demo-partner-{number:03}",
            title=f"Synthetic opportunity {number} (demo)", stage=stage, owner="Synthetic Partnerships Team",
            next_step=step, next_step_date=days(date_offset) if date_offset is not None else None,
            updated_at=days(-number),
            source_label="demo",
        ))
        opportunities[record["id"]] = record

    milestones = {}
    for number, title, status, due_offset, completed_offset, project_no in [
        (1, "Fictional cohort completed", "completed", -30, -28, 1),
        (2, "Fictional enrolment checkpoint", "in_progress", -3, None, 1),
        (3, "Fictional midpoint review", "planned", 20, None, 2),
        (4, "Fictional outreach planning", "planned", 36, None, 4),
    ]:
        record = _record(Milestone(
            id=f"demo-milestone-{number:03}", project_id=f"demo-project-{project_no:03}",
            partner_id=f"demo-partner-{project_no:03}", title=f"{title} (demo)", due_date=days(due_offset),
            completed_date=days(completed_offset) if completed_offset is not None else None, status=status,
            owner="Synthetic Programme Team", source_label="demo",
        ))
        milestones[record["id"]] = record

    documents = {}
    document_specs = [
        (1, "mou", "Complete metadata sample", "extracted", 1, 1, None),
        (2, "mou", "Expiry approaching sample", "extracted", 2, 2, None),
        (3, "mou", "Missing expiry sample", "blocked", 3, 3, "Synthetic example of missing agreement metadata."),
        (4, "mou", "Review warning sample", "extracted", 4, 4, "Illustrative extraction note; no source document is attached."),
        (5, "addendum", "Amendment comparison sample", "extracted", 1, 1, "Synthetic addendum sample; no changes are asserted or applied."),
        (6, "mou", "Past expiry sample", "extracted", 5, 6, None),
    ]
    for number, kind, title, status, partner_no, agreement_no, warning in document_specs:
        document_id = f"demo-document-{number:03}"
        created = (uploaded_at - timedelta(days=number)).isoformat()
        warnings = [SYNTHETIC_WARNING]
        if warning:
            warnings.append(warning)
        extraction = None
        if status == "extracted":
            extraction = {
                "started_at": created, "finished_at": created, "model": "synthetic-demo",
                "pages_to_read": 0, "pages_read": 0, "chunks_total": 0, "chunks_done": 0,
                "pages_sent": [], "pages_skipped_low_text": [], "ai_used": False,
                "mode": "deterministic", "retryable": False,
                "note": "Synthetic illustrative values only; no PDF was uploaded or extracted.",
                "ai_error": None, "counts": {"extracted_fields": 1, "review_issues": int(warning is not None)},
            }
        documents[document_id] = {
            "id": document_id, "filename": f"Synthetic demo - {title}.pdf", "kind": kind,
            "partner_id": f"demo-partner-{partner_no:03}",
            "agreement_id": f"demo-agreement-{agreement_no:03}",
            "uploaded_at": created, "uploaded_by": "Synthetic demo dataset", "size_bytes": None,
            "sha256": None, "page_count": None, "pages": [], "status": status, "storage_ref": None,
            "warnings": warnings, "error": None, "extraction": extraction, "source_label": "demo",
        }

    extracted_fields = {}
    review_issues = {}
    for number, (document_no, field, value) in enumerate([
        (1, "title", "Illustrative complete agreement"),
        (2, "expiry_date", days(18).isoformat()),
        (4, "legal_entity_name", "Fictional review sample entity"),
        (5, "amendment_summary", "No amendment content supplied in this synthetic sample."),
        (6, "expiry_date", days(-10).isoformat()),
    ], start=1):
        document_id = f"demo-document-{document_no:03}"
        item_id = f"demo-field-{number:03}"
        extracted_fields[item_id] = {
            "id": item_id, "document_id": document_id, "target": "agreement", "field": field,
            "proposed_value": value, "verbatim": None, "approved_value": None, "review_state": "needs_review",
            "warnings": [SYNTHETIC_WARNING], "evidence": None,
        }
    for number, document_no in enumerate((3, 4, 5), start=1):
        issue_id = f"demo-issue-{number:03}"
        review_issues[issue_id] = {
            "id": issue_id, "document_id": f"demo-document-{document_no:03}",
            "severity": "warning", "code": "synthetic_demo_note",
            "message": SYNTHETIC_WARNING, "status": "open",
        }

    names = (
        "config", "alert_reviews", "activities", "clauses", "financial_terms", "obligations",
        "programme_scope", "agreement_changes", "document_pages", "tables", "extraction_chunks",
    )
    collections = {
        "partners": partners, "actions": actions, "followups": followups, "agreements": agreements,
        "projects": projects, "finance": finance, "reports": reports, "opportunities": opportunities,
        "milestones": milestones, "documents": documents, "extracted_fields": extracted_fields,
        "review_issues": review_issues,
    }
    collections.update({name: {} for name in names})
    return collections
