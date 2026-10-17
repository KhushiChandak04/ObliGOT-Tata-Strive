"""Currency and number reading for any country's documents. Deterministic; never guesses.

- Currencies: ISO 4217 codes and symbols that identify exactly one currency. Symbols shared by several currencies
  ("$", "¥", "kr", "Fr") return no currency, so the reviewer decides; nothing is assumed from the user's country.
- Numbers: "1,234,567.89", "12,34,567" (Indian grouping), "1.234.567,89", "1 234 567,89", "1'234'567.89".
  A single separator followed by exactly three digits is a thousands separator for "," and ambiguous for "."
  (e.g. "1.500" is 1500 in many European documents and 1.5 elsewhere) unless NUMBER_DECIMAL_SEPARATOR says otherwise.
- Scale words (thousand, lakh, crore, million, billion, k, mn, bn, cr) are kept as written and never applied.
"""
import re

from app.config import settings

# Common ISO 4217 codes. Any of these next to a number identifies the currency.
ISO_CODES = {
    "AED", "ARS", "AUD", "BDT", "BRL", "CAD", "CHF", "CLP", "CNY", "COP", "CZK", "DKK", "EGP", "ETB", "EUR", "GBP", "GHS",
    "HKD", "HUF", "IDR", "ILS", "INR", "JPY", "KES", "KRW", "KWD", "LKR", "MAD", "MXN", "MYR", "NGN", "NOK", "NPR", "NZD",
    "PEN", "PHP", "PKR", "PLN", "QAR", "RON", "RUB", "RWF", "SAR", "SEK", "SGD", "THB", "TRY", "TWD", "TZS", "UAH", "UGX",
    "USD", "VND", "XAF", "XOF", "ZAR", "ZMW",
}
# Symbols and abbreviations that name exactly one currency.
UNAMBIGUOUS = {
    "₹": "INR", "rs": "INR", "rs.": "INR", "€": "EUR", "£": "GBP", "₦": "NGN", "₱": "PHP", "₩": "KRW", "₪": "ILS", "₺": "TRY",
    "₫": "VND", "฿": "THB", "₴": "UAH", "₽": "RUB", "৳": "BDT", "us$": "USD", "a$": "AUD", "c$": "CAD", "s$": "SGD",
    "hk$": "HKD", "nz$": "NZD", "r$": "BRL", "ksh": "KES", "zł": "PLN",
}
AMBIGUOUS = {"$", "¥", "kr", "fr", "fr.", "r", "rp"}  # shared by several currencies: never resolved automatically
SCALE_WORDS = r"thousand|lakhs?|lacs?|crores?|cr|million|mn|billion|bn|k"

_symbols = sorted(set(UNAMBIGUOUS) | AMBIGUOUS, key=len, reverse=True)
CURRENCY_TOKEN = r"(?:" + "|".join(re.escape(s) for s in _symbols) + r"|\b(?:" + "|".join(sorted(ISO_CODES)) + r")\b)"
NUMBER = r"\d[\d,.'   ]*\d|\d"
# "<currency> <number> [scale]" or "<number> [scale] <currency code>"
AMOUNT_PATTERN = re.compile(
    rf"(?P<cur>{CURRENCY_TOKEN})\s*(?P<num>{NUMBER})(?:\s*/-)?(?:\s*(?P<scale>{SCALE_WORDS})\b)?"
    rf"|(?P<num2>{NUMBER})(?:\s*(?P<scale2>{SCALE_WORDS})\b)?\s*(?P<cur2>\b(?:{'|'.join(sorted(ISO_CODES))})\b)",
    re.IGNORECASE)


def currency_of(token: str | None) -> str | None:
    """ISO code for an unambiguous currency token; None for ambiguous or unknown tokens."""
    if not token:
        return None
    t = token.strip().lower()
    if t.upper() in ISO_CODES:
        return t.upper()
    return UNAMBIGUOUS.get(t)


def parse_number(text: str | None, decimal: str | None = None) -> float | None:
    """A number as written; None when it is malformed or its decimal separator is ambiguous."""
    if text is None:
        return None
    s = re.sub(r"[   ']", "", text.strip())
    if not s or not re.fullmatch(r"-?\d[\d,.]*", s):
        return None
    decimal = decimal or settings.number_decimal_separator
    commas, dots = s.count(","), s.count(".")
    if decimal == ".":
        return _to_float(s.replace(",", ""))
    if decimal == ",":
        return _to_float(s.replace(".", "").replace(",", "."))
    # auto
    if commas and dots:  # the last separator is the decimal one
        return _to_float(s.replace(",", "").replace(".", ".") if s.rfind(".") > s.rfind(",") else s.replace(".", "").replace(",", "."))
    if commas > 1 or dots > 1:  # repeated separator: grouping (incl. Indian 12,34,567)
        sep = "," if commas > 1 else "."
        return _to_float(s.replace(sep, ""))
    if commas == 1:
        whole, frac = s.split(",")
        return _to_float(whole + frac) if len(frac) == 3 else _to_float(f"{whole}.{frac}")
    if dots == 1:
        whole, frac = s.split(".")
        return None if len(frac) == 3 else _to_float(s)  # "1.500": thousands or decimal? not guessed
    return _to_float(s)


def _to_float(s: str) -> float | None:
    try:
        return float(s)
    except ValueError:
        return None


def strip_currency(cell: str) -> tuple[str, str | None]:
    """(text without a leading/trailing currency token, ISO code or None)."""
    text = cell.strip()
    m = re.match(rf"^\s*({CURRENCY_TOKEN})\s*", text, re.IGNORECASE)
    if m:
        return text[m.end():], currency_of(m.group(1))
    m = re.search(rf"\s*\b({'|'.join(sorted(ISO_CODES))})\b\s*$", text, re.IGNORECASE)
    if m:
        return text[: m.start()], currency_of(m.group(1))
    return text, None
