import re
import unicodedata


def normalize_vendor_name(name: str) -> str:
    """Normalize vendor name for fuzzy matching.

    - Lowercase
    - Strip common suffixes (LLC, Inc, Ltd, Co, Corp)
    - Remove punctuation
    - Collapse whitespace
    """
    name = name.strip().lower()

    # Remove accents
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()

    # Strip common business suffixes
    suffixes = r"\b(llc|inc|ltd|co|corp|corporation|limited|company|group|sa|sarl)\b\.?"
    name = re.sub(suffixes, "", name)

    # Remove non-alphanumeric (keep spaces)
    name = re.sub(r"[^a-z0-9\s]", "", name)

    # Collapse whitespace
    name = re.sub(r"\s+", " ", name).strip()

    return name


def normalize_currency(raw: str) -> str:
    """Normalize currency string to 3-letter code."""
    mapping = {
        "$": "USD", "usd": "USD", "us$": "USD",
        "€": "EUR", "eur": "EUR",
        "£": "GBP", "gbp": "GBP",
        "cad": "CAD", "ca$": "CAD",
    }
    return mapping.get(raw.strip().lower(), "USD")


def clean_amount(raw: str) -> float | None:
    """Parse a currency string like '$1,234.56' into a float."""
    if not raw:
        return None
    cleaned = re.sub(r"[^\d.,\-]", "", raw)
    # Handle European format (1.234,56)
    if "," in cleaned and "." in cleaned:
        if cleaned.rindex(",") > cleaned.rindex("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        # Could be thousands sep or decimal — heuristic
        parts = cleaned.split(",")
        if len(parts[-1]) == 2:
            cleaned = cleaned.replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    try:
        return round(float(cleaned), 2)
    except ValueError:
        return None
