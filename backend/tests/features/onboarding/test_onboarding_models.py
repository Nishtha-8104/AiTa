from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.features.accounts.models import User
from app.features.accounts.schemas import UserProfileResponse
from app.features.onboarding.models import DiagnosticItem, DiagnosticResponse, OnboardingRecord


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
    u = User(email="onb@example.com", username="onbuser")
    db.add(u)
    db.commit()
    return u


def test_onboarding_done_false_without_record(user):
    assert user.onboarding_done is False


def test_onboarding_done_true_after_finish(db, user):
    db.add(OnboardingRecord(user_id=user.id, finished_at=datetime.now(timezone.utc)))
    db.commit()
    db.refresh(user)
    assert user.onboarding_done is True


def test_response_unique_per_item(db, user):
    item = DiagnosticItem(
        external_id="loops-predict-c-1", kind="predict_output", topic="loops", tier=1,
        difficulty="easy", language="c", concept_key="loop_bounds",
        body={"code": "int main(){}"}, key={"output": ""},
    )
    db.add(item)
    db.flush()
    for order in (1, 2):
        db.add(DiagnosticResponse(
            user_id=user.id, item_id=item.id, order=order, phase="warmup",
            answer={"output": ""}, score=1.0, graded_by="key", ms_taken=1000,
        ))
    with pytest.raises(IntegrityError):
        db.flush()


def test_user_response_has_onboarding_done(db, user):
    db.refresh(user)
    assert UserProfileResponse.model_validate(user).model_dump()["onboarding_done"] is False
    db.add(OnboardingRecord(user_id=user.id, finished_at=datetime.now(timezone.utc)))
    db.commit()
    db.refresh(user)
    assert UserProfileResponse.model_validate(user).onboarding_done is True
