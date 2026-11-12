"""Diagnostic responses to topic mastery seeds, concept level and skill level. Pure."""

from app.core.topics import TOPICS
from app.features.onboarding.logic.types import Resp, Seed
from app.features.onboarding.logic.walk import (
    ANCESTORS,
    PASS,
    STRONG,
    TIERS,
    topic_scores,
    write_passed,
)

SEED_VALUES = {"strong": 0.70, "ok": 0.50, "needs_work": 0.25, "inferred": 0.60}
CODE_WEIGHT = 0.75
CONCEPT_HIGH = 0.75
CONCEPT_MEDIUM = 0.4
ADVANCED_LEVEL = 4
INTERMEDIATE_LEVEL = 3
WRITE_UPGRADES = TIERS[1] + TIERS[2]


def band_of(score: float) -> str:
    if score >= STRONG:
        return "strong"
    return "ok" if score >= PASS else "needs_work"


def blend(code: float, theory: float | None) -> float:
    if theory is None:
        return code
    return round(CODE_WEIGHT * code + (1 - CODE_WEIGHT) * theory, 6)


def seeds(responses: list[Resp]) -> dict[str, Seed]:
    theory = {r.ref.topic: r.score for r in responses
              if r.ref.phase == "theory" and r.score is not None}
    out = {topic: Seed(SEED_VALUES[band_of(blend(score, theory.get(topic)))], "asked")
           for topic, score in topic_scores(responses).items()}
    if write_passed(responses):
        for topic in WRITE_UPGRADES:
            if topic in out and out[topic].value >= SEED_VALUES["ok"]:
                out[topic] = Seed(SEED_VALUES["strong"], "asked")
    passed = [t for t, s in out.items() if s.value >= SEED_VALUES["ok"]]
    for topic in passed:
        for prereq in TOPICS:
            if prereq in ANCESTORS[topic]:
                out.setdefault(prereq, Seed(SEED_VALUES["inferred"], "inferred"))
    return out


def concept_level(theory_scores: list[float | None]) -> str:
    graded = [s for s in theory_scores if s is not None]
    if not graded:
        return "unknown"
    mean = sum(graded) / len(graded)
    if mean >= CONCEPT_HIGH:
        return "high"
    return "medium" if mean >= CONCEPT_MEDIUM else "low"


def tier_level(seeds: dict[str, Seed]) -> int:
    level = 0
    for tier in TIERS:
        asked = [seeds[t] for t in tier if t in seeds and seeds[t].source == "asked"]
        if not asked or any(s.value != SEED_VALUES["strong"] for s in asked):
            break
        level += 1
    return level


def skill_level(seeds: dict[str, Seed]) -> str:
    level = tier_level(seeds)
    if level >= ADVANCED_LEVEL:
        return "advanced"
    return "intermediate" if level >= INTERMEDIATE_LEVEL else "beginner"
