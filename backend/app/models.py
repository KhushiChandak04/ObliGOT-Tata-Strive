from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, model_validator

def _check_date_order(start: date | None, end: date | None, end_label: str) -> None:
    if start and end and end < start:
        raise ValueError(f"{end_label} must be on or after start_date")

PartnerStatus = Literal["prospect", "qualification", "active", "on_hold", "closed"]
Priority = Literal["high", "medium", "low"]
ActionStatus = Literal["open", "in_review", "done", "deferred"]
RecordStatus = Literal["planned", "active", "on_hold", "completed", "closed"]
FinanceType = Literal["budget", "fund_received", "invoice", "utilization_certificate"]

# Allowed statuses per finance record type; the first entry is the default on create.
FINANCE_STATUSES: dict[str, tuple[str, ...]] = {
    "budget": ("planned", "approved", "revised", "closed"),
    "fund_received": ("expected", "received", "cancelled"),
    "invoice": ("raised", "draft", "sent", "paid", "cancelled"),
    "utilization_certificate": ("pending", "submitted", "accepted", "rejected"),
}

class Partner(BaseModel):
    id: str
    name: str
    category: str = "Other"
    contribution_types: list[str] = Field(default_factory=list)
    status: PartnerStatus = "prospect"
    owner: str = "Unassigned"
    updated_at: date
    summary: str = ""
    contact_name: str | None = None
    contact_email: str | None = None
    source_label: str = "demo"

class PartnerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    category: str = Field(min_length=2, max_length=100)
    contribution_types: list[str] = Field(default_factory=list)
    status: PartnerStatus = "prospect"
    owner: str = Field(min_length=2, max_length=120)
    summary: str = Field(default="No summary supplied.", max_length=1200)
    contact_name: str | None = Field(default=None, max_length=120)
    contact_email: str | None = Field(default=None, max_length=254)

class PartnerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    category: str | None = Field(default=None, max_length=100)
    contribution_types: list[str] | None = None
    status: PartnerStatus | None = None
    owner: str | None = Field(default=None, max_length=120)
    summary: str | None = Field(default=None, max_length=1200)
    contact_name: str | None = Field(default=None, max_length=120)
    contact_email: str | None = Field(default=None, max_length=254)

class ActionItem(BaseModel):
    id: str
    title: str
    priority: Priority
    status: ActionStatus = "open"
    due_date: date | None = None
    evidence: list[str] = Field(default_factory=list)
    recommended_action: str = ""
    related_partner_id: str | None = None
    owner: str = "Unassigned"
    source_label: str = "demo"

class ActionCreate(BaseModel):
    title: str = Field(min_length=3, max_length=240)
    priority: Priority = "medium"
    due_date: date | None = None
    evidence: list[str] = Field(default_factory=list)
    recommended_action: str = ""
    related_partner_id: str | None = None
    owner: str = "Unassigned"

class ActionUpdate(BaseModel):
    status: ActionStatus | None = None
    owner: str | None = None
    priority: Priority | None = None
    due_date: date | None = None
    recommended_action: str | None = None

AgreementStatus = Literal["draft", "under_review", "active", "expired", "closed"]
# Whether the signed copy is on file; "unknown" means nobody has confirmed it either way.
SignedCopyStatus = Literal["received", "pending", "unknown"]
RenewalStatus = Literal["none", "in_progress", "renewed", "not_renewing"]

class Agreement(BaseModel):
    id: str
    partner_id: str
    title: str
    reference_number: str | None = None
    status: AgreementStatus = "draft"
    start_date: date | None = None
    expiry_date: date | None = None
    owner: str = "Unassigned"
    document_url: str | None = None
    signed_copy: SignedCopyStatus = "unknown"
    renewal_status: RenewalStatus = "none"
    project_id: str | None = None
    opportunity_id: str | None = None
    source_label: str = "demo"

class AgreementCreate(BaseModel):
    partner_id: str
    title: str = Field(min_length=2, max_length=200)
    reference_number: str | None = Field(default=None, max_length=100)
    status: AgreementStatus = "draft"
    start_date: date | None = None
    expiry_date: date | None = None
    owner: str = Field(default="Unassigned", max_length=120)
    document_url: str | None = Field(default=None, max_length=2000)
    signed_copy: SignedCopyStatus = "unknown"
    renewal_status: RenewalStatus = "none"
    project_id: str | None = None
    opportunity_id: str | None = None

    @model_validator(mode="after")
    def expiry_after_start(self):
        _check_date_order(self.start_date, self.expiry_date, "expiry_date")
        return self

    @model_validator(mode="after")
    def document_url_is_web_link(self):
        # Rendered as a link in the UI, so only http(s) is allowed (blocks javascript: and data: URLs).
        if self.document_url is not None:
            self.document_url = self.document_url.strip() or None
        if self.document_url and not self.document_url.lower().startswith(("https://", "http://")):
            raise ValueError("document_url must start with https:// or http://")
        return self

class Project(BaseModel):
    id: str
    partner_id: str | None = None
    name: str
    status: RecordStatus = "planned"
    owner: str = "Unassigned"
    start_date: date | None = None
    end_date: date | None = None
    milestone_summary: str = ""
    source_label: str = "demo"

class ProjectCreate(BaseModel):
    partner_id: str | None = None
    name: str = Field(min_length=2, max_length=200)
    status: RecordStatus = "planned"
    owner: str = "Unassigned"
    start_date: date | None = None
    end_date: date | None = None
    milestone_summary: str = ""

    @model_validator(mode="after")
    def end_after_start(self):
        _check_date_order(self.start_date, self.end_date, "end_date")
        return self

class FinanceRecord(BaseModel):
    id: str
    partner_id: str
    project_id: str | None = None
    record_type: Literal["budget", "fund_received", "invoice", "utilization_certificate"]
    title: str
    amount: float | None = Field(default=None, ge=0)
    currency: str = "INR"
    due_date: date | None = None
    status: str = "pending"
    reference_number: str | None = None
    source_label: str = "demo"

class FinanceCreate(BaseModel):
    partner_id: str
    project_id: str | None = None
    record_type: FinanceType
    title: str = Field(min_length=2, max_length=200)
    amount: float | None = Field(default=None, ge=0)
    currency: str = "INR"
    due_date: date | None = None
    status: str | None = None
    reference_number: str | None = None

    @model_validator(mode="after")
    def status_matches_record_type(self):
        allowed = FINANCE_STATUSES[self.record_type]
        if self.status is None:
            self.status = allowed[0]
        elif self.status not in allowed:
            raise ValueError(f"status for {self.record_type} must be one of: {', '.join(allowed)}")
        return self

class ReportRecord(BaseModel):
    id: str
    partner_id: str
    project_id: str | None = None
    title: str
    report_type: Literal["monthly", "quarterly", "impact", "other"] = "other"
    due_date: date | None = None
    submitted_date: date | None = None
    status: Literal["planned", "due", "submitted", "overdue", "accepted"] = "planned"
    owner: str = "Unassigned"
    source_label: str = "demo"

class ReportCreate(BaseModel):
    partner_id: str
    project_id: str | None = None
    title: str = Field(min_length=2, max_length=200)
    report_type: Literal["monthly", "quarterly", "impact", "other"] = "other"
    due_date: date | None = None
    submitted_date: date | None = None
    status: Literal["planned", "due", "submitted", "overdue", "accepted"] = "planned"
    owner: str = "Unassigned"

# Partnership lifecycle stages, in order. "closed" ends the pipeline (won, lost, or ended).
OPPORTUNITY_STAGES: tuple[str, ...] = ("identified", "qualification", "proposal", "approval", "agreement", "active", "renewal", "closed")
OpportunityStage = Literal["identified", "qualification", "proposal", "approval", "agreement", "active", "renewal", "closed"]

class Opportunity(BaseModel):
    id: str
    partner_id: str
    title: str
    stage: OpportunityStage = "identified"
    owner: str = "Unassigned"
    next_step: str = ""
    next_step_date: date | None = None
    updated_at: date
    source_label: str = "demo"

class OpportunityCreate(BaseModel):
    partner_id: str
    title: str = Field(min_length=2, max_length=200)
    stage: OpportunityStage = "identified"
    owner: str = Field(default="Unassigned", min_length=2, max_length=120)
    next_step: str = Field(default="", max_length=500)
    next_step_date: date | None = None

class AnalyzeRequest(BaseModel):
    partner_id: str | None = None
    context: str = Field(default="", max_length=8000)

class AnalyzeResponse(BaseModel):
    summary: str
    observations: list[str]
    recommendations: list[str]
    ai_used: bool
    # Machine-readable reason when ai_used is false: not_configured, timeout, empty_response, api_error:<code>, error:<type>.
    ai_error: str | None = None

class FollowupCreate(BaseModel):
    title: str = Field(min_length=3, max_length=240)
    owner: str = Field(min_length=2, max_length=120)
    due_date: date | None = None
    related_partner_id: str | None = None

class FollowupUpdate(BaseModel):
    status: ActionStatus
