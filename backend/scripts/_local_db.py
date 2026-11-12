from sqlalchemy.engine import make_url

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "db"}
LOCAL_DB_HINT = ("Point it at the local stack, e.g. "
                 "DATABASE_URL=postgresql://pet:pet@localhost:5433/pet_db")


def require_local_db(url=None, hint: str = LOCAL_DB_HINT) -> None:
    """For scripts that write: never against a cloud database. Exits without echoing
    the URL, which may carry a password."""
    if url is None:
        from app.core.database import engine

        url = engine.url
    host = make_url(url).host
    if (host or "").lower() not in LOCAL_HOSTS:
        raise SystemExit(f"Refusing to run: DATABASE_URL is not a local database. {hint}")
