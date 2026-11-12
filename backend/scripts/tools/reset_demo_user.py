"""Wipe and recreate ONE account before a rehearsal, inside the backend container:

    docker compose exec backend python -m scripts.tools.reset_demo_user

Defaults to the local student, the account PET opens with. Only the named account is
touched."""

import argparse

from app.core.database import SessionLocal
from app.features.accounts.service import AuthService
from app.features.learner_model.logic.demo import reset_account


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--email", default=AuthService.LOCAL_EMAIL)
    parser.add_argument("--username", default=None)
    args = parser.parse_args()

    username = args.username or args.email.split("@")[0].replace(".", "_")
    with SessionLocal() as db:
        user = reset_account(db, args.email, username)
    print(f"reset {user.email} (id {user.id})")


if __name__ == "__main__":
    main()
