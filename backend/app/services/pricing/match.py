"""Product matching service.

Matches a line item description to an existing Product in the catalog using
token-overlap (Jaccard) similarity.  When no match exceeds the threshold,
a new Product is auto-created with compare_mode='none' for later human review.

No external fuzzy-matching library is required.
"""

import re
import unicodedata
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import Product

log = get_logger("pricing.match")

# Words to ignore when building the comparison token set
_STOP_WORDS: frozenset[str] = frozenset(
    {
        "fresh", "frozen", "organic", "premium", "grade", "natural", "raw",
        "whole", "sliced", "diced", "chopped", "peeled", "boneless", "skinless",
        "the", "a", "an", "and", "or", "of", "in", "with", "without",
    }
)


def normalize_description(description: str) -> str:
    """Normalize a free-text description for matching.

    Steps:
      1. Lowercase + strip
      2. Remove accents (NFKD)
      3. Remove non-alphanumeric characters (keep spaces)
      4. Drop stop words
      5. Collapse whitespace
    """
    s = description.strip().lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    tokens = [t for t in s.split() if t and t not in _STOP_WORDS]
    return " ".join(tokens)


def _jaccard(a: str, b: str) -> float:
    """Token-level Jaccard similarity between two normalized strings."""
    if not a or not b:
        return 0.0
    sa = set(a.split())
    sb = set(b.split())
    union = len(sa | sb)
    return len(sa & sb) / union if union else 0.0


async def find_or_create_product(
    description: str,
    db: AsyncSession,
    similarity_threshold: float = 0.5,
    auto_create: bool = True,
) -> Optional[Product]:
    """Return the best-matching Product for a line item description.

    Algorithm:
      1. Normalize the description.
      2. Load all Products from the DB (acceptable for catalogs < ~10k rows).
      3. Score each Product using Jaccard similarity on normalized names.
      4. If the best score >= similarity_threshold, return that Product.
      5. Otherwise, if auto_create=True, create a new Product with
         compare_mode='none' so a human can later set the correct mode
         and merge duplicates.

    Args:
        description:          Raw line item description string.
        db:                   SQLAlchemy AsyncSession (must be write-capable).
        similarity_threshold: Minimum Jaccard score to accept as a match.
        auto_create:          Create a new Product when no match is found.

    Returns:
        A Product ORM instance, or None if no match and auto_create=False.
    """
    normalized_desc = normalize_description(description)
    if not normalized_desc:
        return None

    result = await db.execute(select(Product))
    products: list[Product] = result.scalars().all()

    best: Optional[Product] = None
    best_score = 0.0

    for product in products:
        score = _jaccard(normalized_desc, product.normalized_name)
        if score > best_score:
            best_score = score
            best = product

    if best is not None and best_score >= similarity_threshold:
        log.debug(
            "Matched '%s' → '%s' (score=%.2f)", description, best.name, best_score
        )
        return best

    if not auto_create:
        log.debug(
            "No match for '%s' (best score=%.2f, threshold=%.2f); skipping auto-create",
            description, best_score, similarity_threshold,
        )
        return None

    # Auto-create a placeholder product for human review
    new_product = Product(
        name=description[:255],
        normalized_name=normalized_desc[:255],
        compare_mode="none",
    )
    db.add(new_product)
    await db.flush()
    log.info(
        "Auto-created product '%s' (normalized='%s') from line item description",
        new_product.name, new_product.normalized_name,
    )
    return new_product
