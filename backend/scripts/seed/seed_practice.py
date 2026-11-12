"""Seed the hand-written practice bank in C, C++ and Python, inside the backend container:

    docker compose exec backend python -m scripts.seed.seed_practice

Reads problems.json, mcq.json and debug.json in content/topics/<topic>/. Every code item is
proven by execution first, and each rejection is printed with its reason. --check only
verifies; --topic limits the run to one file. Rerunning is safe (upsert by external_id).
Debug challenges need their problem seeded first (scripts.seed.ingest_problems)."""

import argparse
from collections import Counter

from app.core.database import SessionLocal
from app.core.topics import TOPICS
from app.features.grading.agent.multi_test import display_statement, merge_cases
from app.features.grading.logic.execution.run_code import run_code
from app.features.grading.models import Language
from app.features.practice.logic.assessment.content import load_practice
from app.features.practice.logic.assessment.seeding import seed
from app.features.practice.logic.assessment.verify import Check, verify_debug, verify_mcq
from app.features.problems.logic.test_generation.curated_tests import CuratedCase, curated_tests
from app.features.problems.models import Difficulty, Problem, ProblemSource
from app.features.problems.service import fill_title, get_or_create_problem, has_test_cases
from scripts._local_db import require_local_db


def _load_problem(db, row: dict, check_only: bool) -> str:
    if check_only:
        cases = [CuratedCase(**case) for case in row["tests"]]
        report = run_code(Language.PYTHON, row["reference"],
                          [(merge_cases([case])[0], case.expected_stdout) for case in cases])
        return f"reference passes {report.passed}/{report.total} tests"
    problem, _ = get_or_create_problem(
        db, row["statement"], source=ProblemSource.DSA, topic=row["topic"],
        difficulty=Difficulty(row["difficulty"]), constraints=row["constraints"],
        external_id=row["external_id"], title=row["title"])
    titled = ", title filled in" if fill_title(db, row["external_id"], row["title"]) else ""
    if has_test_cases(db, problem.id):
        return "already has tests" + titled
    suite = curated_tests(db, problem, row["reference"], row["tests"])
    return (suite.unverified_reason or f"{suite.agreed} tests ({suite.dropped} dropped)") + titled


def _with_problem(db, item: dict, authored: dict[str, dict]) -> tuple[dict, list]:
    """The seeded problem, or under --check the one authored in the same file."""
    problem = db.query(Problem).filter(Problem.external_id == item["problem_external_id"]).first()
    if problem is None:
        row = authored.get(item["problem_external_id"])
        if row is None:
            return item, []
        return {**item, "topic": row["topic"], "difficulty": row["difficulty"],
                "statement": display_statement(row["statement"])}, \
            [CuratedCase(**case) for case in row["tests"]]
    return {**item, "topic": problem.topic,
            "difficulty": getattr(problem.difficulty, "value", problem.difficulty) or "easy",
            "statement": display_statement(problem.statement)}, problem.test_cases


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verify only, write nothing")
    parser.add_argument("--topic", choices=TOPICS)
    args = parser.parse_args()
    require_local_db()

    kept: dict[str, list] = {"mcqs": [], "debug": []}
    counts: Counter = Counter()
    with SessionLocal() as db:
        for topic in [args.topic] if args.topic else TOPICS:
            bank = load_practice(topic)
            authored = {row["external_id"]: row for row in bank["problems"]}
            for row in bank["problems"]:
                print(f"  problem {row['external_id']}: {_load_problem(db, row, args.check)}")
            for item in bank["mcqs"]:
                check = verify_mcq(item, None)
                counts[(topic, "mcq " + item["language"], check.ok)] += 1
                if check.ok:
                    kept["mcqs"].append(item)
                else:
                    print(f"  REJECT {item['external_id']}: {check.reason}")
            for item in bank["debug"]:
                item, cases = _with_problem(db, item, authored)
                check = (verify_debug(item, cases, None) if cases
                         else Check(False, "problem not seeded"))
                counts[(topic, "debug " + item["language"], check.ok)] += 1
                if check.ok:
                    kept["debug"].append(item)
                else:
                    print(f"  REJECT {item['external_id']}: {check.reason}")
        for (topic, kind, ok), count in sorted(counts.items()):
            print(f"  {count:3d}  {topic:20s} {kind:12s} {'ok' if ok else 'REJECTED'}")
        if not args.check:
            for key, count in sorted(seed(db, kept).items()):
                print(f"  {count:3d}  {key}")


if __name__ == "__main__":
    main()
