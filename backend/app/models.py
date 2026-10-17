from datetime import date
from typing import Literal
from pydantic import BaseModel, Field

PartnerStatus = Literal["prospect", "qualification", "active", "on_hold", "closed"]
Priority = Literal["high", "medium", "low"]
ActionStatus = Literal["open", "in_review", "done", "deferred"]
RecordStatus = Literal["planned", "active", "on_hold", "completed", "closed"]

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

class Agreement(BaseModel):
    id: str
    partner_id: str
    title: str
    reference_number: str | None = None
    status: Literal["draft", "under_review", "active", "expired", "closed"] = "draft"
    start_date: date | None = None
    expiry_date: date | None = None
    owner: str = "Unassigned"
    document_url: str | None = None
    source_label: str = "demo"

class AgreementCreate(BaseModel):
    partner_id: str
    title: str = Field(min_length=2, max_length=200)
    reference_number: str | None = None
    status: Literal["draft", "under_review", "active", "expired", "closed"] = "draft"
    start_date: date | None = None
    expiry_date: date | None = None
    owner: str = "Unassigned"
    document_url: str | None = None

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
    record_type: Literal["budget", "fund_received", "invoice", "utilization_certificate"]
    title: str = Field(min_length=2, max_length=200)
    amount: float | None = Field(default=None, ge=0)
    currency: str = "INR"
    due_date: date | None = None
    status: str = "pending"
    reference_number: str | None = None

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

class AnalyzeRequest(BaseModel):
    partner_id: str | None = None
    context: str = Field(default="", max_length=8000)

class AnalyzeResponse(BaseModel):
    summary: str
    observations: list[str]
    recommendations: list[str]
    ai_used: bool

class FollowupCreate(BaseModel):
    title: str = Field(min_length=3, max_length=240)
    owner: str = Field(min_length=2, max_length=120)
    due_date: date | None = None
    related_partner_id: str | None = None

class FollowupUpdate(BaseModel):
    status: ActionStatus
