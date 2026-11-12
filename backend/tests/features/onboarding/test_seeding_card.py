"""Pure seeding, concept level, skill level and the profile card."""

import pytest

from app.core.topics import TOPICS
from app.features.onboarding.logic import profile_card, seeding
from app.features.onboarding.logic.types import ItemRef, Resp, Seed
from app.features.onboarding.logic.walk import TIERS

ASKED = {"strong": Seed(0.70, "asked"), "ok": Seed(0.50, "asked"),
         "needs_work": Seed(0.25, "asked")}


def code(topic, score, difficulty="medium"):
    return Resp(ItemRef(topic, "predict_output", difficulty, "code"), score, "key")


def theory(topic, score):
    return Resp(ItemRef(topic, "theory", "medium", "theory"), score, "llm")


def test_band_thresholds():
    assert seeding.band_of(0.75) == "strong"
    assert seeding.band_of(0.74) == "ok"
    assert seeding.band_of(0.5) == "ok"
    assert seeding.band_of(0.49) == "needs_work"


def test_seed_values_and_inference():
    out = seeding.seeds([code("arrays", 1.0)])
    assert out["arrays"] == Seed(0.70, "asked")
    for topic in ("loops", "conditionals", "basics_io"):
        assert out[topic] == Seed(0.60, "inferred")
    assert set(out) == {"arrays", "loops", "conditionals", "basics_io"}


def test_inferred_never_overwrites_asked():
    out = seeding.seeds([code("loops", 0.0), code("arrays", 1.0)])
    assert out["loops"] == Seed(0.25, "asked")
    assert out["conditionals"] == Seed(0.60, "inferred")


def test_unasked_above_stop_has_no_seed():
    out = seeding.seeds([
        code("basics_io", 1.0), code("conditionals", 1.0),
        code("loops", 0.0), code("loops", 0.0, "easy"),
        code("functions", 0.0), code("functions", 0.0, "easy"),
    ])
    assert set(out) == {"basics_io", "conditionals", "loops", "functions"}


def test_theory_blend():
    assert seeding.blend(0.6, 1.0) == pytest.approx(0.7)
    assert seeding.seeds([code("loops", 0.6), theory("loops", 1.0)])["loops"].value == 0.50
    assert seeding.blend(0.7, 1.0) == pytest.approx(0.775)
    assert seeding.seeds([code("loops", 0.7), theory("loops", 1.0)])["loops"].value == 0.70
    assert seeding.blend(0.6, None) == 0.6
    assert seeding.seeds([code("loops", 0.75), theory("loops", None)])["loops"].value == 0.70


def test_theory_without_code_score_gives_no_seed():
    responses = [code("basics_io", 1.0), theory("recursion", 1.0)]
    assert "recursion" not in seeding.seeds(responses)


def test_write_code_upgrades_t2_t3():
    responses = [code(t, 0.5) for t in ("basics_io", "loops", "functions", "arrays", "strings")]
    responses.append(Resp(ItemRef("arrays", "write_code", "medium", "write"), 1.0, "sandbox"))
    out = seeding.seeds(responses)
    for topic in ("loops", "functions", "arrays", "strings"):
        assert out[topic] == Seed(0.70, "asked")
    assert out["basics_io"] == Seed(0.50, "asked")


def test_write_code_does_not_upgrade_needs_work():
    responses = [code(t, 1.0) for t in ("basics_io", "conditionals", "loops", "arrays", "strings")]
    responses += [code("functions", 0.0), code("functions", 0.0, "easy"),
                  Resp(ItemRef("arrays", "write_code", "medium", "write"), 1.0, "sandbox")]
    out = seeding.seeds(responses)
    assert out["functions"] == Seed(0.25, "asked")
    assert seeding.skill_level(out) == "beginner"


def test_concept_level():
    assert seeding.concept_level([]) == "unknown"
    assert seeding.concept_level([1, 0.5, 1]) == "high"
    assert seeding.concept_level([0.5, 0.5, 0]) == "low"
    assert seeding.concept_level([0.5, 0.5]) == "medium"


def test_skill_level():
    def cleared(tiers):
        return {t: ASKED["strong"] for tier in TIERS[:tiers] for t in tier}

    assert seeding.skill_level(cleared(4)) == "advanced"
    assert seeding.skill_level(cleared(3)) == "intermediate"
    assert seeding.skill_level(cleared(2)) == "beginner"
    assert seeding.skill_level({**cleared(3), "loops": ASKED["ok"]}) == "beginner"
    assert seeding.skill_level({"basics_io": ASKED["strong"],
                                "loops": Seed(0.60, "inferred")}) == "beginner"


def test_title_map():
    t1_to_t3 = ("basics_io", "conditionals", "loops", "functions", "arrays", "strings")
    assert profile_card.title_for({t: ASKED["strong"] for t in t1_to_t3}) == "Array Ace"
    assert profile_card.title_for({t: ASKED["ok"] for t in t1_to_t3}) == "Fresh Starter"
    gap = {t: ASKED["strong"] for t in t1_to_t3} | {"strings": ASKED["ok"],
                                                    "recursion": ASKED["strong"]}
    assert profile_card.title_for(gap) == "Loop Wrangler"


def test_card_bands_include_unchecked():
    seeds = seeding.seeds([code("arrays", 1.0), code("functions", 0.5)])
    prefs = {"pace": "steady"}
    card = profile_card.build(seeds, "medium", prefs, "strings")
    assert list(card.bands) == list(TOPICS)
    assert card.bands["arrays"] == "strong"
    assert card.bands["functions"] == "ok"
    assert card.bands["loops"] == "ok"
    assert card.bands["recursion"] == "not_checked"
    assert card.inferred == ["basics_io", "conditionals", "loops"]
    assert (card.concept_level, card.start_topic, card.preferences) == ("medium", "strings", prefs)
    assert card.start_reason == profile_card.START_REASONS["not_checked"]
    stored = profile_card.build({"loops": Seed(0.55, "asked")}, "unknown", {}, "loops")
    assert stored.bands["loops"] == "ok"
    assert stored.start_reason == profile_card.START_REASONS["ok"]
    assert profile_card.build(seeds, "medium", {}, "loops").start_reason == (
        profile_card.START_REASONS["inferred"])
