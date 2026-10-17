"""Document-to-data contract (Step P1a): evidence verification, review gates, and the workbook contract."""
from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from app import documents, models, workbook
from app.documents import (
    AgreementChange, Evidence, ExtractedField, FinancialTerm, ReviewIssue, SourceDocument, page_text_status,
    verify_evidence,
)

NOW = datetime(2026, 10, 17, 10, 0, tzinfo=timezone.utc)
# Synthetic page text; not taken from any real agreement.
PAGES = [
    "SYNTHETIC MEMORANDUM OF UNDERSTANDING\nbetween Example Foundation and the Implementing Partner.",
    "4.2 The Implementing Partner shall submit a quarterly progress\nreport within fifteen (15) days of each quarter’s end.",
    "7.1 The total commitment shall not exceed INR 25,00,000 for the co-\noperative programme.",
]


def ev(page: int, quote: str) -> Evidence:
    return Evidence(document_id="doc-1", page=page, quote=quote)


def test_quote_on_cited_page_is_verified_across_line_breaks_and_quote_styles():
    result = verify_evidence(ev(2, "submit a quarterly progress report within fifteen (15) days of each quarter's end"), PAGES)
    assert result.verified and result.verification_error is None


def test_quote_matching_is_case_and_whitespace_insensitive_only():
    assert verify_evidence(ev(1, "synthetic   memorandum of understanding"), PAGES).verified
    assert not verify_evidence(ev(1, "memorandum of agreement"), PAGES).verified


def test_line_break_hyphen_matches_hyphenated_or_joined_wording():
    assert verify_evidence(ev(3, "for the co-operative programme"), PAGES).verified
    assert verify_evidence(ev(3, "for the cooperative programme"), PAGES).verified


def test_quote_from_another_page_is_not_verified():
    result = verify_evidence(ev(1, "total commitment shall not exceed"), PAGES)
    assert not result.verified and result.verification_error == "quote_not_found"


def test_page_outside_document_is_rejected():
    result = verify_evidence(ev(4, "total commitment"), PAGES)
    assert not result.verified and result.verification_error == "page_out_of_range"
    with pytest.raises(ValidationError):
        ev(0, "anything")


def test_verified_flag_from_model_output_is_recomputed():
    claimed = Evidence(document_id="doc-1", page=2, quote="invented clause text", verified=True)
    assert not verify_evidence(claimed, PAGES).verified


def test_low_text_pages_are_detected():
    assert page_text_status(PAGES[1]) == "text"
    assert page_text_status("  \n 3 ") == "low_text"


def test_missing_values_stay_missing():
    field = ExtractedField(id="f1", document_id="doc-1", target="agreement", field="expiry_date")
    assert field.proposed_value is None and field.approved_value is None and field.review_state == "proposed"
    term = FinancialTerm(id="t1", agreement_id="a1", partner_id="p1", term_type="total_commitment", description="Not stated")
    assert term.amount is None and term.currency is None and term.basis == "unspecified"


def test_approval_requires_reviewer_metadata():
    with pytest.raises(ValidationError, match="reviewed_by"):
        ExtractedField(id="f1", document_id="doc-1", target="agreement", field="expiry_date", review_state="approved")
    approved = ExtractedField(
        id="f1", document_id="doc-1", target="agreement", field="expiry_date", proposed_value=date(2027, 3, 31),
        review_state="approved", approved_value=date(2027, 3, 31), reviewed_by="Reviewer (fictional)", reviewed_at=NOW,
    )
    assert approved.approved_value == date(2027, 3, 31)


def test_unapproved_field_cannot_carry_an_approved_value():
    with pytest.raises(ValidationError, match="approved_value"):
        ExtractedField(id="f1", document_id="doc-1", target="agreement", field="title", approved_value="X")


def test_document_is_not_approved_without_approval_record():
    base = dict(id="doc-1", filename="synthetic-mou.pdf", kind="mou", uploaded_at=NOW, uploaded_by="Demo user")
    with pytest.raises(ValidationError, match="approved_by"):
        SourceDocument(**base, status="approved")
    assert SourceDocument(**base, status="needs_review").status == "needs_review"


def test_amount_needs_currency_and_financial_year_format():
    with pytest.raises(ValidationError, match="currency"):
        FinancialTerm(id="t1", agreement_id="a1", partner_id="p1", term_type="annual_budget", description="x", amount=100)
    with pytest.raises(ValidationError):
        FinancialTerm(id="t1", agreement_id="a1", partner_id="p1", term_type="annual_budget", description="x", financial_year="FY27")


def test_addendum_change_needs_verified_evidence_and_reviewer_to_be_approved():
    base = dict(id="c1", agreement_id="a1", addendum_document_id="doc-2", target="agreement", field="expiry_date",
                prior_value=date(2027, 3, 31), proposed_value=date(2028, 3, 31))
    unverified = ev(1, "extended to 31 March 2028")
    with pytest.raises(ValidationError, match="verified evidence"):
        AgreementChange(**base, evidence=unverified, status="approved", reviewed_by="Reviewer (fictional)", reviewed_at=NOW)
    verified = unverified.model_copy(update={"verified": True})
    with pytest.raises(ValidationError, match="reviewed_by"):
        AgreementChange(**base, evidence=verified, status="approved")
    change = AgreementChange(**base, evidence=verified, status="approved", reviewed_by="Reviewer (fictional)", reviewed_at=NOW)
    assert change.prior_value == date(2027, 3, 31)  # the prior value is kept alongside the new one


def test_effective_date_cannot_precede_amendment_date():
    with pytest.raises(ValidationError, match="effective_date"):
        AgreementChange(id="c1", agreement_id="a1", addendum_document_id="doc-2", target="agreement", field="expiry_date",
                        evidence=ev(1, "x"), amendment_date=date(2026, 5, 1), effective_date=date(2026, 4, 1))


def test_resolved_issue_requires_explanation():
    with pytest.raises(ValidationError, match="resolution"):
        ReviewIssue(id="i1", document_id="doc-1", severity="warning", code="NAME_MISMATCH", message="x", status="resolved")


# ---- workbook contract ----

def test_workbook_has_expected_sheets():
    assert list(workbook.SHEETS) == [
        "Partners", "Agreements", "Programmes_Projects", "Programme_Scope", "Financial_Terms",
        "Obligations_Milestones", "Clauses", "Addenda_Change_History", "Validation_Review_Issues",
    ]
    assert all(len(name) <= 31 for name in workbook.SHEETS)  # Excel sheet-name limit


def test_each_sheet_starts_with_a_required_id_and_has_unique_columns():
    for sheet, columns in workbook.SHEETS.items():
        assert columns[0].type == "id" and columns[0].required, sheet
        names = [c.name for c in columns]
        assert len(names) == len(set(names)), sheet


def test_references_point_to_existing_sheets():
    for sheet, columns in workbook.SHEETS.items():
        for column in columns:
            if column.references:
                assert column.references in workbook.SHEETS, (sheet, column.name)
                assert column.type == "id"


def test_enum_columns_match_model_values():
    cols = {(s, c.name): c for s, cs in workbook.SHEETS.items() for c in cs}
    assert cols[("Agreements", "status")].allowed == ("draft", "under_review", "active", "expired", "closed")
    assert set(cols[("Financial_Terms", "basis")].allowed) == {"confirmed", "estimated", "ceiling", "unspecified"}
    assert all(c.allowed for c in cols.values() if c.type == "enum")
    assert all(not c.allowed for c in cols.values() if c.type != "enum")


def test_pdf_derived_sheets_carry_review_state():
    for sheet in ("Agreements", "Programme_Scope", "Financial_Terms", "Obligations_Milestones", "Clauses"):
        names = [c.name for c in workbook.SHEETS[sheet]]
        assert "review_state" in names, sheet


def test_contract_is_plain_data():
    data = workbook.contract()
    assert data["Partners"][0] == {"name": "partner_id", "type": "id", "required": True, "references": None, "allowed": []}
    assert data["Partners"][4]["allowed"] == list(models.PartnerStatus.__args__)
