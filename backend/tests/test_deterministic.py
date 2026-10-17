"""Deterministic fallback extraction (Phase R1): explicit, labelled values only; nothing inferred."""
from datetime import date

from app.deterministic import extract, parse_amount, parse_date
from app.extraction import build_proposals

DOC = {"id": "doc-0000000000dd", "kind": "mou", "partner_id": None, "agreement_id": None}


def test_dates_in_common_formats():
    assert parse_date("1 April 2026") == (date(2026, 4, 1), None)
    assert parse_date("1st day of April, 2026") == (date(2026, 4, 1), None)
    assert parse_date("April 1, 2026") == (date(2026, 4, 1), None)
    assert parse_date("31/03/2027") == (date(2027, 3, 31), None)  # day > 12: unambiguous
    value, warning = parse_date("04/05/2026")
    assert value is None and "day/month or month/day" in warning  # ambiguous: not guessed
    value, warning = parse_date("31 February 2026")
    assert value is None and "not a valid calendar date" in warning


def test_amounts_keep_grouping_and_never_apply_units():
    assert parse_amount("36,08,000") == 3608000 and parse_amount("3,608,000.50") == 3608000.5
    assert parse_amount("3,60,80,00") is None  # malformed grouping
    out = extract(["The grant is INR 36,08,000/- in total. A further Rs. 5 lakhs is a ceiling."])
    first, second = out.financial_terms
    assert first.amount == 3608000 and first.currency == "INR" and first.quote == "INR 36,08,000/-"
    assert second.amount is None and "not converted" in second.condition  # "5 lakhs" is never turned into a number


def test_only_labelled_dates_are_taken():
    text = ("This MOU is effective from 1 April 2026 and shall remain in force until 31 March 2027. "
            "A meeting was held on 3 May 2025.")
    fields = {f.field: f for f in extract([text]).fields}
    assert fields["effective_date"].normalized_value == "2026-04-01"
    assert fields["expiry_date"].normalized_value == "2027-03-31"
    assert len(extract([text]).fields) == 2  # the unlabelled meeting date is not a contract date


def test_references_and_evidence_verify_against_the_same_text():
    texts = ["Reference: SYN-MOU-001. MOU No. TS/2026/14 was signed.", "valid until 30 June 2027"]
    out = build_proposals(DOC, [extract(texts)], texts)
    refs = [f["proposed_value"] for f in out["extracted_fields"] if f["field"] == "reference_number"]
    assert refs == ["SYN-MOU-001", "TS/2026/14"]
    assert all(f["evidence"]["verified"] for f in out["extracted_fields"])
    assert all(f["review_state"] in ("proposed", "needs_review") for f in out["extracted_fields"])


def test_nothing_is_invented_from_empty_or_unlabelled_text():
    assert extract(["", "Clause 7: the partner shall report quarterly."]) .fields == []
    assert extract(["", "Clause 7: the partner shall report quarterly."]).financial_terms == []
