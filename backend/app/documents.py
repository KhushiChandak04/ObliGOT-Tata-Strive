"""Document-to-data contract: source documents, evidence, extracted fields, clauses, financial terms, amendments.

These models describe PDF-derived data before and after human review. Nothing here is operational until a
reviewer approves it; the rules engine reads only approved, normalized records (see ARCHITECTURE.md).
Model output is untrusted: evidence is verified deterministically against the extracted page text.
"""
import re
import unicodedata
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.models import _check_date_order

DocumentKind = Literal["mou", "addendum"]
# uploaded → extracting → needs_review → approved. failed: processing error; blocked: needs OCR/manual input or
# an addendum whose target agreement is not yet chosen. A document is never approved because extraction finished.
DocumentStatus = Literal["uploaded", "extracting", "needs_review", "approved", "failed", "blocked"]
PageTextStatus = Literal["text", "low_text"]
ReviewState = Literal["proposed", "needs_review", "approved", "rejected", "deferred"]
ExtractionTarget = Literal["partner", "agreement", "programme", "scope", "financial_term", "obligation", "clause"]
ScalarValue = str | int | float | bool | date | None

ClauseType = Literal[
    "responsibility", "payment_condition", "fund_release", "reporting", "utilization_certificate",
    "renewal", "termination", "penalty", "exception", "audit", "confidentiality", "other",
]
FinancialTermType = Literal["total_commitment", "annual_budget", "tranche", "payment_term", "partner_contribution", "other"]
# Kept explicit so a ceiling is never read as money spent and an estimate never as a confirmed commitment.
CommitmentBasis = Literal["confirmed", "estimated", "ceiling", "unspecified"]
ObligationType = Literal[
    "milestone", "deliverable", "progress_report", "impact_report", "utilization_certificate", "fund_release", "other",
]
ObligationFrequency = Literal["once", "monthly", "quarterly", "half_yearly", "annual", "unspecified"]
ScopeDimension = Literal["state", "region", "course", "training_type", "beneficiary_group", "target"]
ChangeStatus = Literal["proposed", "approved", "rejected", "unresolved"]
IssueSeverity = Literal["error", "warning"]
IssueStatus = Literal["open", "resolved", "deferred"]

# Statuses a reviewer must sign off; the model rejects them without reviewer metadata.
_REVIEWED_STATES = {"approved", "rejected"}


def _require_reviewer(state: str, reviewed_by: str | None, reviewed_at: datetime | None) -> None:
    if state in _REVIEWED_STATES and not (reviewed_by and reviewed_at):
        raise ValueError(f"{state} requires reviewed_by and reviewed_at")


class DocumentPage(BaseModel):
    page_number: int = Field(ge=1)
    char_count: int = Field(ge=0)
    text_status: PageTextStatus


class SourceDocument(BaseModel):
    id: str
    filename: str = Field(min_length=1, max_length=255)
    kind: DocumentKind
    partner_id: str | None = None
    agreement_id: str | None = None  # required before an addendum's changes can be reviewed; chosen by a human if unsure
    uploaded_at: datetime
    uploaded_by: str
    page_count: int | None = Field(default=None, ge=1)
    pages: list[DocumentPage] = Field(default_factory=list)
    status: DocumentStatus = "uploaded"
    storage_ref: str | None = None  # private storage path, never a public URL
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    source_label: str = "user"

    @model_validator(mode="after")
    def approval_is_recorded(self):
        if self.status == "approved" and not (self.approved_by and self.approved_at):
            raise ValueError("an approved document requires approved_by and approved_at")
        if self.pages and self.page_count is not None and len(self.pages) != self.page_count:
            raise ValueError("pages must list every page of the document")
        return self


class Evidence(BaseModel):
    """Where a value comes from. `verified` is set only by `verify_evidence`, never taken from model output."""
    document_id: str
    page: int = Field(ge=1)
    quote: str = Field(min_length=1, max_length=1000)
    verified: bool = False
    verification_error: Literal["page_out_of_range", "quote_not_found"] | None = None


class ExtractedField(BaseModel):
    """One proposed value. Verbatim text, normalized value, warnings, and the approved value are kept apart."""
    id: str
    document_id: str
    target: ExtractionTarget
    target_id: str | None = None
    field: str = Field(min_length=1, max_length=80)
    verbatim: str | None = None
    proposed_value: ScalarValue = None  # None means "not stated in the document", never a default
    evidence: Evidence | None = None
    warnings: list[str] = Field(default_factory=list)
    review_state: ReviewState = "proposed"
    approved_value: ScalarValue = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    review_note: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def review_is_recorded(self):
        _require_reviewer(self.review_state, self.reviewed_by, self.reviewed_at)
        if self.review_state != "approved" and self.approved_value is not None:
            raise ValueError("approved_value is only set once the field is approved")
        return self


class Clause(BaseModel):
    id: str
    agreement_id: str
    document_id: str
    clause_type: ClauseType
    heading: str | None = Field(default=None, max_length=200)
    summary: str = Field(min_length=1, max_length=1000)  # advisory; the verbatim text is authoritative
    verbatim: str = Field(min_length=1)
    evidence: Evidence
    needs_legal_review: bool = False
    review_state: ReviewState = "proposed"
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None

    @model_validator(mode="after")
    def review_is_recorded(self):
        _require_reviewer(self.review_state, self.reviewed_by, self.reviewed_at)
        return self


class FinancialTerm(BaseModel):
    """A contractual money term from an agreement. Distinct from `finance` records (budgets, receipts, invoices, UCs)."""
    id: str
    agreement_id: str
    partner_id: str
    term_type: FinancialTermType
    description: str = Field(min_length=1, max_length=500)
    amount: float | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    basis: CommitmentBasis = "unspecified"
    financial_year: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}$")  # e.g. 2026-27
    payer: str | None = Field(default=None, max_length=160)
    due_date: date | None = None
    condition: str | None = Field(default=None, max_length=1000)
    evidence: Evidence | None = None
    review_state: ReviewState = "proposed"
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    source_label: str = "user"

    @model_validator(mode="after")
    def amount_has_currency(self):
        if self.amount is not None and self.currency is None:
            raise ValueError("an amount requires its currency")
        _require_reviewer(self.review_state, self.reviewed_by, self.reviewed_at)
        return self


class Obligation(BaseModel):
    """Deliverable, milestone, report, UC, or fund release stated in an agreement. Due dates only when stated."""
    id: str
    agreement_id: str
    partner_id: str
    project_id: str | None = None
    obligation_type: ObligationType
    title: str = Field(min_length=1, max_length=300)
    frequency: ObligationFrequency = "unspecified"
    due_date: date | None = None
    owner: str | None = None
    evidence: Evidence | None = None
    review_state: ReviewState = "proposed"
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    source_label: str = "user"

    @model_validator(mode="after")
    def review_is_recorded(self):
        _require_reviewer(self.review_state, self.reviewed_by, self.reviewed_at)
        return self


class ProgrammeScope(BaseModel):
    """One scope item (state, course, beneficiary group, target) of a programme; many rows per programme."""
    id: str
    project_id: str
    agreement_id: str
    dimension: ScopeDimension
    value: str = Field(min_length=1, max_length=300)
    target_value: float | None = Field(default=None, ge=0)
    target_unit: str | None = Field(default=None, max_length=60)
    evidence: Evidence | None = None
    review_state: ReviewState = "proposed"


class AgreementChange(BaseModel):
    """A change an addendum makes to one field or clause. Applied to the effective view only once approved."""
    id: str
    agreement_id: str
    addendum_document_id: str
    target: ExtractionTarget
    target_id: str | None = None
    field: str = Field(min_length=1, max_length=80)
    prior_value: ScalarValue = None
    proposed_value: ScalarValue = None
    amendment_date: date | None = None
    effective_date: date | None = None
    evidence: Evidence
    status: ChangeStatus = "proposed"
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    note: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def approval_needs_reviewer_and_evidence(self):
        _require_reviewer(self.status, self.reviewed_by, self.reviewed_at)
        if self.status == "approved" and not self.evidence.verified:
            raise ValueError("a change can only be approved with verified evidence")
        _check_date_order(self.amendment_date, self.effective_date, "effective_date", "amendment_date")
        return self


class ReviewIssue(BaseModel):
    id: str
    document_id: str
    severity: IssueSeverity
    code: str = Field(min_length=1, max_length=60)
    message: str = Field(min_length=1, max_length=1000)
    related_id: str | None = None
    status: IssueStatus = "open"
    resolution: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def resolution_is_explained(self):
        if self.status in ("resolved", "deferred") and not self.resolution:
            raise ValueError(f"a {self.status} issue requires a resolution note")
        return self


# Pages with fewer extracted characters than this are treated as scanned/low-text and need OCR or manual review.
LOW_TEXT_CHARS = 40

_QUOTE_MAP = str.maketrans({
    "‘": "'", "’": "'", "“": '"', "”": '"',
    "–": "-", "—": "-", "−": "-", "­": None,
})


def normalize_text(text: str, join_hyphenation: bool = False) -> str:
    """Normalization used to match quotes: Unicode NFKC, straight quotes and dashes, whitespace collapsed,
    case-folded; optionally words split by a line-break hyphen are joined. Wording itself is never changed."""
    text = unicodedata.normalize("NFKC", text).translate(_QUOTE_MAP)
    text = re.sub(r"(\w)-[ \t]*\n\s*(\w)", r"\1\2" if join_hyphenation else r"\1-\2", text)
    return re.sub(r"\s+", " ", text).strip().casefold()


def verify_evidence(evidence: Evidence, page_texts: list[str]) -> Evidence:
    """Return a copy of `evidence` marked verified only if its page exists and the quote appears on that page."""
    if evidence.page > len(page_texts):
        return evidence.model_copy(update={"verified": False, "verification_error": "page_out_of_range"})
    quote = normalize_text(evidence.quote)
    page = page_texts[evidence.page - 1]
    # A hyphen at a line break may be a real hyphen ("co-\noperate" quoted as "co-operate") or a word split.
    found = bool(quote) and (quote in normalize_text(page) or quote in normalize_text(page, join_hyphenation=True))
    return evidence.model_copy(update={"verified": found, "verification_error": None if found else "quote_not_found"})


def page_text_status(text: str) -> PageTextStatus:
    return "text" if len(text.strip()) >= LOW_TEXT_CHARS else "low_text"
