"""Excel workbook contract: sheet names, columns, types, and relationships.

The workbook is the standard representation of approved, normalized partnership data. It is generated from
the same records the application persists (export arrives in a later step); unapproved values never appear in
operational columns. This module defines the contract only and is checked by tests against the models.
"""
from dataclasses import dataclass
from typing import Literal, get_args

from app import documents, models

ColumnType = Literal["id", "text", "date", "datetime", "number", "integer", "bool", "enum"]


@dataclass(frozen=True)
class Column:
    name: str
    type: ColumnType
    required: bool = False
    references: str | None = None  # sheet whose first (ID) column this value must match
    allowed: tuple[str, ...] = ()  # for enum columns


def _enum(name: str, literal, required: bool = False) -> Column:
    return Column(name, "enum", required, allowed=tuple(get_args(literal)))


_REVIEW = _enum("review_state", documents.ReviewState, required=True)
_SOURCE = (
    Column("source_document_id", "id"),
    Column("source_page", "integer"),
    Column("source_quote", "text"),
)

SHEETS: dict[str, tuple[Column, ...]] = {
    "Partners": (
        Column("partner_id", "id", True),
        Column("name", "text", True),
        Column("legal_entity_name", "text"),
        Column("category", "text"),
        _enum("status", models.PartnerStatus, True),
        Column("owner", "text"),
        Column("contact_name", "text"),
        Column("contact_email", "text"),
        Column("source_label", "text", True),
    ),
    "Agreements": (
        # Latest approved effective values; originals and each amendment are in Addenda_Change_History.
        Column("agreement_id", "id", True),
        Column("partner_id", "id", True, references="Partners"),
        Column("reference_number", "text"),
        Column("title", "text", True),
        _enum("status", models.AgreementStatus, True),
        Column("execution_date", "date"),
        Column("effective_date", "date"),
        Column("start_date", "date"),
        Column("expiry_date", "date"),
        Column("renewal_terms", "text"),
        _enum("renewal_status", models.RenewalStatus),
        _enum("signed_copy", models.SignedCopyStatus),
        Column("owner", "text"),
        Column("amended", "bool", True),
        Column("unresolved_changes", "integer", True),
        *_SOURCE,
        _REVIEW,
        Column("source_label", "text", True),
    ),
    "Programmes_Projects": (
        Column("project_id", "id", True),
        Column("agreement_id", "id", references="Agreements"),
        Column("partner_id", "id", references="Partners"),
        Column("name", "text", True),
        _enum("status", models.RecordStatus, True),
        Column("start_date", "date"),
        Column("end_date", "date"),
        Column("owner", "text"),
        Column("source_label", "text", True),
    ),
    "Programme_Scope": (
        # One row per state, course, beneficiary group, or target, so many-to-many scope stays filterable.
        Column("scope_id", "id", True),
        Column("project_id", "id", True, references="Programmes_Projects"),
        Column("agreement_id", "id", True, references="Agreements"),
        _enum("dimension", documents.ScopeDimension, True),
        Column("value", "text", True),
        Column("target_value", "number"),
        Column("target_unit", "text"),
        *_SOURCE,
        _REVIEW,
    ),
    "Financial_Terms": (
        # Contractual terms only. Budgets, receipts, invoices, and UCs stay in their own records; amounts are
        # never summed across currencies or term types.
        Column("term_id", "id", True),
        Column("agreement_id", "id", True, references="Agreements"),
        Column("partner_id", "id", True, references="Partners"),
        _enum("term_type", documents.FinancialTermType, True),
        Column("description", "text", True),
        Column("amount", "number"),
        Column("currency", "text"),
        _enum("basis", documents.CommitmentBasis, True),
        Column("financial_year", "text"),
        Column("payer", "text"),
        Column("due_date", "date"),
        Column("condition", "text"),
        Column("amended", "bool", True),
        *_SOURCE,
        _REVIEW,
    ),
    "Obligations_Milestones": (
        Column("obligation_id", "id", True),
        Column("agreement_id", "id", references="Agreements"),
        Column("partner_id", "id", True, references="Partners"),
        Column("project_id", "id", references="Programmes_Projects"),
        _enum("obligation_type", documents.ObligationType, True),
        Column("title", "text", True),
        _enum("frequency", documents.ObligationFrequency, True),
        Column("due_date", "date"),
        Column("status", "text"),
        Column("owner", "text"),
        Column("amended", "bool", True),
        *_SOURCE,
        _REVIEW,
    ),
    "Clauses": (
        Column("clause_id", "id", True),
        Column("agreement_id", "id", True, references="Agreements"),
        Column("document_id", "id", True),
        _enum("clause_type", documents.ClauseType, True),
        Column("heading", "text"),
        Column("summary", "text", True),
        Column("verbatim_text", "text", True),
        Column("source_page", "integer", True),
        Column("needs_legal_review", "bool", True),
        _REVIEW,
    ),
    "Addenda_Change_History": (
        Column("change_id", "id", True),
        Column("agreement_id", "id", True, references="Agreements"),
        Column("addendum_document_id", "id", True),
        _enum("target", documents.ExtractionTarget, True),
        Column("target_id", "id"),
        Column("field", "text", True),
        Column("prior_value", "text"),
        Column("proposed_value", "text"),
        Column("amendment_date", "date"),
        Column("effective_date", "date"),
        Column("source_page", "integer", True),
        Column("source_quote", "text", True),
        _enum("status", documents.ChangeStatus, True),
        Column("reviewed_by", "text"),
        Column("reviewed_at", "datetime"),
        Column("note", "text"),
    ),
    "Validation_Review_Issues": (
        Column("issue_id", "id", True),
        Column("document_id", "id", True),
        _enum("severity", documents.IssueSeverity, True),
        Column("code", "text", True),
        Column("message", "text", True),
        Column("related_id", "id"),
        _enum("status", documents.IssueStatus, True),
        Column("resolution", "text"),
    ),
}


def contract() -> dict:
    """The workbook contract as plain data (for docs and a future schema endpoint)."""
    return {
        sheet: [
            {"name": c.name, "type": c.type, "required": c.required, "references": c.references, "allowed": list(c.allowed)}
            for c in columns
        ]
        for sheet, columns in SHEETS.items()
    }
