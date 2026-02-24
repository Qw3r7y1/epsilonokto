"""Line item extraction from invoice text.

Handles formats like:
  Butter unsalted    5/20 oz    $3.45    $345.00
  Olive oil          2/12 gal   $18.99   $455.76
  Sugar              10 lb      $0.89    $8.90
  Napkins            3 cases    $12.00   $36.00
"""

import re
from decimal import Decimal
from typing import Optional

from app.core.logging import get_logger
from app.services.units import parse_quantity, normalize_price, ParsedQuantity
from app.services.extraction.normalize import clean_amount

logger = get_logger("extraction.line_items")


# Patterns for matching line items in invoice text
LINE_PATTERNS = [
    # Pattern 1: description | qty/qty unit | $price | $total
    # e.g., "Butter unsalted    5/20 oz    $3.45    $345.00"
    re.compile(
        r"^(.+?)\s{2,}"                           # description (2+ spaces separator)
        r"(\d+(?:\.\d+)?\s*[/xX×]\s*\d+(?:\.\d+)?"  # case-pack qty: 5/20
        r"(?:\s+\w+(?:\.\s*\w+)?)?)\s{2,}"         # optional unit after case-pack
        r"\$?([\d,]+\.?\d*)\s{2,}"                 # unit price
        r"\$?([\d,]+\.?\d*)",                      # total price
        re.IGNORECASE,
    ),

    # Pattern 2: description | simple qty unit | $price | $total
    # e.g., "Sugar    10 lb    $0.89    $8.90"
    re.compile(
        r"^(.+?)\s{2,}"                            # description
        r"(\d+(?:[.,]\d+)?"                         # quantity
        r"(?:\s+\w+(?:\.\s*\w+)?)?)\s{2,}"          # optional unit
        r"\$?([\d,]+\.?\d*)\s{2,}"                  # unit price
        r"\$?([\d,]+\.?\d*)",                       # total price
        re.IGNORECASE,
    ),

    # Pattern 3: tab-separated columns
    re.compile(
        r"^(.+?)\t+"                               # description
        r"(\d+(?:\.\d+)?(?:\s*[/xX]\s*\d+(?:\.\d+)?)?)"  # qty or case-pack
        r"(?:\s+(\w+))?\t+"                         # unit
        r"\$?([\d,]+\.?\d*)\t+"                     # unit price
        r"\$?([\d,]+\.?\d*)",                       # total
        re.IGNORECASE,
    ),
]

# Words that indicate a line is NOT a line item
SKIP_WORDS = {
    "subtotal", "sub-total", "sub total", "total", "tax", "shipping",
    "discount", "balance", "amount due", "grand total", "invoice",
    "date", "bill to", "ship to", "description", "qty", "quantity",
    "price", "item", "product", "unit", "ext", "extended",
}


def extract_line_items(raw_text: str) -> list[dict]:
    """Extract line items from invoice text.

    Returns a list of dicts with keys:
        description, raw_quantity_text, cases, units_per_case,
        raw_quantity, raw_unit, normalized_quantity, normalized_unit,
        unit_price, total_price, normalized_unit_price, position
    """
    if not raw_text:
        return []

    items = []
    position = 0

    for line in raw_text.splitlines():
        line = line.strip()
        if not line or len(line) < 5:
            continue

        if _is_skip_line(line):
            continue

        parsed = _try_parse_line(line)
        if parsed:
            position += 1
            parsed["position"] = position
            items.append(parsed)

    logger.info(f"Extracted {len(items)} line items")
    return items


def _try_parse_line(line: str) -> Optional[dict]:
    """Try each pattern against a line and return parsed data or None."""
    for pattern in LINE_PATTERNS:
        match = pattern.match(line)
        if match:
            return _build_item_from_match(match)

    return _try_loose_parse(line)


def _build_item_from_match(match: re.Match) -> Optional[dict]:
    """Build a line item dict from a regex match."""
    groups = match.groups()

    description = groups[0].strip()
    qty_text = groups[1].strip() if len(groups) > 1 else ""

    price_groups = [g for g in groups[2:] if g]
    unit_price_raw = price_groups[0] if len(price_groups) >= 1 else None
    total_price_raw = price_groups[1] if len(price_groups) >= 2 else unit_price_raw

    parsed_qty = parse_quantity(qty_text)

    unit_price = clean_amount(unit_price_raw) if unit_price_raw else None
    total_price = clean_amount(total_price_raw) if total_price_raw else None

    norm_price = None
    if total_price and parsed_qty.normalized_quantity:
        norm_price = normalize_price(Decimal(str(total_price)), parsed_qty)

    return _to_dict(description, parsed_qty, unit_price, total_price, norm_price)


def _try_loose_parse(line: str) -> Optional[dict]:
    """Loose fallback: look for a line with at least a dollar amount."""
    dollar_matches = re.findall(r"\$\s*([\d,]+\.?\d*)", line)
    if not dollar_matches:
        return None

    case_pack = re.search(r"(\d+)\s*[/xX×]\s*(\d+)", line)
    qty_unit = re.search(
        r"(\d+(?:\.\d+)?)\s+(oz|lb|lbs|kg|g|gal|L|ml|ea|cases?|packs?)\b", line, re.I
    )

    qty_text = ""
    if case_pack:
        upc = case_pack.group(0)
        after = line[case_pack.end():].strip()
        unit_after = re.match(r"(\w+)", after)
        qty_text = f"{upc} {unit_after.group(1)}" if unit_after else upc
    elif qty_unit:
        qty_text = qty_unit.group(0)

    parsed_qty = parse_quantity(qty_text) if qty_text else ParsedQuantity(raw_text="")

    desc_match = re.match(r"^([A-Za-z][\w\s,&\-']+?)(?=\s+\d)", line)
    description = desc_match.group(1).strip() if desc_match else line[:50].strip()

    total_price = clean_amount(dollar_matches[-1]) if dollar_matches else None
    unit_price = clean_amount(dollar_matches[0]) if len(dollar_matches) >= 2 else total_price

    norm_price = None
    if total_price and parsed_qty.normalized_quantity:
        norm_price = normalize_price(Decimal(str(total_price)), parsed_qty)

    return _to_dict(description, parsed_qty, unit_price, total_price, norm_price)


def _to_dict(
    description: str,
    parsed_qty: ParsedQuantity,
    unit_price: Optional[float],
    total_price: Optional[float],
    norm_price: Optional[Decimal],
) -> dict:
    return {
        "description": description,
        "raw_quantity_text": parsed_qty.raw_text,
        "cases": float(parsed_qty.cases) if parsed_qty.cases else None,
        "units_per_case": float(parsed_qty.units_per_case) if parsed_qty.units_per_case else None,
        "raw_quantity": float(parsed_qty.total_quantity) if parsed_qty.total_quantity else None,
        "raw_unit": parsed_qty.raw_unit,
        "normalized_quantity": float(parsed_qty.normalized_quantity) if parsed_qty.normalized_quantity else None,
        "normalized_unit": parsed_qty.normalized_unit,
        "unit_price": unit_price,
        "total_price": total_price,
        "normalized_unit_price": float(norm_price) if norm_price else None,
    }


def _is_skip_line(line: str) -> bool:
    """Check if line is a header, total, or other non-item line."""
    lower = line.lower().strip()
    for word in SKIP_WORDS:
        if lower.startswith(word):
            return True
    if re.match(r"^[\-=_]{5,}$", lower):
        return True
    return False
