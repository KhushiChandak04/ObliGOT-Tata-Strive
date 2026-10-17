"""Fictional, clearly labelled demo records for the in-memory fallback.

No real organization, agreement, amount, or commitment is implied. Dates are relative to
the business date so each demo scenario stays live:
- demo-001: MOU expiring soon, active addendum missing its expiry date, overdue monthly
  report, invoice without a due date, UC due soon, plus resolved records that must not alert.
- demo-002: draft MOU only (drafts are not evaluated).
- demo-003: early-stage opportunity only.
Opportunities: demo-001 renewal (MOU expiring), demo-002 proposal, demo-003 identified.
"""
from datetime import timedelta
from app.models import ActionItem, Agreement, FinanceRecord, Opportunity, Partner, Project, ReportRecord
from app.rules import business_today

today = business_today()
days = lambda n: today + timedelta(days=n)

PARTNERS = {
    "demo-001": Partner(id="demo-001", name="Illustrative Skills Partner", category="Training & curriculum", contribution_types=["curriculum", "training"], status="active", owner="Partnerships Team", updated_at=today, summary="Illustrative record only. Not a verified organization or commitment.", contact_name="Demo Contact (fictional)", contact_email="contact@example.org", source_label="demo"),
    "demo-002": Partner(id="demo-002", name="Illustrative Industry Partner", category="Industry collaboration", contribution_types=["industry expertise"], status="qualification", owner="Regional Partnerships", updated_at=today, summary="Illustrative prospect record. Validate all details before operational use.", source_label="demo"),
    "demo-003": Partner(id="demo-003", name="Illustrative Community Partner", category="Implementation", contribution_types=["implementation"], status="prospect", owner="Program Team", updated_at=today, summary="Illustrative pipeline record.", source_label="demo"),
}
ACTIONS = {
    "demo-action-001": ActionItem(id="demo-action-001", title="Confirm next reporting date for sample project", priority="high", status="open", due_date=days(2), evidence=["Demo record has no verified reporting date attached."], recommended_action="Confirm the reporting schedule with the record owner and update the source record.", related_partner_id="demo-001", owner="Partnerships Team", source_label="demo"),
    "demo-action-002": ActionItem(id="demo-action-002", title="Review agreement dates before enabling expiry alerts", priority="medium", status="open", due_date=days(7), evidence=["No verified agreement date is present in the starter dataset."], recommended_action="Enter and verify the signed agreement's effective and expiry dates.", owner="Partnerships Team", source_label="demo"),
}
FOLLOWUPS = {}
AGREEMENTS = {
    "demo-agreement-001": Agreement(id="demo-agreement-001", partner_id="demo-001", title="Skills training MOU (demo)", reference_number="DEMO-MOU-001", status="active", start_date=days(-340), expiry_date=days(21), owner="Partnerships Team", signed_copy="received", renewal_status="in_progress", project_id="demo-project-001", document_url="https://example.org/demo/mou-001.pdf", source_label="demo"),
    "demo-agreement-002": Agreement(id="demo-agreement-002", partner_id="demo-001", title="Data-sharing addendum (demo)", reference_number="DEMO-ADD-002", status="active", start_date=days(-120), owner="Partnerships Team", signed_copy="pending", source_label="demo"),
    "demo-agreement-003": Agreement(id="demo-agreement-003", partner_id="demo-002", title="Draft collaboration MOU (demo)", status="draft", owner="Regional Partnerships", opportunity_id="demo-opportunity-002", source_label="demo"),
}
PROJECTS = {
    "demo-project-001": Project(id="demo-project-001", partner_id="demo-001", name="Retail skilling cohort (demo)", status="active", owner="Program Team", start_date=days(-200), end_date=days(160), milestone_summary="Cohort 2 enrolment in progress (illustrative).", source_label="demo"),
}
FINANCE = {
    "demo-finance-001": FinanceRecord(id="demo-finance-001", partner_id="demo-001", project_id="demo-project-001", record_type="budget", title="Programme budget FY (demo)", amount=1500000, currency="INR", status="approved", source_label="demo"),
    "demo-finance-002": FinanceRecord(id="demo-finance-002", partner_id="demo-001", project_id="demo-project-001", record_type="fund_received", title="Tranche 1 received (demo)", amount=600000, currency="INR", status="received", reference_number="DEMO-RCPT-01", source_label="demo"),
    "demo-finance-003": FinanceRecord(id="demo-finance-003", partner_id="demo-001", project_id="demo-project-001", record_type="invoice", title="Invoice for tranche 2 (demo)", amount=450000, currency="INR", status="raised", reference_number="DEMO-INV-07", source_label="demo"),
    "demo-finance-004": FinanceRecord(id="demo-finance-004", partner_id="demo-001", project_id="demo-project-001", record_type="utilization_certificate", title="Utilization certificate for tranche 1 (demo)", due_date=days(10), status="pending", source_label="demo"),
}
REPORTS = {
    "demo-report-001": ReportRecord(id="demo-report-001", partner_id="demo-001", project_id="demo-project-001", title="Monthly progress report (demo)", report_type="monthly", due_date=days(-6), status="due", owner="Program Team", source_label="demo"),
    "demo-report-002": ReportRecord(id="demo-report-002", partner_id="demo-001", project_id="demo-project-001", title="Quarterly progress report (demo)", report_type="quarterly", due_date=days(-40), submitted_date=days(-42), status="submitted", owner="Program Team", source_label="demo"),
}
OPPORTUNITIES = {
    "demo-opportunity-001": Opportunity(id="demo-opportunity-001", partner_id="demo-001", title="Renew skills training MOU (demo)", stage="renewal", owner="Partnerships Team", next_step="Share renewal draft with partner (illustrative).", next_step_date=days(7), updated_at=days(-3), source_label="demo"),
    "demo-opportunity-002": Opportunity(id="demo-opportunity-002", partner_id="demo-002", title="Industry mentoring collaboration (demo)", stage="proposal", owner="Regional Partnerships", next_step="Send proposal for internal review (illustrative).", next_step_date=days(4), updated_at=days(-12), source_label="demo"),
    "demo-opportunity-003": Opportunity(id="demo-opportunity-003", partner_id="demo-003", title="Community outreach pilot (demo)", stage="identified", owner="Program Team", next_step="Schedule introductory call (illustrative).", updated_at=days(-30), source_label="demo"),
}
