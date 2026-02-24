"""Vendor detection from invoice raw text.

Scans the top of an invoice document to extract a probable vendor name,
then fuzzy-matches it against existing Vendor records using Jaccard similarity
on normalized tokens.
"""

import re
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import Vendor
from app.services.extraction.normalize import normalize_vendor_name

log = get_logger("ingestion.vendor_detect")

# Look for explicit labels like "From:", "Vendor:", "Sold by:"
_LABEL_PATTERNS = [
    re.compile(
        r"^(?:from|sold\s*by|vendor|supplier|billed?\s*by)\s*[:\-]?\s*(.+)$",
        re.IGNORECASE | re.MULTILINE,
    ),
]

# Number of lines at the top of the document to scan for the company name
_SCAN_LINES = 15

# Minimum / maximum plausible lengths for a vendor name
_MIN_LEN = 3
_MAX_LEN = 120


def _extract_candidate(text: str) -> Optional[str]:
    """Return the most likely vendor name string from the raw text, or None."""
    # 1. Try explicit "From: Acme Inc" style labels
    for pattern in _LABEL_PATTERNS:
        m = pattern.search(text)
        if m:
            candidate = m.group(1).strip()
            if _MIN_LEN < len(candidate) <= _MAX_LEN:
                return candidate

    # 2. Fallback: the first non-trivial line of the document is often
    #    the supplier's company name.
    header_lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    for line in header_lines[:_SCAN_LINES]:
        # Skip lines that look like invoice metadata
        if re.search(
            r"\b(?:invoice|date|no\.?|page|bill\s*to|ship\s*to|p\.?o\.?\s*box)\b",
            line,
            re.IGNORECASE,
        ):
            continue
        # Skip lines that are all numbers or very short
        if re.match(r"^[\d\s\-/]+$", line):
            continue
        if _MIN_LEN < len(line) <= _MAX_LEN:
            return line

    return None


def _jaccard(a: str, b: str) -> float:
    sa, sb = set(a.split()), set(b.split())
    union = len(sa | sb)
    return len(sa & sb) / union if union else 0.0


async def detect_vendor(
    raw_text: str,
    db: AsyncSession,
    similarity_threshold: float = 0.6,
) -> Optional[Vendor]:
    """Identify which Vendor issued this invoice.

    Returns the best-matching Vendor, or None when confidence is too low.

    Args:
        raw_text:             Full extracted text of the invoice.
        db:                   Read-capable AsyncSession.
        similarity_threshold: Minimum Jaccard score to accept a match.
    """
    candidate = _extract_candidate(raw_text)
    if not candidate:
        log.debug("vendor_detect: no candidate name extracted")
        return None

    normalized_candidate = normalize_vendor_name(candidate)
    if not normalized_candidate:
        return None

    result = await db.execute(select(Vendor))
    vendors: list[Vendor] = result.scalars().all()

    best: Optional[Vendor] = None
    best_score = 0.0

    for vendor in vendors:
        score = _jaccard(normalized_candidate, vendor.normalized_name)
        if score > best_score:
            best_score = score
            best = vendor

    if best is not None and best_score >= similarity_threshold:
        log.info(
            "vendor_detect: matched '%s' → '%s' (score=%.2f)",
            candidate, best.name, best_score,
        )
        return best

    log.debug(
        "vendor_detect: no match (candidate='%s', best_score=%.2f)",
        candidate, best_score,
    )
    return None
