"""Spot-check the loaded diagnostic bank and approve it, inside the backend container:

    docker compose exec backend \\
        python -m scripts.tools.review_diagnostic
    ... python -m scripts.tools.review_diagnostic --approve 12,40
    ... python -m scripts.tools.review_diagnostic --approve-all-verified
    ... python -m scripts.tools.review_diagnostic --reject 7,19

With no flag it prints a ~20% sample of every (topic, language). The sample is seeded
(--seed), so the same command prints the same items. Every loaded row was verified by
execution; only rows marked reviewed are served to students. --reject deletes bad items
found in the spot check, but never a reviewed or already-answered row."""

import argparse
import json
import random
from collections import defaultdict

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.features.onboarding.models import DiagnosticItem, DiagnosticResponse
from scripts._local_db import require_local_db

SAMPLE = 0.2


def sample(rows: list[DiagnosticItem], seed: int = 0) -> list[DiagnosticItem]:
    groups: dict[tuple[str, str], list[DiagnosticItem]] = defaultdict(list)
    for row in sorted(rows, key=lambda r: r.external_id):
        groups[(row.topic, row.language)].append(row)
    picked = []
    for (topic, language), group in sorted(groups.items()):
        rng = random.Random(f"{seed}:{topic}:{language}")
        picked += rng.sample(group, max(1, round(len(group) * SAMPLE)))
    return picked


def show(row: DiagnosticItem) -> str:
    lines = [f"[{row.id}] {row.external_id}  {row.kind} {row.difficulty}"
             + ("  (reviewed)" if row.reviewed else "")]
    for part, fields in (("body", row.body), ("key", row.key)):
        for name, value in fields.items():
            if isinstance(value, str) and "\n" in value.strip():
                lines.append(f"  {part}.{name}:")
                lines += [f"    | {line}" for line in value.rstrip("\n").split("\n")]
            else:
                lines.append(f"  {part}.{name}: {json.dumps(value)}")
    return "\n".join(lines)


def approve(db: Session, ids: list[int] | None = None) -> int:
    query = db.query(DiagnosticItem).filter(DiagnosticItem.reviewed.is_(False))
    if ids is not None:
        query = query.filter(DiagnosticItem.id.in_(ids))
    count = query.update({DiagnosticItem.reviewed: True}, synchronize_session=False)
    db.commit()
    return count


def reject(db: Session, ids: list[int]) -> tuple[list[int], dict[int, str]]:
    """Delete unreviewed rows nobody has answered; reviewed or answered rows stay."""
    rows = {row.id: row for row in db.query(DiagnosticItem).filter(DiagnosticItem.id.in_(ids))}
    answered = {item_id for (item_id,) in db.query(DiagnosticResponse.item_id)
                .filter(DiagnosticResponse.item_id.in_(ids)).distinct()}
    deleted, refused = [], {}
    for item_id in ids:
        row = rows.get(item_id)
        if row is None:
            refused[item_id] = "not found"
        elif row.reviewed:
            refused[item_id] = "reviewed"
        elif item_id in answered:
            refused[item_id] = "answered"
        else:
            db.delete(row)
            deleted.append(item_id)
    db.commit()
    return deleted, refused


def _ids(text: str) -> list[int]:
    return [int(part) for part in text.split(",") if part.strip()]


def main() -> None:
    parser = argparse.ArgumentParser()
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--approve", help="comma-separated item ids, e.g. 12,40")
    action.add_argument("--approve-all-verified", action="store_true")
    action.add_argument("--reject", help="comma-separated ids of unreviewed items to delete")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    require_local_db()
    with SessionLocal() as db:
        if args.approve:
            print(f"approved {approve(db, _ids(args.approve))}")
        elif args.reject:
            deleted, refused = reject(db, _ids(args.reject))
            print(f"deleted {len(deleted)}: {deleted}")
            for item_id, why in refused.items():
                print(f"  refused {item_id}: {why}")
        elif args.approve_all_verified:
            print(f"approved {approve(db)}")
        else:
            rows = db.query(DiagnosticItem).all()
            picked = sample(rows, args.seed)
            for row in picked:
                print(show(row), end="\n\n")
            print(f"{len(picked)} of {len(rows)} items shown. Approve with --approve id,id "
                  f"or --approve-all-verified.")


if __name__ == "__main__":
    main()
