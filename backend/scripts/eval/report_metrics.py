"""The demo's three numbers, inside the backend container:

    docker compose exec backend python -m scripts.eval.report_metrics

Hint leak rate and verified-vs-estimated correctness are system-wide; the mastery
trace is for the named account, the local student by default."""

import argparse
import json

from app.core.database import SessionLocal
from app.features.accounts.models import User
from app.features.accounts.service import AuthService
from app.features.learner_model.logic.demo import report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", default=AuthService.LOCAL_EMAIL)
    args = parser.parse_args()
    with SessionLocal() as db:
        user = db.query(User).filter(User.email == args.email).first()
        print(json.dumps(report(db, user.id if user else None), indent=2))


if __name__ == "__main__":
    main()
