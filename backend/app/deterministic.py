"""Deterministic extraction used when Gemini is unavailable (no key, quota used up, or failing).

It recovers only explicitly labelled, pattern-identifiable facts from text that is actually available — the PDF
text layer or page readings already stored — and never interprets clauses, obligations, or tables:
- dates introduced by explicit labels ("effective from", "valid until", "executed on", "expires on", ...),
- reference numbers introduced by "Ref./Reference/MOU/Agreement No.",
- money amounts written with a currency marker (Rs., INR, ₹).
Every value keeps its exact matched wording as the quote, so evidence is verified against the same text.
Everything else is left for Gemini (retry) or a reviewer; nothing is inferred.
"""
import re
from datetime import date

from app.extraction import (
    ChunkExtraction, ProposedField, ProposedFinancialTerm,
)

MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"], 1)}
MONTHS.update({k[:3]: v for k, v in list(MONTHS.items())})
MONTHS["sept"] = 9

_DAY = r"(\d{1,2})(?:st|nd|rd|th)?"
_MONTH = r"([A-Za-z]{3,9})\.?"
DATE_PATTERNS = [
    re.compile(rf"\b{_DAY}\s+(?:day\s+of\s+)?{_MONTH},?\s+(\d{{4}})\b"),        # 1 April 2026, 1st day of April, 2026
    re.compile(rf"\b{_MONTH}\s+{_DAY},?\s+(\d{{4}})\b"),                          # April 1, 2026
    re.compile(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b"),                        # 01/04/2026 (day first, Indian usage)
]
DATE_LABELS = {
    "effective_date": r"(?:effective\s+(?:from|on|date|as\s+of)|with\s+effect\s+from|commenc\w*\s+(?:from|on))",
    "expiry_date": r"(?:valid\s+(?:until|till|up\s*to)|in\s+force\s+(?:until|till|up\s*to)|expir\w*\s+on|terminat\w*\s+on|ending\s+on)",
    "execution_date": r"(?:executed\s+on|made\s+(?:on|this)|entered\s+into\s+on|signed\s+on|dated)",
}
REFERENCE = re.compile(r"\b(?:Ref(?:erence)?\.?\s*(?:No\.?|Number)?|(?:MOU|MoU|Agreement)\s*(?:No\.?|Number))\s*[:.\-]?\s*([A-Z0-9][A-Z0-9/\-._]{2,40})")
AMOUNT = re.compile(r"(?:Rs\.?|INR|₹)\s*([0-9][0-9,]*(?:\.\d+)?)(\s*/-)?(\s*(?:lakhs?|crores?|lacs?))?", re.IGNORECASE)


def parse_date(text: str) -> tuple[date | None, str | None]:
    """(date, warning). Day-first numeric dates are accepted only when unambiguous (day > 12)."""
    for pattern in DATE_PATTERNS:
        m = pattern.search(text)
        if not m:
            continue
        a, b, year = m.groups()
        try:
            if pattern is DATE_PATTERNS[2]:
                day, month = int(a), int(b)
                if day <= 12 and month <= 12 and day != month:
                    return None, f"“{m.group(0)}” could be day/month or month/day; enter it from the document."
                return date(int(year), month, day), None
            if pattern is DATE_PATTERNS[0]:
                month = MONTHS.get(b.lower())
                return (date(int(year), month, int(a)), None) if month else (None, None)
            month = MONTHS.get(a.lower())
            return (date(int(year), month, int(b)), None) if month else (None, None)
        except ValueError:
            return None, f"“{m.group(0)}” is not a valid calendar date."
    return None, None


def parse_amount(digits: str) -> float | None:
    """Indian or international digit grouping ("36,08,000", "3,608,000.50"); None if the number is malformed."""
    if not re.fullmatch(r"\d{1,3}(?:,\d{2})*(?:,\d{3})(?:\.\d+)?|\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?", digits):
        return None
    return float(digits.replace(",", ""))


def extract(page_texts: list[str]) -> ChunkExtraction:
    """Pattern-based proposals from the given pages (1-based in the output). Only explicit, labelled values."""
    fields: list[ProposedField] = []
    terms: list[ProposedFinancialTerm] = []
    seen: set[tuple] = set()
    for number, text in enumerate(page_texts, 1):
        if not text.strip():
            continue
        flat = re.sub(r"\s+", " ", text)
        for field, label in DATE_LABELS.items():
            for m in re.finditer(label + r"[:\s,]+(.{6,40})", flat, re.IGNORECASE):
                value, warning = parse_date(m.group(1))
                if value is None and warning is None:
                    continue
                quote = (m.group(0) if value is None else m.group(0)[: m.group(0).find(m.group(1)) + len(m.group(1))]).strip()
                key = (field, str(value), number)
                if key in seen:
                    continue
                seen.add(key)
                fields.append(ProposedField(field=field, value_as_written=m.group(1).strip()[:120],
                                            normalized_value=value.isoformat() if value else None, page=number,
                                            quote=quote[:300], ambiguity=warning))
        for m in REFERENCE.finditer(flat):
            ref = m.group(1).rstrip("./-_")  # sentence punctuation is not part of the reference
            key = ("reference_number", ref, number)
            if key not in seen:
                seen.add(key)
                fields.append(ProposedField(field="reference_number", value_as_written=ref, page=number,
                                            quote=m.group(0)[: m.group(0).rfind(ref) + len(ref)][:300]))
        for m in AMOUNT.finditer(flat):
            raw = m.group(0).strip()
            key = ("amount", raw, number)
            if key in seen:
                continue
            seen.add(key)
            amount = parse_amount(m.group(1))
            unit = (m.group(3) or "").strip()
            context = flat[max(0, m.start() - 80): m.end() + 40].strip()
            terms.append(ProposedFinancialTerm(
                term_type="other", description=f"Amount stated on page {number}: “{context[:200]}”",
                # Unit words (lakh/crore) are kept, never applied: the amount is left empty for the reviewer.
                amount=None if unit or amount is None else amount, currency="INR", basis="unspecified",
                condition=f"Stated with unit “{unit}”; not converted." if unit else None, page=number, quote=raw[:300]))
    return ChunkExtraction(fields=fields, financial_terms=terms)
