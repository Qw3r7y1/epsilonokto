"""Seed the vendors table with common supplier names.

Usage: python scripts/seed_vendors.py
"""
import asyncio
from app.db.session import async_session
from app.db.models import Vendor
from app.services.extraction.normalize import normalize_vendor_name

VENDORS = [
    {"name": "Sysco", "notes": "National food distributor"},
    {"name": "US Foods", "notes": "National food distributor"},
    {"name": "Gordon Food Service", "notes": "National food distributor"},
    {"name": "Performance Food Group", "notes": "National food distributor"},
    {"name": "Restaurant Depot", "notes": "Cash & carry wholesale"},
]


async def seed():
    async with async_session() as session:
        for v in VENDORS:
            vendor = Vendor(
                name=v["name"],
                normalized_name=normalize_vendor_name(v["name"]),
                notes=v.get("notes"),
            )
            session.add(vendor)
        await session.commit()
        print(f"Seeded {len(VENDORS)} vendors")


if __name__ == "__main__":
    asyncio.run(seed())
