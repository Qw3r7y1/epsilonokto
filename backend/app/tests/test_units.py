from decimal import Decimal

from app.services.units import (
    parse_quantity,
    normalize_price,
    convert_to_display_unit,
)


class TestCasePackParsing:
    """Test the 5/20 case-pack format."""

    def test_basic_case_pack(self):
        result = parse_quantity("5/20")
        assert result.cases == Decimal("5")
        assert result.units_per_case == Decimal("20")
        assert result.total_quantity == Decimal("100")

    def test_case_pack_with_unit(self):
        result = parse_quantity("5/20 oz")
        assert result.cases == Decimal("5")
        assert result.units_per_case == Decimal("20")
        assert result.total_quantity == Decimal("100")
        assert result.raw_unit == "oz"
        assert result.unit_family == "weight"
        # 100 oz * 28.3495 g/oz = 2834.95 g
        assert result.normalized_quantity == Decimal("2834.9500")
        assert result.normalized_unit == "g"

    def test_case_pack_x_notation(self):
        result = parse_quantity("3x24 gal")
        assert result.cases == Decimal("3")
        assert result.units_per_case == Decimal("24")
        assert result.total_quantity == Decimal("72")
        assert result.raw_unit == "gal"

    def test_case_pack_no_unit(self):
        """Without a unit, we get total but no normalization."""
        result = parse_quantity("5/20")
        assert result.total_quantity == Decimal("100")
        assert result.raw_unit is None
        assert result.normalized_quantity is None

    def test_single_slash_in_fraction(self):
        """2/12 should be 2 cases of 12."""
        result = parse_quantity("2/12 lb")
        assert result.cases == Decimal("2")
        assert result.units_per_case == Decimal("12")
        assert result.total_quantity == Decimal("24")
        assert result.raw_unit == "lb"


class TestSimpleQuantityParsing:
    def test_simple_weight(self):
        result = parse_quantity("10 lb")
        assert result.cases is None
        assert result.total_quantity == Decimal("10")
        assert result.raw_unit == "lb"
        assert result.unit_family == "weight"
        # 10 lb * 453.592 = 4535.92 g
        assert result.normalized_quantity == Decimal("4535.9200")
        assert result.normalized_unit == "g"

    def test_simple_volume(self):
        result = parse_quantity("5 gal")
        assert result.total_quantity == Decimal("5")
        assert result.raw_unit == "gal"
        assert result.unit_family == "volume"
        # 5 gal * 3785.41 = 18927.05 ml
        assert result.normalized_unit == "ml"

    def test_simple_count(self):
        result = parse_quantity("3 cases")
        assert result.total_quantity == Decimal("3")
        assert result.raw_unit == "cases"
        assert result.unit_family == "count"
        assert result.normalized_unit == "ea"

    def test_just_number(self):
        result = parse_quantity("42")
        assert result.total_quantity == Decimal("42")
        assert result.raw_unit is None

    def test_empty(self):
        result = parse_quantity("")
        assert result.total_quantity is None

    def test_grams(self):
        result = parse_quantity("500 g")
        assert result.total_quantity == Decimal("500")
        assert result.normalized_quantity == Decimal("500.0000")
        assert result.normalized_unit == "g"

    def test_dozen(self):
        result = parse_quantity("2 dozen")
        assert result.total_quantity == Decimal("2")
        assert result.normalized_quantity == Decimal("24")
        assert result.normalized_unit == "ea"


class TestNormalizePrice:
    def test_price_per_gram(self):
        qty = parse_quantity("10 lb")
        # $45 for 10 lb = $45 / 4535.92g
        price = normalize_price(Decimal("45.00"), qty)
        assert price is not None
        assert float(price) < 0.01  # less than a cent per gram

    def test_price_per_unit(self):
        qty = parse_quantity("5/20")
        qty.normalized_quantity = Decimal("100")
        qty.normalized_unit = "ea"
        price = normalize_price(Decimal("50.00"), qty)
        assert price == Decimal("0.500000")

    def test_case_pack_price(self):
        qty = parse_quantity("5/20 oz")
        # $100 for 5 cases of 20 oz = $100 / 2834.95g
        price = normalize_price(Decimal("100.00"), qty)
        assert price is not None


class TestDisplayConversion:
    def test_grams_to_kg(self):
        qty, unit = convert_to_display_unit(Decimal("5000"), "weight", "kg")
        assert unit == "kg"
        assert qty == Decimal("5.000")

    def test_grams_to_lb(self):
        qty, unit = convert_to_display_unit(Decimal("453.592"), "weight", "lb")
        assert unit == "lb"
        assert qty == Decimal("1.000")

    def test_ml_to_liters(self):
        qty, unit = convert_to_display_unit(Decimal("3000"), "volume", "L")
        assert unit == "L"
        assert qty == Decimal("3.000")

    def test_count_stays_ea(self):
        qty, unit = convert_to_display_unit(Decimal("24"), "count")
        assert unit == "ea"
        assert qty == Decimal("24")

    def test_auto_pick_unit(self):
        # 5000g should auto-pick kg
        qty, unit = convert_to_display_unit(Decimal("5000"), "weight")
        assert unit == "kg"
        assert qty == Decimal("5.000")
