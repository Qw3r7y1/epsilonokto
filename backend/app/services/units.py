"""Unit parsing, normalization, and conversion.

Handles three families:
  - weight:  g, oz, lb, kg  → normalized to grams (g)
  - volume:  ml, L, gal, fl oz, qt, pt  → normalized to milliliters (ml)
  - count:   each, case, pack, box, unit -> normalized to "ea" (individual units)

Case-pack notation like "5/20" means 5 cases × 20 per case = 100 total.
"""

import re
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional

from app.core.logging import get_logger

logger = get_logger("services.units")


# ── Conversion tables (everything → base unit) ──────────

# Weight → grams
WEIGHT_TO_GRAMS: dict[str, Decimal] = {
    "g":     Decimal("1"),
    "gram":  Decimal("1"),
    "grams": Decimal("1"),
    "gr":    Decimal("1"),
    "oz":    Decimal("28.3495"),
    "ounce": Decimal("28.3495"),
    "ounces": Decimal("28.3495"),
    "lb":    Decimal("453.592"),
    "lbs":   Decimal("453.592"),
    "pound": Decimal("453.592"),
    "pounds": Decimal("453.592"),
    "kg":    Decimal("1000"),
    "kilo":  Decimal("1000"),
    "kilos": Decimal("1000"),
    "kilogram":  Decimal("1000"),
    "kilograms": Decimal("1000"),
}

# Volume → milliliters
VOLUME_TO_ML: dict[str, Decimal] = {
    "ml":         Decimal("1"),
    "milliliter": Decimal("1"),
    "milliliters": Decimal("1"),
    "cl":         Decimal("10"),
    "l":          Decimal("1000"),
    "liter":      Decimal("1000"),
    "liters":     Decimal("1000"),
    "litre":      Decimal("1000"),
    "litres":     Decimal("1000"),
    "gal":        Decimal("3785.41"),
    "gallon":     Decimal("3785.41"),
    "gallons":    Decimal("3785.41"),
    "qt":         Decimal("946.353"),
    "quart":      Decimal("946.353"),
    "quarts":     Decimal("946.353"),
    "pt":         Decimal("473.176"),
    "pint":       Decimal("473.176"),
    "pints":      Decimal("473.176"),
    "fl oz":      Decimal("29.5735"),
    "floz":       Decimal("29.5735"),
    "fl. oz":     Decimal("29.5735"),
    "fluid ounce": Decimal("29.5735"),
}

# Count → each (factor = 1, these don't convert between each other)
COUNT_UNITS: set[str] = {
    "ea", "each", "unit", "units", "pc", "pcs", "piece", "pieces",
    "case", "cases", "cs",
    "pack", "packs", "pk", "pks",
    "box", "boxes", "bx",
    "bag", "bags",
    "can", "cans",
    "jar", "jars",
    "bottle", "bottles", "btl",
    "tray", "trays",
    "dozen", "doz",
}

# Display-friendly base units per mode
BASE_UNITS = {
    "weight": "g",
    "volume": "ml",
    "count": "ea",
}

# Preferred display conversions (from base → friendlier unit)
DISPLAY_CONVERSIONS = {
    "weight": {
        "kg": Decimal("1000"),
        "lb": Decimal("453.592"),
        "oz": Decimal("28.3495"),
        "g":  Decimal("1"),
    },
    "volume": {
        "L":    Decimal("1000"),
        "gal":  Decimal("3785.41"),
        "ml":   Decimal("1"),
    },
}


@dataclass
class ParsedQuantity:
    """Result of parsing a quantity expression from an invoice line."""
    raw_text: str                          # original text, e.g. "5/20", "10 lb"
    cases: Optional[Decimal] = None        # 5 (if case-pack)
    units_per_case: Optional[Decimal] = None  # 20 (if case-pack)
    total_quantity: Optional[Decimal] = None   # 100 (computed or direct)
    raw_unit: Optional[str] = None          # "oz", "lb", "ea", etc.
    unit_family: Optional[str] = None       # "weight", "volume", "count", or None
    normalized_quantity: Optional[Decimal] = None  # in base unit (g/ml/ea)
    normalized_unit: Optional[str] = None   # "g", "ml", "ea"


def parse_quantity(raw: str) -> ParsedQuantity:
    """Parse quantity text from an invoice line item.

    Handles formats:
      "5/20"         → 5 cases × 20 = 100 (unit from context)
      "5/20 oz"      → 5 cases × 20 oz = 100 oz
      "5x20"         → same as 5/20
      "10 lb"        → 10 lb
      "10"           → 10 (no unit)
      "3 cases"      → 3 cases
      "2/12 gal"     → 2 cases × 12 gal = 24 gal
    """
    result = ParsedQuantity(raw_text=raw.strip())
    text = raw.strip()

    if not text:
        return result

    # ── Step 1: Detect case-pack format (5/20, 5x20, 5\20) ─────
    case_pack_match = re.match(
        r"(\d+(?:\.\d+)?)\s*[/xX×\\]\s*(\d+(?:\.\d+)?)\s*(.*)",
        text,
    )

    if case_pack_match:
        result.cases = Decimal(case_pack_match.group(1))
        result.units_per_case = Decimal(case_pack_match.group(2))
        result.total_quantity = result.cases * result.units_per_case
        unit_text = case_pack_match.group(3).strip()
    else:
        # ── Step 2: Simple quantity + unit ──────────────────────
        simple_match = re.match(
            r"(\d+(?:[.,]\d+)?)\s*(.*)",
            text,
        )
        if simple_match:
            qty_str = simple_match.group(1).replace(",", "")
            result.total_quantity = Decimal(qty_str)
            unit_text = simple_match.group(2).strip()
        else:
            return result

    # ── Step 3: Parse the unit ──────────────────────────────
    if unit_text:
        result.raw_unit = _normalize_unit_text(unit_text)
        result.unit_family = _detect_unit_family(result.raw_unit)

    # ── Step 4: Normalize to base unit ──────────────────────
    if result.total_quantity is not None and result.raw_unit:
        _apply_normalization(result)

    return result


def normalize_price(
    total_price: Decimal,
    parsed_qty: ParsedQuantity,
) -> Optional[Decimal]:
    """Calculate the normalized per-unit price.

    Returns price per gram, per ml, or per unit depending on the unit family.
    """
    if not parsed_qty.normalized_quantity or parsed_qty.normalized_quantity == 0:
        return None

    return (total_price / parsed_qty.normalized_quantity).quantize(
        Decimal("0.000001"), rounding=ROUND_HALF_UP
    )


def convert_to_display_unit(
    quantity_in_base: Decimal,
    family: str,
    target_unit: Optional[str] = None,
) -> tuple[Decimal, str]:
    """Convert from base unit (g/ml/ea) to a display-friendly unit.

    If target_unit is specified, convert to that.
    Otherwise, pick the most readable unit.
    """
    if family == "count" or family not in DISPLAY_CONVERSIONS:
        return quantity_in_base, "ea"

    conversions = DISPLAY_CONVERSIONS[family]

    if target_unit and target_unit.lower() in conversions:
        factor = conversions[target_unit.lower()]
        return (quantity_in_base / factor).quantize(Decimal("0.001")), target_unit

    # Auto-pick: use the largest unit that gives a value >= 1
    for unit, factor in conversions.items():
        value = quantity_in_base / factor
        if value >= 1:
            return value.quantize(Decimal("0.001")), unit

    return quantity_in_base, BASE_UNITS.get(family, "ea")


# ── Internal helpers ─────────────────────────────────────

def _normalize_unit_text(raw: str) -> str:
    """Clean up unit text: lowercase, strip dots/spaces."""
    cleaned = raw.lower().strip().rstrip(".")
    # Handle "fl oz" / "fl. oz" / "fl.oz"
    cleaned = re.sub(r"fl\.?\s*oz\.?", "fl oz", cleaned)
    return cleaned


def _detect_unit_family(unit: str) -> Optional[str]:
    """Determine if a unit is weight, volume, or count."""
    if unit in WEIGHT_TO_GRAMS:
        return "weight"
    if unit in VOLUME_TO_ML:
        return "volume"
    if unit in COUNT_UNITS:
        return "count"
    return None


def _apply_normalization(result: ParsedQuantity) -> None:
    """Convert total_quantity + raw_unit to normalized base unit."""
    unit = result.raw_unit
    qty = result.total_quantity

    if not unit or qty is None:
        return

    if unit in WEIGHT_TO_GRAMS:
        factor = WEIGHT_TO_GRAMS[unit]
        result.normalized_quantity = (qty * factor).quantize(Decimal("0.0001"))
        result.normalized_unit = "g"
    elif unit in VOLUME_TO_ML:
        factor = VOLUME_TO_ML[unit]
        result.normalized_quantity = (qty * factor).quantize(Decimal("0.0001"))
        result.normalized_unit = "ml"
    elif unit in COUNT_UNITS:
        # For count, handle "dozen" → multiply by 12
        if unit in ("dozen", "doz"):
            result.normalized_quantity = qty * Decimal("12")
        else:
            result.normalized_quantity = qty
        result.normalized_unit = "ea"
