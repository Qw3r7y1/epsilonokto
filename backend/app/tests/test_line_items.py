from app.services.extraction.line_items import extract_line_items


class TestLineItemExtraction:
    def test_case_pack_format(self):
        text = "Butter unsalted    5/20 oz    $3.45    $345.00"
        items = extract_line_items(text)
        assert len(items) == 1
        item = items[0]
        assert item["description"] == "Butter unsalted"
        assert item["cases"] == 5.0
        assert item["units_per_case"] == 20.0
        assert item["raw_quantity"] == 100.0
        assert item["raw_unit"] == "oz"

    def test_simple_weight(self):
        text = "Sugar    10 lb    $0.89    $8.90"
        items = extract_line_items(text)
        assert len(items) == 1
        assert items[0]["raw_quantity"] == 10.0
        assert items[0]["raw_unit"] == "lb"

    def test_multiple_items(self):
        text = """Butter unsalted    5/20 oz    $3.45    $345.00
Olive oil          2/12 gal   $18.99   $455.76
Sugar              10 lb      $0.89    $8.90"""
        items = extract_line_items(text)
        assert len(items) == 3
        assert items[0]["description"] == "Butter unsalted"
        assert items[1]["description"] == "Olive oil"
        assert items[2]["description"] == "Sugar"

    def test_skips_headers(self):
        text = """Description    Qty    Price    Total
Butter         5/20 oz    $3.45    $345.00
Subtotal: $345.00"""
        items = extract_line_items(text)
        assert len(items) == 1
        assert items[0]["description"] == "Butter"

    def test_empty_text(self):
        assert extract_line_items("") == []
        assert extract_line_items(None) == []

    def test_normalized_price_calculated(self):
        text = "Butter    5/20 oz    $3.45    $345.00"
        items = extract_line_items(text)
        item = items[0]
        # Should have a normalized unit price (per gram)
        assert item["normalized_unit"] == "g"
        assert item["normalized_unit_price"] is not None

    def test_volume_items(self):
        text = "Olive oil    2/12 gal    $18.99    $455.76"
        items = extract_line_items(text)
        assert len(items) == 1
        assert items[0]["raw_unit"] == "gal"
        assert items[0]["normalized_unit"] == "ml"

    def test_position_numbering(self):
        text = """Cheese    5 lb    $1.00    $5.00
Cream     10 oz   $2.00    $20.00"""
        items = extract_line_items(text)
        assert items[0]["position"] == 1
        assert items[1]["position"] == 2
