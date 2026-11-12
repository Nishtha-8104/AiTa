import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.dependencies import get_current_active_user
from app.features.accounts.models import User


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        yield session


@pytest.fixture
def user(db):
    u = User(email="lang@example.com", username="languser")
    db.add(u)
    db.commit()
    return u


@pytest.fixture
def client(db, user):
    from app.main import app

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_active_user] = lambda: user
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_new_user_defaults_to_c(client):
    assert client.get("/api/v1/auth/me").json()["preferred_language"] == "c"


def test_update_to_cpp_persists(client, db, user):
    response = client.patch("/api/v1/users/profile", json={"preferred_language": "cpp"})
    assert response.status_code == 200
    assert response.json()["preferred_language"] == "cpp"
    db.expire_all()
    assert db.get(User, user.id).preferred_language == "cpp"
    assert client.get("/api/v1/auth/me").json()["preferred_language"] == "cpp"


def test_unsupported_language_is_rejected(client):
    for value in ("java", None):
        response = client.patch("/api/v1/users/profile", json={"preferred_language": value})
        assert response.status_code == 422
