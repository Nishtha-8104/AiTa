"""Session facts: counts by type, topic levels, hints, mistakes and live-only awards."""

from datetime import datetime, timedelta, timezone

import pytest

from app.features.accounts.models import User
from app.features.gamification.models import GamificationAward
from app.features.hints.models import HintEvent
from app.features.learner_model.models import LearningEvent
from app.features.practice.logic.practice_session.facts import TypeCount, session_facts
from app.features.practice.models import PracticeSession
from app.features.problems.models import Problem, ProblemSource

T0 = datetime(2026, 10, 24, 10, 0, tzinfo=timezone.utc)


@pytest.fixture
def user(session):
    u = User(email="f@example.com", username="facts")
    session.add(u)
    session.flush()
    return u


@pytest.fixture
def practice(session, user):
    s = PracticeSession(user_id=user.id, language="c", started_at=T0, last_activity_at=T0,
                        graded_count=0, served=[])
    session.add(s)
    session.flush()
    return s


def add_event(session, s, kind, item_id, score, topic="loops", before=0.3, after=0.3,
              misconceptions=(), minute=0):
    ev = LearningEvent(user_id=s.user_id, kind=kind, item_id=item_id, topic=topic, score=score,
                       weight=1.0, language="c", misconceptions=list(misconceptions),
                       mastery_before=before, mastery_after=after, session_id=s.id,
                       created_at=T0 + timedelta(minutes=minute))
    session.add(ev)
    session.flush()
    return ev


def test_facts_counts_and_levels(session, practice):
    add_event(session, practice, "mcq", 1, 1.0, before=0.30, after=0.35, minute=0)
    add_event(session, practice, "mcq", 2, 0.0, before=0.35, after=0.33, minute=2)
    add_event(session, practice, "debug", 5, 0.2, topic="arrays", before=0.50, after=0.48,
              minute=4)
    add_event(session, practice, "code", 9, 0.5, topic="arrays", before=0.48, after=0.47,
              minute=6)
    add_event(session, practice, "code", 9, 1.0, before=0.33, after=0.42, minute=9)

    facts = session_facts(session, practice)

    assert facts.by_type["mcq"] == TypeCount(2, 1)
    assert facts.by_type["debug"] == TypeCount(1, 0)
    assert facts.by_type["coding"] == TypeCount(1, 1)
    loops = next(t for t in facts.topics if t.topic == "loops")
    arrays = next(t for t in facts.topics if t.topic == "arrays")
    assert loops.before == 0.30 and loops.after == 0.42
    assert arrays.before == 0.50 and arrays.after == 0.47
    assert facts.duration_s == 9 * 60


def test_facts_hints_and_mistakes(session, user, practice):
    problem = Problem(source=ProblemSource.DSA, statement="sum", statement_hash="f" * 64,
                      topic="loops")
    session.add(problem)
    session.flush()
    for level in (1, 1, 2):
        session.add(HintEvent(user_id=user.id, problem_id=problem.id, level=level,
                              source="practice", session_id=practice.id))
    session.add(HintEvent(user_id=user.id, problem_id=problem.id, level=3, source="practice"))
    add_event(session, practice, "code", problem.id, 0.0,
              misconceptions=["off_by_one", "wrong_loop_bound"])
    add_event(session, practice, "code", problem.id, 0.5, misconceptions=["off_by_one"])
    session.flush()

    facts = session_facts(session, practice)

    assert facts.hints == {1: 2, 2: 1, 3: 0, 4: 0}
    assert facts.mistakes[0] == ("off_by_one", 2)


def test_awards_only_when_live(session, user, practice, monkeypatch):
    ev = add_event(session, practice, "code", 9, 1.0)
    session.add(GamificationAward(user_id=user.id, learning_event_id=ev.id, kind="points",
                                  code="solved:9", dedupe_key="solved:9", points=10,
                                  message="Solved"))
    session.flush()

    monkeypatch.setattr("app.core.config.settings.GAMIFICATION_MODE", "silent")
    assert session_facts(session, practice).awards is None

    monkeypatch.setattr("app.core.config.settings.GAMIFICATION_MODE", "live")
    awards = session_facts(session, practice).awards
    assert len(awards) == 1
