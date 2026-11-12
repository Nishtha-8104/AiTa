"""Seed the hand-written theory bank in C, C++ and Python, inside the backend container:

    docker compose exec backend python -m scripts.seed.seed_theory

Reads content/topics/<topic>/theory.json. --check only validates; --topic limits the run
to one topic. Rerunning is safe (upsert by external_id)."""

import argparse
from collections import Counter

from app.core.database import SessionLocal
from app.core.topics import TOPICS
from app.features.practice.logic.assessment.content import load_theory
from app.features.practice.logic.assessment.seeding import seed_theory, theory_problem
from scripts._local_db import require_local_db


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="validate only, write nothing")
    parser.add_argument("--topic", choices=TOPICS)
    args = parser.parse_args()

    items = load_theory([args.topic] if args.topic else TOPICS)
    counts: Counter = Counter()
    for item in items:
        problem = theory_problem(item)
        counts[(item["topic"], item["language"], item["difficulty"], problem is None)] += 1
        if problem:
            print(f"  REJECT {item['external_id']}: {problem}")
    for (topic, language, difficulty, ok), count in sorted(counts.items()):
        print(f"  {count:3d}  {topic:20s} {language:7s} {difficulty:7s} {'ok' if ok else 'REJECTED'}")
    if args.check:
        return
    require_local_db()
    with SessionLocal() as db:
        for key, count in sorted(seed_theory(db, items).items()):
            print(f"  {count:3d}  {key}")


if __name__ == "__main__":
    main()
