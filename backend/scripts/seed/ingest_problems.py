import argparse
import json
import time

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core import content
from app.core.exceptions import LLMUnavailable
from app.features.problems.logic.test_generation.curated_tests import curated_tests
from app.features.problems.logic.test_generation.generate_tests import generate_tests
from app.features.problems.models import Difficulty, ProblemSource
from app.features.problems.service import fill_title, get_or_create_problem, has_test_cases

DATA = content.root() / "imported" / "problems.json"


class IngestReport(BaseModel):
    seen: int = 0
    created: int = 0
    titled: int = 0
    skipped: int = 0
    generated: int = 0
    curated: int = 0
    unverified: list[str] = []
    stopped_early: bool = False


def ingest(db: Session, rows: list[dict], *, generator=None, provider=None,
           limit: int | None = None, pause: float = 1.0) -> IngestReport:
    report = IngestReport()

    for row in rows:
        if limit is not None and report.seen >= limit:
            break
        report.seen += 1

        problem, created = get_or_create_problem(
            db, row["statement"],
            source=ProblemSource(row["source"]),
            topic=row.get("topic"),
            difficulty=Difficulty(row["difficulty"]) if row.get("difficulty") else None,
            constraints=row.get("constraints"),
            external_id=row.get("external_id"),
            title=row.get("title"),
        )
        if created:
            report.created += 1
        elif row.get("title") and fill_title(db, row["external_id"], row["title"]):
            report.titled += 1

        if has_test_cases(db, problem.id):
            report.skipped += 1
            continue

        # Problems that ship their own reference and cases never touch the LLM,
        # so the bank can be rebuilt from scratch with the daily quota exhausted.
        shipped = row.get("tests")
        if shipped and row.get("reference"):
            suite = curated_tests(db, problem, row["reference"], shipped,
                                  provider=provider)
            if suite.unverified_reason:
                report.unverified.append(row["external_id"])
                print(f"  {row['external_id']}: UNVERIFIED ({suite.unverified_reason})")
            else:
                report.curated += 1
                print(f"  {row['external_id']}: {suite.agreed} curated cases "
                      f"({suite.dropped} dropped)")
            continue

        try:
            suite = generate_tests(db, problem, generator=generator, provider=provider)
        except LLMUnavailable as exc:
            print(f"  {row['external_id']}: LLM unavailable, stopping early ({exc.detail})")
            report.stopped_early = True
            break

        if suite.unverified_reason:
            report.unverified.append(row["external_id"])
            print(f"  {row['external_id']}: UNVERIFIED ({suite.unverified_reason})")
        else:
            report.generated += 1
            print(f"  {row['external_id']}: {suite.agreed} cases "
                  f"({suite.dropped} dropped, attempt {suite.attempts})")

        if pause:
            time.sleep(pause)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the PET problem bank.")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--only", choices=["dsa", "mbpp"], default=None)
    args = parser.parse_args()

    from app.core.database import SessionLocal

    rows = json.loads(DATA.read_text(encoding="utf-8"))
    if args.only:
        rows = [r for r in rows if r["source"] == args.only]

    db = SessionLocal()
    try:
        report = ingest(db, rows, limit=args.limit)
    finally:
        db.close()

    print(f"\nseen={report.seen} created={report.created} titled={report.titled} "
          f"skipped={report.skipped} "
          f"curated={report.curated} generated={report.generated} "
          f"unverified={len(report.unverified)}")
    if report.unverified:
        print("unverified:", ", ".join(report.unverified))
    if report.stopped_early:
        print("stopped early on a rate limit — rerun to continue where it left off")


if __name__ == "__main__":
    main()
