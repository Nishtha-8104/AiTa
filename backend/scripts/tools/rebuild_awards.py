"""Rebuild the gamification ledger from learning_events, inside the backend container:

    docker compose exec backend python -m scripts.tools.rebuild_awards --all
    docker compose exec backend python -m scripts.tools.rebuild_awards --user-id 7

Deterministic: running it twice gives the same ledger."""

import argparse

from app.core.database import SessionLocal
from app.features.accounts.models import User
from app.features.gamification.service import rebuild


def main() -> None:
    parser = argparse.ArgumentParser()
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--user-id", type=int)
    target.add_argument("--all", action="store_true")
    args = parser.parse_args()

    with SessionLocal() as db:
        ids = ([args.user_id] if args.user_id is not None
               else [uid for (uid,) in db.query(User.id).order_by(User.id)])
        for user_id in ids:
            print(f"{user_id}: {rebuild(db, user_id)} awards")


if __name__ == "__main__":
    main()
