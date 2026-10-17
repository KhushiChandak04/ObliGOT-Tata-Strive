"""Deterministic extraction used when Groq is unavailable (no key, quota used up, or failing).

It recovers only explicitly labelled, pattern-identifiable facts from text that is actually available — the PDF
text layer, OCR text, or page readings already stored — and never interprets clauses, obligations, or tables:
- dates introduced by explicit labels ("effective from", "valid until", "executed on", "expires on", ...),
- reference numbers introduced by "Ref./Reference/MOU/Agreement No.",
- money amounts written with a currency code or an unambiguous currency symbol (any country; see app.money).
Every value keeps its exact matched wording as the quote, so evidence is verified against the same text.
Labels are recognised in English only; documents in other languages need Groq or manual entry.
"""
import re
from datetime import date

from app.config import settings
from app.extraction import ChunkExtraction, ProposedField, ProposedFinancialTerm
from app.money import AMOUNT_PATTERN, currency_of, parse_number

MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"], 1)}
MONTHS.update({k[:3]: v for k, v in list(MONTHS.items())})
MONTHS["sept"] = 9

_DAY = r"(\d{1,2})(?:st|nd|rd|th)?"
_MONTH = r"([A-Za-z]{3,9})\.?"
ISO_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
DAY_MONTH_NAME = re.compile(rf"\b{_DAY}\s+(?:day\s+of\s+)?{_MONTH},?\s+(\d{{4}})\b")   # 1 April 2026, 1st day of April, 2026
MONTH_NAME_DAY = re.compile(rf"\b{_MONTH}\s+{_DAY},?\s+(\d{{4}})\b")                    # April 1, 2026
NUMERIC_DATE = re.compile(r"\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b")                     # 01/04/2026, 04.01.2026
DATE_LABELS = {
    "effective_date": r"(?:effective\s+(?:from|on|date|as\s+of)|with\s+effect\s+from|commenc\w*\s+(?:from|on))",
    "expiry_date": r"(?:valid\s+(?:until|till|up\s*to)|in\s+force\s+(?:until|till|up\s*to)|expir\w*\s+on|terminat\w*\s+on|ending\s+on)",
    "execution_date": r"(?:executed\s+on|made\s+(?:on|this)|entered\s+into\s+on|signed\s+on|dated)",
}
REFERENCE = re.compile(r"\b(?:Ref(?:erence)?\.?\s*(?:No\.?|Number)?|(?:MOU|MoU|Agreement)\s*(?:No\.?|Number))\s*[:.\-]?\s*([A-Z0-9][A-Z0-9/\-._]{2,40})")


def _numeric(a: int, b: int, year: int, raw: str) -> tuple[date | None, str | None]:
    order = settings.date_order
    if order == "auto":
        if a > 12 and b <= 12:
            order = "dmy"
        elif b > 12 and a <= 12:
            order = "mdy"
        elif a == b:
            order = "dmy"
        else:
            return None, f"“{raw}” could be day/month or month/day; enter it from the document (or set DATE_ORDER)."
    day, month = (a, b) if order == "dmy" else (b, a)
    try:
        return date(year, month, day), None
    except ValueError:
        return None, f"“{raw}” is not a valid calendar date."


def parse_date(text: str) -> tuple[date | None, str | None]:
    """(date, warning). Numeric dates are read day-first or month-first only when unambiguous (or per DATE_ORDER)."""
    m = ISO_DATE.search(text)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3))), None
        except ValueError:
            return None, f"“{m.group(0)}” is not a valid calendar date."
    for pattern, day_first in ((DAY_MONTH_NAME, True), (MONTH_NAME_DAY, False)):
        m = pattern.search(text)
        if m:
            d, mon, year = (m.group(1), m.group(2), m.group(3)) if day_first else (m.group(2), m.group(1), m.group(3))
            month = MONTHS.get(mon.lower())
            if not month:
                continue
            try:
                return date(int(year), month, int(d)), None
            except ValueError:
                return None, f"“{m.group(0)}” is not a valid calendar date."
    m = NUMERIC_DATE.search(text)
    if m:
        return _numeric(int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(0))
    return None, None


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
        for m in AMOUNT_PATTERN.finditer(flat):
            raw = m.group(0).strip()
            key = ("amount", raw, number)
            if key in seen:
                continue
            seen.add(key)
            token, digits = m.group("cur") or m.group("cur2"), m.group("num") or m.group("num2")
            scale = (m.group("scale") or m.group("scale2") or "").strip()
            currency, amount = currency_of(token), parse_number(digits)
            notes = []
            if scale:
                notes.append(f"Stated with “{scale}”; not converted.")
            if currency is None:
                notes.append(f"“{token}” does not identify a single currency.")
            if amount is None and not scale:
                notes.append(f"“{digits.strip()}” could be read more than one way (decimal or thousands separator).")
            context = flat[max(0, m.start() - 80): m.end() + 40].strip()
            terms.append(ProposedFinancialTerm(
                term_type="other", description=f"Amount stated on page {number}: “{context[:200]}”",
                # Scale words are kept, never applied; an ambiguous currency or number leaves the amount for the reviewer.
                amount=None if scale or amount is None or currency is None else amount, currency=currency,
                basis="unspecified", ambiguity=" ".join(notes) or None, page=number, quote=raw[:300]))
    return ChunkExtraction(fields=fields, financial_terms=terms)
