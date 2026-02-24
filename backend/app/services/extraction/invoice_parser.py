import re
from datetime import date
from typing import Any

from dateutil import parser as dateparser

from app.core.logging import get_logger
from app.services.extraction.normalize import clean_amount

logger = get_logger("extraction.invoice_parser")


# ── Regex patterns ───────────────────────────────────────

INVOICE_NUMBER_PATTERNS = [
    r"invoice\s*#?\s*:?\s*([A-Z0-9\-]+)",
    r"inv\s*#?\s*:?\s*([A-Z0-9\-]+)",
    r"facture\s*#?\s*:?\s*([A-Z0-9\-]+)",
    r"bill\s*#?\s*:?\s*([A-Z0-9\-]+)",
    r"no\.?\s*:?\s*([A-Z0-9\-]+)",
]

DATE_PATTERNS = [
    r"(?:invoice\s*)?date\s*:?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    r"date\s*:?\s*(\w+\s+\d{1,2},?\s+\d{4})",
    r"(\d{4}[/\-]\d{2}[/\-]\d{2})",
]

DUE_DATE_PATTERNS = [
    r"due\s*date\s*:?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
    r"due\s*:?\s*(\w+\s+\d{1,2},?\s+\d{4})",
    r"payment\s*due\s*:?\s*(\d{1,2}[/\-\.]\d{1,2}[/\-\.]\d{2,4})",
]

TOTAL_PATTERNS = [
    r"total\s*(?:due)?\s*:?\s*\$?\s*([\d,]+\.?\d*)",
    r"amount\s*due\s*:?\s*\$?\s*([\d,]+\.?\d*)",
    r"balance\s*due\s*:?\s*\$?\s*([\d,]+\.?\d*)",
    r"grand\s*total\s*:?\s*\$?\s*([\d,]+\.?\d*)",
]

SUBTOTAL_PATTERNS = [
    r"sub\s*-?\s*total\s*:?\s*\$?\s*([\d,]+\.?\d*)",
]

TAX_PATTERNS = [
    r"(?:sales\s*)?tax\s*:?\s*\$?\s*([\d,]+\.?\d*)",
    r"(?:hst|gst|vat|tps|tvq)\s*:?\s*\$?\s*([\d,]+\.?\d*)",
]


def parse_invoice_fields(raw_text: str) -> dict[str, Any]:
    """Extract structured fields from raw invoice text using regex."""
    if not raw_text:
        return {"confidence": 0}

    text = raw_text  # keep original case for dates
    text_upper = raw_text.upper()  # for pattern matching

    result: dict[str, Any] = {}
    found_count = 0

    # Invoice number
    inv_num = _first_match(text_upper, INVOICE_NUMBER_PATTERNS)
    if inv_num:
        result["invoice_number"] = inv_num
        found_count += 1

    # Invoice date
    inv_date = _parse_date(_first_match(text, DATE_PATTERNS))
    if inv_date:
        result["invoice_date"] = inv_date
        found_count += 1

    # Due date
    due_date = _parse_date(_first_match(text, DUE_DATE_PATTERNS))
    if due_date:
        result["due_date"] = due_date
        found_count += 1

    # Total
    total = clean_amount(_first_match(text, TOTAL_PATTERNS) or "")
    if total:
        result["total"] = total
        found_count += 1

    # Subtotal
    subtotal = clean_amount(_first_match(text, SUBTOTAL_PATTERNS) or "")
    if subtotal:
        result["subtotal"] = subtotal
        found_count += 1

    # Tax
    tax = clean_amount(_first_match(text, TAX_PATTERNS) or "")
    if tax:
        result["tax"] = tax
        found_count += 1

    # Confidence score (how many fields we found out of 6 key fields)
    result["confidence"] = round((found_count / 6) * 100, 1)

    logger.info(f"Parsed {found_count}/6 fields (confidence: {result['confidence']}%)")
    return result


def _first_match(text: str, patterns: list[str]) -> str | None:
    """Return first regex group match across multiple patterns."""
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _parse_date(raw: str | None) -> date | None:
    """Try to parse a date string into a date object."""
    if not raw:
        return None
    try:
        return dateparser.parse(raw, fuzzy=True).date()
    except (ValueError, TypeError):
        return None
