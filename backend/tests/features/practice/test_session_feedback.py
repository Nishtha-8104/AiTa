"""Short session feedback: stored once, facts kept when the LLM is down, code blocked."""

from datetime import datetime, timedelta, timezone

import pytest

from app.core.exceptions import LLMUnavailable
from app.features.accounts.models import User
from app.features.learner_model.models import LearningEvent
from app.features.practice.logic.practice_session.feedback import SessionNarrative, generate_session_feedback
from app.features.practice.models import PracticeSession

T0 = datetime(2026, 10, 24, 10, 0, tzinfo=timezone.utc)


class FakeRunnable:
    def __init__(self, result):
        self.result = result
        self.calls = 0

    def invoke(self, payload):
        self.calls += 1
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


@pytest.fixture
def practice(session):
    user = User(email="sf@example.com", username="sessfb")
    session.add(user)
    session.flush()
    s = PracticeSession(user_id=user.id, language="c", started_at=T0, last_activity_at=T0,
                        graded_count=2, served=[])
    session.add(s)
    session.flush()
    for minute, (kind, score) in enumerate([("mcq", 1.0), ("debug", 0.2)]):
        session.add(LearningEvent(user_id=user.id, kind=kind, item_id=minute + 1, topic="loops",
                                  score=score, weight=1.0, language="c",
                                  misconceptions=["off_by_one"], mastery_before=0.3,
                                  mastery_after=0.32, session_id=s.id,
                                  created_at=T0 + timedelta(minutes=minute)))
    session.flush()
    return s


GOOD = SessionNarrative(
    summary="You got the loops question right. The debug task on loops was harder.",
    work_on_next=["Loops: trace two more loops by hand where the count starts at 0."],
)


def test_feedback_stored_once(session, practice):
    fake = FakeRunnable(GOOD)

    generate_session_feedback(session, practice, runnable=fake)
    generate_session_feedback(session, practice, runnable=fake)

    assert fake.calls == 1
    assert practice.feedback_status == "ready"
    assert practice.feedback["work_on_next"] == GOOD.work_on_next


def test_feedback_unavailable_keeps_facts(session, practice):
    generate_session_feedback(session, practice,
                              runnable=FakeRunnable(LLMUnavailable("down")))

    assert practice.feedback_status == "unavailable"
    assert practice.feedback is None


def test_feedback_blocked(session, practice):
    leaky = SessionNarrative(summary="Nearly there.\n```c\nfor (i = 0; i < n; i++)\n```",
                             work_on_next=["Loops: check the start value."])

    generate_session_feedback(session, practice, runnable=FakeRunnable(leaky))

    assert practice.feedback_status == "blocked"
    assert practice.feedback is None
