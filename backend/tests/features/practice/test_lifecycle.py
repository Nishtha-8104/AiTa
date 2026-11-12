"""Practice session lifecycle: open on serve, real once graded, idle and language closes,
carry-over of unsolved coding/debug items."""

from datetime import datetime, timedelta, timezone

import pytest

from app.features.accounts.models import User
from app.features.learner_model.models import LearningEvent
from app.features.practice import service as lifecycle
from app.features.practice.models import PracticeSession

T0 = datetime(2026, 10, 24, 10, 0, tzinfo=timezone.utc)


def at(minutes: int) -> datetime:
    return T0 + timedelta(minutes=minutes)


@pytest.fixture
def user(session):
    u = User(email="p@example.com", username="practiser")
    session.add(u)
    session.flush()
    return u


def code_event(session, user, item_id, score, kind="code"):
    ev = LearningEvent(user_id=user.id, kind=kind, item_id=item_id, score=score, weight=1.0,
                       language="c")
    session.add(ev)
    session.flush()
    return ev


def test_serve_opens_but_not_real_until_graded(session, user):
    s = lifecycle.record_served(session, user.id, "mcq", 1, "c", T0)
    assert s.id is not None
    assert s.graded_count == 0
    assert lifecycle.pending_wrap_up(session, user.id) is None


def test_idle_close_stamps_last_activity(session, user):
    lifecycle.record_served(session, user.id, "coding", 7, "c", T0)
    lifecycle.attach_event(session, code_event(session, user, 7, 0.5), "coding", at(5))
    closed = lifecycle.close_if_idle(session, user.id, at(40))
    assert closed.end_reason == "idle"
    assert closed.ended_at == at(5)


def test_idle_close_discards_empty_session(session, user):
    lifecycle.record_served(session, user.id, "coding", 7, "c", T0)
    assert lifecycle.close_if_idle(session, user.id, at(31)) is None
    assert session.query(PracticeSession).count() == 0


def test_unserved_problem_not_attached(session, user):
    s = lifecycle.record_served(session, user.id, "coding", 7, "c", T0)
    ev = code_event(session, user, 9, 1.0)
    lifecycle.attach_event(session, ev, "coding", at(1))
    assert ev.session_id is None
    assert s.graded_count == 0


def test_carry_over_joins_new_session(session, user):
    old = lifecycle.record_served(session, user.id, "coding", 7, "c", T0)
    lifecycle.attach_event(session, code_event(session, user, 7, 0.5), "coding", T0)
    lifecycle.close_if_idle(session, user.id, at(40))

    ev = code_event(session, user, 7, 1.0)
    new = lifecycle.attach_event(session, ev, "coding", at(50))
    assert new.id != old.id
    assert ev.session_id == new.id
    assert old.ended_at == T0


def test_carry_over_is_one_hop(session, user):
    lifecycle.record_served(session, user.id, "coding", 7, "c", T0)
    lifecycle.attach_event(session, code_event(session, user, 7, 0.5), "coding", T0)
    lifecycle.close_if_idle(session, user.id, at(40))

    second = lifecycle.record_served(session, user.id, "mcq", 1, "c", at(50))
    assert any(e["type"] == "coding" and e["id"] == 7 for e in second.served)
    lifecycle.attach_event(session, code_event(session, user, 1, 1.0, "mcq"), "mcq", at(51))
    lifecycle.close_if_idle(session, user.id, at(90))

    third = lifecycle.record_served(session, user.id, "mcq", 2, "c", at(100))
    assert [(e["type"], e["id"]) for e in third.served] == [("mcq", 2)]


def test_run_keeps_session_alive(session, user):
    s = lifecycle.record_served(session, user.id, "coding", 7, "c", T0)
    assert lifecycle.touch(session, user.id, "coding", 7, at(25))
    session.expire(s)
    assert lifecycle.close_if_idle(session, user.id, at(50)) is None
    assert s.ended_at is None


def test_language_switch_closes(session, user):
    s = lifecycle.record_served(session, user.id, "coding", 7, "c", T0)
    lifecycle.attach_event(session, code_event(session, user, 7, 1.0), "coding", at(2))
    lifecycle.close_for_language_switch(session, user.id, at(3))
    assert s.end_reason == "language_switch"
    assert lifecycle.pending_wrap_up(session, user.id) is s


def test_serving_another_language_closes_the_open_session(session, user):
    old = lifecycle.record_served(session, user.id, "coding", 7, "c", T0)
    lifecycle.attach_event(session, code_event(session, user, 7, 0.5), "coding", at(2))
    new = lifecycle.record_served(session, user.id, "coding", 8, "python", at(3))
    assert old.end_reason == "language_switch"
    assert new.id != old.id and new.language == "python" and new.ended_at is None
    assert [(e["type"], e["id"]) for e in new.served] == [("coding", 8)]


def test_finished_session_hides_older_idle_wrap_up(session, user):
    lifecycle.record_served(session, user.id, "coding", 7, "c", T0)
    lifecycle.attach_event(session, code_event(session, user, 7, 1.0), "coding", T0)
    lifecycle.close_if_idle(session, user.id, at(40))

    b = lifecycle.record_served(session, user.id, "mcq", 1, "c", at(50))
    lifecycle.attach_event(session, code_event(session, user, 1, 1.0, "mcq"), "mcq", at(51))
    lifecycle.finish(session, user.id, b.id, at(52))
    assert lifecycle.pending_wrap_up(session, user.id) is None
