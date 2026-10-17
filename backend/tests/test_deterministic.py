"""Deterministic fallback extraction: explicit, labelled values only; works for any country's formats; nothing inferred."""
from datetime import date

import pytest

from app.config import settings
from app.deterministic import extract, parse_date
from app.extraction import build_proposals
from app.money import currency_of, parse_number
from app.validators import parse_number as cell_number

DOC = {"id": "doc-0000000000dd", "kind": "mou", "partner_id": None, "agreement_id": None}


def test_indian_defaults_read_numeric_dates_day_first_and_dot_as_decimal():
    assert parse_date("04/05/2026") == (date(2026, 5, 4), None)  # Tata STRIVE default: day first
    assert parse_number("1.5") == 1.5 and parse_number("1.500") == 1.5 and parse_number("36,08,000") == 3608000


def test_dates_in_common_formats(monkeypatch):
    monkeypatch.setattr(settings, "date_order", "auto")
    assert parse_date("1 April 2026") == (date(2026, 4, 1), None)
    assert parse_date("1st day of April, 2026") == (date(2026, 4, 1), None)
    assert parse_date("April 1, 2026") == (date(2026, 4, 1), None)
    assert parse_date("2026-04-01") == (date(2026, 4, 1), None)          # ISO
    assert parse_date("31/03/2027") == (date(2027, 3, 31), None)         # day first (unambiguous)
    assert parse_date("03/31/2027") == (date(2027, 3, 31), None)         # month first (unambiguous)
    assert parse_date("31.03.2027") == (date(2027, 3, 31), None)         # dotted European style
    value, warning = parse_date("04/05/2026")
    assert value is None and "day/month or month/day" in warning         # ambiguous: not guessed
    value, warning = parse_date("31 February 2026")
    assert value is None and "not a valid calendar date" in warning


def test_date_order_setting_resolves_ambiguous_numeric_dates(monkeypatch):
    monkeypatch.setattr(settings, "date_order", "mdy")
    assert parse_date("04/05/2026") == (date(2026, 4, 5), None)
    monkeypatch.setattr(settings, "date_order", "dmy")
    assert parse_date("04/05/2026") == (date(2026, 5, 4), None)


@pytest.mark.parametrize("text, value", [
    ("1,234,567.89", 1234567.89), ("12,34,567", 1234567), ("1.234.567,89", 1234567.89), ("1 234 567,89", 1234567.89),
    ("1'234'567.50", 1234567.5), ("15,000", 15000), ("2,5", 2.5), ("1500", 1500), ("1.234,5", 1234.5),
])
def test_numbers_in_international_formats(text, value, monkeypatch):
    monkeypatch.setattr(settings, "number_decimal_separator", "auto")
    assert parse_number(text) == value


def test_ambiguous_numbers_are_not_guessed_unless_configured(monkeypatch):
    monkeypatch.setattr(settings, "number_decimal_separator", "auto")
    assert parse_number("1.500") is None  # 1500 in many European documents, 1.5 elsewhere
    monkeypatch.setattr(settings, "number_decimal_separator", ",")
    assert parse_number("1.500") == 1500
    monkeypatch.setattr(settings, "number_decimal_separator", ".")
    assert parse_number("1.500") == 1.5


def test_currencies_from_any_country_and_ambiguous_symbols():
    assert [currency_of(t) for t in ("USD", "eur", "₹", "Rs.", "€", "£", "KES", "US$", "R$", "zł")] == \
        ["USD", "EUR", "INR", "INR", "EUR", "GBP", "KES", "USD", "BRL", "PLN"]
    assert currency_of("$") is None and currency_of("¥") is None and currency_of("kr") is None  # shared by several


def test_amounts_in_many_currencies_with_scales_kept_as_written(monkeypatch):
    monkeypatch.setattr(settings, "number_decimal_separator", "auto")
    out = extract(["Grant of USD 250,000 and EUR 1.200.000,00; local costs Rs. 5 lakhs; partner share 3,000,000 KES; "
                   "an advance of $40,000; and 2 million GBP subject to approval."])
    by_quote = {t.quote: t for t in out.financial_terms}
    assert (by_quote["USD 250,000"].amount, by_quote["USD 250,000"].currency) == (250000, "USD")
    assert (by_quote["EUR 1.200.000,00"].amount, by_quote["EUR 1.200.000,00"].currency) == (1200000, "EUR")
    assert by_quote["Rs. 5 lakhs"].amount is None and "not converted" in by_quote["Rs. 5 lakhs"].ambiguity
    assert (by_quote["3,000,000 KES"].amount, by_quote["3,000,000 KES"].currency) == (3000000, "KES")
    dollar = by_quote["$40,000"]
    assert dollar.currency is None and dollar.amount is None and "does not identify a single currency" in dollar.ambiguity
    assert by_quote["2 million GBP"].amount is None and by_quote["2 million GBP"].currency == "GBP"


def test_table_cells_in_any_currency_and_format(monkeypatch):
    monkeypatch.setattr(settings, "number_decimal_separator", "auto")
    assert cell_number("€ 1.234,50") == 1234.5 and cell_number("USD 10,000") == 10000 and cell_number("₹23,80,000") == 2380000
    assert cell_number("18,04,000/-") == 1804000 and cell_number("10%") is None and cell_number("1.500") is None


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


def test_ambiguous_amounts_become_review_issues_not_values():
    texts = ["An advance of $40,000 is payable on signing."]
    out = build_proposals(DOC, [extract(texts)], texts)
    term = out["financial_terms"][0]
    assert term["amount"] is None and term["currency"] is None and term["review_state"] == "needs_review"


def test_nothing_is_invented_from_empty_or_unlabelled_text():
    out = extract(["", "Clause 7: the partner shall report quarterly."])
    assert out.fields == [] and out.financial_terms == []
