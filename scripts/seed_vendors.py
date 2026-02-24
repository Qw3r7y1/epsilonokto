#!/usr/bin/env python3
"""Seed initial vendor data."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.db.models import Vendor
from app.db.session import SessionLocal

VENDORS = [
    {"name": "Sysco", "alias": "sysco", "contact_email": "orders@sysco.com"},
    {"name": "US Foods", "alias": "usfoods"},
    {"name": "Performance Food Group", "alias": "pfg"},
    {"name": "Gordon Food Service", "alias": "gfs"},
]


def seed() -> None:
    db = SessionLocal()
    try:
        added = 0
        for v in VENDORS:
            exists = db.query(Vendor).filter(Vendor.name == v["name"]).first()
            if not exists:
                db.add(Vendor(**v))
                added += 1
        db.commit()
        print(f"Seeded {added} vendors ({len(VENDORS) - added} already existed).")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
