"""Text normalization utilities for vendor and product names."""

import re


def normalize_vendor_name(name: str) -> str:
    """Return a lowercased, whitespace-collapsed vendor name for fuzzy matching."""
    return re.sub(r"\s+", " ", name.strip()).lower()
