"""Deterministic validators for extracted data: arithmetic consistency and duplicates.

Generic rules only — no values from any particular agreement. A mismatch is reported with the numbers involved;
contractual values are never changed to make the arithmetic balance. Amounts are compared only within one table
column or one currency, never across currencies, units, or financial concepts.
"""
import re
from collections.abc import Iterable

from app.money import parse_number as money_parse, strip_currency

TOLERANCE = 0.5  # rupee/paisa-level rounding in printed figures
TOTAL_ROW = re.compile(r"^\s*(grand\s+|sub[\s-]?)?total\b", re.IGNORECASE)
PERIOD_HEADER = re.compile(r"^\s*(q[1-4]|quarter\s*[1-4]|h[12]|half[\s-]?year\s*[12]|year\s*\d|y\d|fy\s*\d{2,4}(-\d{2,4})?|"
                           r"jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\b", re.IGNORECASE)
TOTAL_HEADER = re.compile(r"\btotal\b", re.IGNORECASE)
QUANTITY_HEADER = re.compile(r"\b(students?|learners?|beneficiar\w*|participants?|target|no\.|number|qty|quantity|units?|batches)\b", re.IGNORECASE)
UNIT_COST_HEADER = re.compile(r"\b(per|unit\s+cost|rate|cost\s+per)\b", re.IGNORECASE)


def parse_number(cell: str | None) -> float | None:
    """A number written in a table cell, in any common format and with any currency marker (see app.money).
    Percentages, ranges, text, and ambiguous numbers return None, so they are never summed with amounts."""
    if cell is None:
        return None
    text = cell.strip()
    if not text or "%" in text:
        return None
    text, _ = strip_currency(text)
    text = re.sub(r"\s*/-\s*$", "", text).strip()
    return money_parse(text)


def _fmt(value: float) -> str:
    return f"{value:,.2f}".rstrip("0").rstrip(".")


def _label(row: dict) -> str:
    return next((c for c in row["cells"] if c and parse_number(c) is None), f"row {row['row_index']}")


def table_checks(table: dict) -> list[tuple[str, str, str]]:
    """(code, message, field) for each arithmetic inconsistency found in one table."""
    issues: list[tuple[str, str, str]] = []
    headers, rows = table["headers"], table["rows"]
    title = table["title"][:80]
    # 1. Total rows: the sum of the rows since the previous total equals the total (grand total includes the
    #    previous total and the rows after it).
    previous_total: dict | None = None
    group: list[dict] = []
    for row in rows:
        label = _label(row)
        if TOTAL_ROW.match(label):
            components = ([previous_total] if previous_total and label.lower().startswith("grand") else []) + group
            for col, header in enumerate(headers):
                if col >= len(row["cells"]) or "%" in header:
                    continue
                stated = parse_number(row["cells"][col])
                values = [parse_number(r["cells"][col]) if col < len(r["cells"]) else None for r in components]
                if stated is None or not components or any(v is None for v in values):
                    continue  # only compare when every component is a readable number
                computed = sum(values)
                if abs(computed - stated) > TOLERANCE:
                    issues.append(("ARITHMETIC_MISMATCH",
                                   f"“{title}”, {label} row, column “{header}”: stated {_fmt(stated)}, but the rows above add up to "
                                   f"{_fmt(computed)}. The stated value is kept; check the page.", header))
            previous_total, group = row, []
        else:
            group.append(row)
    # 2. Period columns (Q1..Q4, months, years) against a total column, row by row.
    periods = [i for i, h in enumerate(headers) if PERIOD_HEADER.match(h) and not TOTAL_HEADER.search(h)]
    totals = [i for i, h in enumerate(headers) if TOTAL_HEADER.search(h)]
    if len(periods) >= 2 and len(totals) == 1:
        t = totals[0]
        for row in rows:
            cells = row["cells"]
            stated = parse_number(cells[t]) if t < len(cells) else None
            values = [parse_number(cells[i]) if i < len(cells) else None for i in periods]
            if stated is None or any(v is None for v in values):
                continue
            if abs(sum(values) - stated) > TOLERANCE:
                issues.append(("ARITHMETIC_MISMATCH",
                               f"“{title}”, {_label(row)}: {', '.join(headers[i] for i in periods)} add up to {_fmt(sum(values))}, "
                               f"but “{headers[t]}” states {_fmt(stated)}.", headers[t]))
    # 3. Quantity × unit cost = line total (one column of each kind, identified by header wording).
    qty = [i for i, h in enumerate(headers) if QUANTITY_HEADER.search(h) and not UNIT_COST_HEADER.search(h) and not TOTAL_HEADER.search(h)]
    unit = [i for i, h in enumerate(headers) if UNIT_COST_HEADER.search(h) and not TOTAL_HEADER.search(h)]
    if len(qty) == 1 and len(unit) == 1 and len(totals) == 1:
        q, u, t = qty[0], unit[0], totals[0]
        for row in rows:
            cells = row["cells"]
            if TOTAL_ROW.match(_label(row)) or max(q, u, t) >= len(cells):
                continue
            a, b, stated = parse_number(cells[q]), parse_number(cells[u]), parse_number(cells[t])
            if None in (a, b, stated):
                continue
            if abs(a * b - stated) > TOLERANCE:
                issues.append(("ARITHMETIC_MISMATCH",
                               f"“{title}”, {_label(row)}: {headers[q]} {_fmt(a)} × {headers[u]} {_fmt(b)} = {_fmt(a * b)}, "
                               f"but “{headers[t]}” states {_fmt(stated)}.", headers[t]))
    return issues


def tranche_checks(terms: Iterable[dict]) -> list[tuple[str, str, str]]:
    """Tranches of one currency against the stated total commitment(s) in that currency."""
    issues = []
    terms = [t for t in terms if t.get("amount") is not None and t.get("currency")]
    for currency in sorted({t["currency"] for t in terms}):
        tranches = [t["amount"] for t in terms if t["currency"] == currency and t["term_type"] == "tranche"]
        commitments = sorted({t["amount"] for t in terms if t["currency"] == currency and t["term_type"] == "total_commitment"})
        if len(tranches) < 2 or not commitments:
            continue
        total = sum(tranches)
        if all(abs(total - c) > TOLERANCE for c in commitments):
            issues.append(("TRANCHE_TOTAL_MISMATCH",
                           f"{len(tranches)} tranches add up to {currency} {_fmt(total)}, but the stated total commitment is "
                           f"{' or '.join(f'{currency} {_fmt(c)}' for c in commitments)}. Neither value was changed.", "amount"))
    return issues


def _dedupe_key(collection: str, item: dict) -> tuple:
    quote = " ".join(((item.get("evidence") or {}).get("quote") or "").lower().split())
    keys = {"clauses": ("clause_type",), "financial_terms": ("term_type", "amount", "currency", "due_date"),
            "obligations": ("obligation_type", "title", "due_date"), "programme_scope": ("dimension", "value", "location")}
    return tuple(str(item.get(k)).lower() for k in keys[collection]) + (quote,)


def remove_duplicates(out: dict[str, list[dict]]) -> int:
    """Drop proposals identical to an earlier one (same kind, values, and quote). Returns how many were dropped."""
    dropped = 0
    for collection in ("clauses", "financial_terms", "obligations", "programme_scope"):
        seen, kept = set(), []
        for item in out[collection]:
            key = _dedupe_key(collection, item)
            if key in seen:
                dropped += 1
                continue
            seen.add(key)
            kept.append(item)
        out[collection] = kept
    return dropped
