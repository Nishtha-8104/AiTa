import pytest

from app.features.learner_model.logic.mastery import (
    PRIOR,
    band,
    code_score,
    confidence,
    debug_score,
    hint_multiplier,
    updated_mastery,
)


def test_update_formula_matches_the_spec_by_hand():
    assert updated_mastery(PRIOR, 1.0, 1.0) == pytest.approx(0.3 + 0.3 * (1.0 - 0.3))
    assert updated_mastery(0.51, 0.5, 0.0) == pytest.approx(0.51 + 0.15 * (0.0 - 0.51))


@pytest.mark.parametrize("level, multiplier", [
    (0, 1.0), (1, 0.9), (2, 0.75), (3, 0.6), (4, 0.5), (9, 0.5), (-1, 1.0),
])
def test_hint_multipliers(level, multiplier):
    assert hint_multiplier(level) == multiplier


def test_code_score_is_pass_rate_times_hint_multiplier():
    assert code_score(4, 6) == pytest.approx(4 / 6)
    assert code_score(6, 6, hint_level=2) == pytest.approx(0.75)
    assert code_score(0, 0) == 0.0


def test_debug_score_halves_partial_credit():
    assert debug_score(True, 6, 6) == 1.0
    assert debug_score(False, 3, 6) == pytest.approx(0.25)
    assert debug_score(True, 6, 6, hint_level=1) == pytest.approx(0.9)


def test_confidence_saturates_at_five_events():
    assert confidence(0) == 0.0
    assert confidence(3) == pytest.approx(0.6)
    assert confidence(12) == 1.0


@pytest.mark.parametrize("mastery, count, expected", [
    (0.3, 0, "unseen"),
    (0.39, 4, "weak"),
    (0.4, 1, "developing"),
    (0.9, 2, "developing"),
    (0.75, 3, "mastered"),
    (0.74, 9, "developing"),
])
def test_bands(mastery, count, expected):
    assert band(mastery, count) == expected
