"""
Invoice field extraction from raw OCR/PDF text.

Extracts:
  - Invoice number
  - Invoice date
  - Vendor name (heuristic)
  - Total amount
  - Line items (description, quantity, unit price, total)
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from app.core.logging import get_logger
from app.services.units import parse_quantity, ParsedQuantity

log = get_logger(__name__)

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

_INVOICE_NO_RE = re.compile(
    r"(?:invoice\s*(?:#|no\.?|number)?|inv\.?)\s*[:\-]?\s*([A-Z0-9\-]+)",
    re.IGNORECASE,
)

_DATE_PATTERNS = [
    re.compile(r"\b(\d{1,2})[/\-](\d{1,2})[/\-](\d{2,4})\b"),   # MM/DD/YY(YY)
    re.compile(r"\b(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})\b"),      # YYYY-MM-DD
    re.compile(
        r"\b(\d{1,2})\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*"
        r"\s+(\d{4})\b",
        re.IGNORECASE,
    ),
]

_MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

_TOTAL_RE = re.compile(
    r"(?:total|amount\s*due|balance\s*due|grand\s*total)\s*[:\$]?\s*([\d,]+\.\d{2})",
    re.IGNORECASE,
)

# Heuristic line item pattern: description | qty | unit | price | total
_LINE_ITEM_RE = re.compile(
    r"^(.{3,50}?)\s{2,}"          # description (left-aligned, tab-separated)
    r"([\d./x×]+\s*[a-zA-Z]*)\s{2,}"  # quantity
    r"\$?([\d,]+\.\d{2,4})\s{2,}"     # unit price
    r"\$?([\d,]+\.\d{2})",             # line total
    re.MULTILINE,
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class RawLineItem:
    description: str
    raw_quantity: str
    raw_unit_price: float
    raw_total: float
    parsed_quantity: Optional[ParsedQuantity] = None
    line_number: Optional[int] = None


@dataclass
class ParsedInvoice:
    invoice_number: Optional[str] = None
    invoice_date: Optional[datetime] = None
    vendor_name: Optional[str] = None
    total_amount: Optional[float] = None
    line_items: list[RawLineItem] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_date(text: str) -> Optional[datetime]:
    for pattern in _DATE_PATTERNS:
        for m in pattern.finditer(text):
            try:
                groups = m.groups()
                if len(groups) == 3:
                    a, b, c = groups
                    # Check for named month
                    if isinstance(b, str) and b[:3].lower() in _MONTH_MAP:
                        return datetime(int(c), _MONTH_MAP[b[:3].lower()], int(a))
                    # YYYY-MM-DD
                    if len(a) == 4:
                        return datetime(int(a), int(b), int(c))
                    # MM/DD/YY or MM/DD/YYYY
                    year = int(c)
                    if year < 100:
                        year += 2000
                    return datetime(year, int(a), int(b))
            except (ValueError, TypeError):
                continue
    return None


def _parse_float(s: str) -> Optional[float]:
    try:
        return float(s.replace(",", ""))
    except (ValueError, AttributeError):
        return None


# ---------------------------------------------------------------------------
# Main parser
# ---------------------------------------------------------------------------

def parse_invoice_text(text: str) -> ParsedInvoice:
    result = ParsedInvoice()

    # Invoice number
    m = _INVOICE_NO_RE.search(text)
    if m:
        result.invoice_number = m.group(1).strip()

    # Date (use first found)
    result.invoice_date = _parse_date(text)

    # Total
    totals = _TOTAL_RE.findall(text)
    if totals:
        result.total_amount = _parse_float(totals[-1])  # last match = grand total

    # Line items
    for i, m in enumerate(_LINE_ITEM_RE.finditer(text), start=1):
        desc, qty_raw, price_raw, total_raw = m.groups()
        unit_price = _parse_float(price_raw)
        line_total = _parse_float(total_raw)
        if unit_price is None or line_total is None:
            continue

        parsed_qty = parse_quantity(qty_raw.strip())

        result.line_items.append(
            RawLineItem(
                description=desc.strip(),
                raw_quantity=qty_raw.strip(),
                raw_unit_price=unit_price,
                raw_total=line_total,
                parsed_quantity=parsed_qty,
                line_number=i,
            )
        )

    log.info(
        "Parsed invoice: number=%s date=%s total=%s items=%d",
        result.invoice_number,
        result.invoice_date,
        result.total_amount,
        len(result.line_items),
    )
    return result
