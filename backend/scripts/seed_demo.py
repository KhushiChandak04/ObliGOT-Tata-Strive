"""Load the fictional demo records into Firestore once.

Usage (from backend/):  python scripts/seed_demo.py
- Writes only records whose ID does not exist yet, so re-running never overwrites edited or real data.
- Every record is fictional and labelled source_label="demo".
- Dates are computed relative to the IST business date at the moment of seeding; they do not move afterwards.
- Refuses to run unless Firestore is configured (the in-memory fallback already has these records).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import demo_data  # noqa: E402
from app.repository import firestore_enabled, get_record, put_record  # noqa: E402

DEMO = {
    "partners": demo_data.PARTNERS, "actions": demo_data.ACTIONS, "agreements": demo_data.AGREEMENTS,
    "projects": demo_data.PROJECTS, "finance": demo_data.FINANCE, "reports": demo_data.REPORTS,
    "opportunities": demo_data.OPPORTUNITIES, "milestones": demo_data.MILESTONES,
}


def main() -> int:
    if not firestore_enabled():
        print("Firestore is not configured; nothing to seed. Set FIREBASE_PROJECT_ID and FIREBASE_CREDENTIALS_FILE.")
        return 1
    for collection, records in DEMO.items():
        added = skipped = 0
        for record_id, record in records.items():
            record = record.model_dump(mode="json") if hasattr(record, "model_dump") else dict(record)
            if record.get("source_label") != "demo":
                raise SystemExit(f"Refusing to seed unlabelled record {collection}/{record_id}")
            if get_record(collection, record_id):
                skipped += 1
                continue
            put_record(collection, record, record_id)
            added += 1
        print(f"{collection}: {added} added, {skipped} already present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
