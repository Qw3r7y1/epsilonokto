"""
Unit conversion and quantity parsing.

Supported invoice quantity formats:
  "5/20 oz"   → 5 cases × 20 oz each
  "3x24 gal"  → 3 cases × 24 gal each
  "10 lb"     → 10 lb
  "3 cases"   → 3 ea (no sub-unit)
  "500 g"     → 500 g
"""

import re
from dataclasses import dataclass
from typing import Optional

# ---------------------------------------------------------------------------
# Conversion factors → base units (grams / millilitres / each)
# ---------------------------------------------------------------------------

_WEIGHT_TO_G: dict[str, float] = {
    "g": 1.0,
    "gram": 1.0,
    "grams": 1.0,
    "kg": 1000.0,
    "kilogram": 1000.0,
    "kilograms": 1000.0,
    "oz": 28.3495,
    "ounce": 28.3495,
    "ounces": 28.3495,
    "lb": 453.592,
    "lbs": 453.592,
    "pound": 453.592,
    "pounds": 453.592,
}

_VOLUME_TO_ML: dict[str, float] = {
    "ml": 1.0,
    "milliliter": 1.0,
    "milliliters": 1.0,
    "millilitre": 1.0,
    "millilitres": 1.0,
    "l": 1000.0,
    "liter": 1000.0,
    "liters": 1000.0,
    "litre": 1000.0,
    "litres": 1000.0,
    "fl oz": 29.5735,
    "floz": 29.5735,
    "fl. oz": 29.5735,
    "fl. oz.": 29.5735,
    "cup": 236.588,
    "cups": 236.588,
    "pt": 473.176,
    "pint": 473.176,
    "pints": 473.176,
    "qt": 946.353,
    "quart": 946.353,
    "quarts": 946.353,
    "gal": 3785.41,
    "gallon": 3785.41,
    "gallons": 3785.41,
}

_COUNT_UNITS = {"ea", "each", "pc", "pcs", "piece", "pieces", "count", "ct", "unit", "units"}


@dataclass
class ParsedQuantity:
    cases: Optional[float]
    units_per_case: Optional[float]
    unit_size: Optional[float]
    unit_size_unit: Optional[str]  # raw string, e.g. "oz"
    total_base_quantity: Optional[float]  # in base unit (g / ml / ea)
    base_unit: Optional[str]  # "g", "ml", or "ea"


def _normalise_unit(raw: str) -> str:
    return raw.strip().lower().rstrip(".")


def to_grams(value: float, unit: str) -> Optional[float]:
    factor = _WEIGHT_TO_G.get(_normalise_unit(unit))
    return value * factor if factor is not None else None


def to_ml(value: float, unit: str) -> Optional[float]:
    factor = _VOLUME_TO_ML.get(_normalise_unit(unit))
    return value * factor if factor is not None else None


def is_weight_unit(unit: str) -> bool:
    return _normalise_unit(unit) in _WEIGHT_TO_G


def is_volume_unit(unit: str) -> bool:
    return _normalise_unit(unit) in _VOLUME_TO_ML


def is_count_unit(unit: str) -> bool:
    return _normalise_unit(unit) in _COUNT_UNITS


# ---------------------------------------------------------------------------
# Quantity string parser
# ---------------------------------------------------------------------------

_CASE_PACK_RE = re.compile(
    r"""
    ^\s*
    (?P<cases>\d+(?:\.\d+)?)          # cases / outer quantity
    \s*[/x×]\s*                        # separator: / or x or ×
    (?P<qty>\d+(?:\.\d+)?)             # inner quantity
    \s*
    (?P<unit>[a-zA-Z. ]+)?             # optional unit
    \s*$
    """,
    re.VERBOSE,
)

_SIMPLE_RE = re.compile(
    r"""
    ^\s*
    (?P<qty>\d+(?:\.\d+)?)
    \s*
    (?P<unit>[a-zA-Z. ]+)?
    \s*$
    """,
    re.VERBOSE,
)


def parse_quantity(raw: str) -> ParsedQuantity:
    """Parse a raw quantity string from an invoice line item."""
    raw = raw.strip()

    m = _CASE_PACK_RE.match(raw)
    if m:
        cases = float(m.group("cases"))
        qty = float(m.group("qty"))
        unit_raw = (m.group("unit") or "ea").strip()
        unit_norm = _normalise_unit(unit_raw)

        total: Optional[float] = None
        base_unit: Optional[str] = None
        if is_weight_unit(unit_norm):
            total = to_grams(cases * qty, unit_norm)
            base_unit = "g"
        elif is_volume_unit(unit_norm):
            total = to_ml(cases * qty, unit_norm)
            base_unit = "ml"
        else:
            total = cases * qty
            base_unit = "ea"

        return ParsedQuantity(
            cases=cases,
            units_per_case=qty,
            unit_size=None,
            unit_size_unit=unit_raw if unit_norm not in _COUNT_UNITS else None,
            total_base_quantity=total,
            base_unit=base_unit,
        )

    m = _SIMPLE_RE.match(raw)
    if m:
        qty = float(m.group("qty"))
        unit_raw = (m.group("unit") or "ea").strip()
        unit_norm = _normalise_unit(unit_raw)

        total: Optional[float] = None
        base_unit: Optional[str] = None
        if is_weight_unit(unit_norm):
            total = to_grams(qty, unit_norm)
            base_unit = "g"
        elif is_volume_unit(unit_norm):
            total = to_ml(qty, unit_norm)
            base_unit = "ml"
        else:
            total = qty
            base_unit = "ea"

        return ParsedQuantity(
            cases=None,
            units_per_case=None,
            unit_size=qty,
            unit_size_unit=unit_raw,
            total_base_quantity=total,
            base_unit=base_unit,
        )

    # Unparseable — return raw as-is with no normalization
    return ParsedQuantity(
        cases=None,
        units_per_case=None,
        unit_size=None,
        unit_size_unit=None,
        total_base_quantity=None,
        base_unit=None,
    )
