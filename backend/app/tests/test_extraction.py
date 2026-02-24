from app.services.extraction.invoice_parser import parse_invoice_fields
from app.services.extraction.normalize import normalize_vendor_name, clean_amount


class TestInvoiceParser:
    def test_extracts_invoice_number(self):
        text = "Invoice #: INV-2024-0042\nDate: 01/15/2025\nTotal: $1,234.56"
        result = parse_invoice_fields(text)
        assert result["invoice_number"] == "INV-2024-0042"

    def test_extracts_total(self):
        text = "Subtotal: $1,000.00\nTax: $80.00\nTotal Due: $1,080.00"
        result = parse_invoice_fields(text)
        assert result["total"] == 1080.00

    def test_extracts_date(self):
        text = "Invoice Date: 01/15/2025\nDue Date: 02/15/2025"
        result = parse_invoice_fields(text)
        assert result["invoice_date"].isoformat() == "2025-01-15"
        assert result["due_date"].isoformat() == "2025-02-15"

    def test_empty_text_returns_zero_confidence(self):
        result = parse_invoice_fields("")
        assert result["confidence"] == 0

    def test_confidence_score(self):
        text = "Invoice #: 123\nDate: 01/15/2025\nTotal: $500"
        result = parse_invoice_fields(text)
        assert result["confidence"] > 0


class TestNormalize:
    def test_vendor_name_strips_suffixes(self):
        assert normalize_vendor_name("Sysco Corp.") == "sysco"
        assert normalize_vendor_name("US Foods, LLC") == "us foods"

    def test_vendor_name_lowercases(self):
        assert normalize_vendor_name("ACME SUPPLY") == "acme supply"

    def test_clean_amount(self):
        assert clean_amount("$1,234.56") == 1234.56
        assert clean_amount("1234") == 1234.0
        assert clean_amount("") is None

    def test_clean_amount_european(self):
        assert clean_amount("1.234,56") == 1234.56
