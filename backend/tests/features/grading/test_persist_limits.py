"""A finished evaluation must survive a verbose model.

Everything expensive - compiling, running the sandbox, the LLM call - has already
happened by the time the row is written. A value one character too long for its
column used to raise DataError there and throw the whole run away.
"""

from app.core.text import ellipsize
from app.features.grading.models import CodeEvaluation

PROSE = ("O(n) per test case, where n is the length of the string, due to the "
         "string reversal operation.")


def _limit(column: str) -> int:
    return CodeEvaluation.__table__.columns[column].type.length


def test_the_observed_failure_now_fits():
    assert len(PROSE) > 30, "the value that broke a real evaluation"
    assert len(PROSE) <= _limit("time_complexity")


def test_short_values_are_untouched():
    assert ellipsize("O(n log n)", 120) == "O(n log n)"


def test_none_stays_none():
    assert ellipsize(None, 120) is None


def test_a_value_at_the_limit_is_untouched():
    exact = "x" * 120
    assert ellipsize(exact, 120) == exact


def test_an_overlong_value_is_clamped_not_raised():
    clamped = ellipsize("y" * 500, 120)
    assert len(clamped) == 120
    assert clamped.endswith("…")


def test_every_clamped_column_is_at_least_as_wide_as_the_clamp():
    # Guards the pairing in persist.py: clamping to a width the column cannot hold
    # would still raise.
    assert _limit("time_complexity") >= 120
    assert _limit("space_complexity") >= 120
    assert _limit("model_used") >= 100
