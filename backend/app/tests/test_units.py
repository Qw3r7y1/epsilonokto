"""Tests for unit conversion and quantity parsing."""

import pytest
from app.services.units import parse_quantity


@pytest.mark.parametrize(
    "raw, expected_base_unit, expected_total",
    [
        ("5/20 oz", "g", pytest.approx(5 * 20 * 28.3495, rel=1e-3)),
        ("3x24 gal", "ml", pytest.approx(3 * 24 * 3785.41, rel=1e-3)),
        ("10 lb", "g", pytest.approx(10 * 453.592, rel=1e-3)),
        ("500 g", "g", pytest.approx(500.0)),
        ("2 L", "ml", pytest.approx(2000.0)),
        ("3 cases", "ea", pytest.approx(3.0)),
        ("12 ea", "ea", pytest.approx(12.0)),
    ],
)
def test_parse_quantity(raw, expected_base_unit, expected_total):
    result = parse_quantity(raw)
    assert result.base_unit == expected_base_unit
    assert result.total_base_quantity == expected_total


def test_case_pack_sets_cases_and_units_per_case():
    result = parse_quantity("5/20 oz")
    assert result.cases == 5.0
    assert result.units_per_case == 20.0


def test_simple_quantity_sets_unit_size():
    result = parse_quantity("10 lb")
    assert result.unit_size == 10.0
    assert result.unit_size_unit == "lb"


def test_unparseable_returns_none():
    result = parse_quantity("???")
    assert result.total_base_quantity is None
    assert result.base_unit is None
