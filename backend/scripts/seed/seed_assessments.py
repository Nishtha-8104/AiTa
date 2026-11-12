"""Seed the verified assessment bank, inside the backend container:

    docker compose exec backend python -m scripts.seed.seed_assessments

Re-verifies every item by execution first; rerunning is safe (upsert by external_id)."""

import json

from app.core import content
from app.core.database import SessionLocal
from app.features.practice.logic.assessment.seeding import seed


def main() -> None:
    bank = json.loads((content.root() / "legacy" / "assessments.json").read_text("utf-8"))
    with SessionLocal() as db:
        report = seed(db, bank)
    for key, count in sorted(report.items()):
        print(f"  {count:3d}  {key}")


if __name__ == "__main__":
    main()
