"""Pure award rules: no database, every case is a hand-built event history."""

import pytest

from app.features.gamification.logic.rules import Ev, evaluate


def ev(id, kind, item, topic="loops", score=1.0, hint=0, m=0.5):
    return Ev(id=id, kind=kind, item_id=item, topic=topic, score=score,
              hint_level_used=hint, mastery_after=m)


def of_kind(awards, kind):
    return [a for a in awards if a.kind == kind]


def test_points_base_times_hint_once_per_item():
    assert [a.points for a in of_kind(evaluate(ev(1, "code", 7, score=0.75, hint=2), [], set()),
                                      "points")] == [8]
    assert of_kind(evaluate(ev(2, "code", 7), [], {"points:code:7"}), "points") == []
    assert [a.points for a in of_kind(evaluate(ev(3, "debug", 4), [], set()), "points")] == [8]
    assert of_kind(evaluate(ev(4, "code", 8, score=0.5), [], set()), "points") == []
    assert evaluate(ev(5, "diagnostic", 9), [], set()) == []


def test_mcq_points_only_when_first_attempt_correct():
    history = [ev(1, "mcq", 3, score=0.0)]
    assert of_kind(evaluate(ev(2, "mcq", 3), history, set()), "points") == []
    assert [a.points for a in of_kind(evaluate(ev(3, "mcq", 5), history, set()), "points")] == [5]


def test_missing_topic_or_item_gives_nothing_and_no_error():
    assert of_kind(evaluate(ev(1, "code", None), [], set()), "points") == []
    assert of_kind(evaluate(ev(2, "code", 1, topic=None, m=None), [], set()), "level_up") == []


def test_level_up_once_never_for_diagnostic_never_revoked():
    diagnostic = ev(1, "diagnostic", 1, m=0.45)
    assert evaluate(diagnostic, [], set()) == []

    history = [diagnostic]
    assert of_kind(evaluate(ev(2, "code", 2, m=0.5), history, set()), "level_up") == []

    history += [ev(2, "code", 2, m=0.5), ev(3, "code", 3, m=0.7)]
    awards = evaluate(ev(4, "code", 4, m=0.8), history, set())
    assert [a.dedupe_key for a in of_kind(awards, "level_up")] == ["level:loops:mastered"]
    assert "badge:first_mastery" in {a.dedupe_key for a in awards}

    history += [ev(4, "code", 4, m=0.8), ev(5, "code", 5, score=0.0, m=0.6)]
    keys = {"level:loops:mastered", "badge:first_mastery"}
    assert of_kind(evaluate(ev(6, "code", 6, m=0.8), history, keys), "level_up") == []


def misses(n, kind="code"):
    return [ev(i, kind, 100 + i, score=0.2, m=0.3) for i in range(1, n + 1)]


BADGE_CASES = [
    ("comeback", misses(3), ev(10, "code", 1), True),
    ("comeback", [ev(1, "code", 50)] + misses(2), ev(10, "code", 1), False),
    ("comeback", misses(3, kind="diagnostic"), ev(10, "code", 1), False),
    ("comeback", misses(3, kind="mcq"), ev(10, "mcq", 103), False),
    ("fixed_it", [ev(1, "code", 1), ev(2, "code", 1, score=0.0)], ev(3, "code", 1), False),
    ("less_help", [ev(1, "code", 1, score=0.5, hint=4)], ev(2, "code", 1), False),
    ("fixed_it", [ev(1, "code", 1, score=0.5)], ev(2, "code", 1), True),
    ("fixed_it", [], ev(2, "code", 1), False),
    ("less_help", [ev(1, "code", 1, score=0.6, hint=3)], ev(2, "code", 2, score=0.9, hint=1), True),
    ("less_help", [ev(1, "code", 1, score=0.6, hint=3)], ev(2, "code", 2, score=0.75, hint=2), False),
    ("less_help", [ev(1, "code", 1, score=0.6, hint=3)], ev(2, "mcq", 2), False),
    ("bug_hunter", [ev(1, "debug", 1), ev(2, "debug", 2)], ev(3, "debug", 3), True),
    ("bug_hunter", [ev(1, "debug", 1), ev(2, "debug", 1)], ev(3, "debug", 1), False),
    ("first_mastery", [ev(1, "code", 1, m=0.5), ev(2, "code", 2, m=0.7)], ev(3, "code", 3, m=0.8), True),
    ("first_mastery", [ev(1, "code", 1, m=0.5)], ev(2, "code", 2, m=0.6), False),
]


@pytest.mark.parametrize("badge,history,event,earned", BADGE_CASES)
def test_badges(badge, history, event, earned):
    codes = {a.code for a in of_kind(evaluate(event, history, set()), "badge")}
    assert (badge in codes) is earned
