"""Mastery maths. Deterministic: every number here can be recomputed by hand from
the learning_events rows."""

PRIOR = 0.3
LEARNING_RATE = 0.3

SEED_KINDS = ("diagnostic_seed", "diagnostic_theory")

# source_ref of the score-0 code event a give-up records; the answer has been seen after it.
GIVE_UP_REF = "give_up"

# Kinds whose key is shown after the first answer, so only that first answer is evidence.
ONE_SHOT_KINDS = ("mcq", "diagnostic", "theory")

WEIGHTS = {"code": 1.0, "debug": 0.8, "mcq": 0.5, "diagnostic": 0.5, "theory": 0.5,
           "diagnostic_seed": 0.0, "diagnostic_theory": 0.0}

HINT_MULTIPLIER = {0: 1.0, 1: 0.9, 2: 0.75, 3: 0.6, 4: 0.5}

WEAK_BELOW = 0.4
MISS_BELOW = 0.5
MASTERED_FROM = 0.75
MASTERED_MIN_CONFIDENCE = 0.6
FULL_CONFIDENCE_AT = 5


def hint_multiplier(level: int) -> float:
    return HINT_MULTIPLIER[max(0, min(4, level))]


def is_solved(score: float, hint_level: int) -> bool:
    return score / hint_multiplier(hint_level) >= 0.999


def code_score(tests_passed: int, tests_total: int, hint_level: int = 0) -> float:
    if tests_total <= 0:
        return 0.0
    return (tests_passed / tests_total) * hint_multiplier(hint_level)


def debug_score(fixed: bool, tests_passed: int, tests_total: int, hint_level: int = 0) -> float:
    if fixed:
        base = 1.0
    elif tests_total > 0:
        base = tests_passed / tests_total * 0.5
    else:
        base = 0.0
    return base * hint_multiplier(hint_level)


def updated_mastery(current: float, weight: float, score: float) -> float:
    return current + LEARNING_RATE * weight * (score - current)


def confidence(evidence_count: int) -> float:
    return min(1.0, evidence_count / FULL_CONFIDENCE_AT)


def band(mastery: float, evidence_count: int) -> str:
    if evidence_count == 0:
        return "unseen"
    if mastery < WEAK_BELOW:
        return "weak"
    if mastery >= MASTERED_FROM and confidence(evidence_count) >= MASTERED_MIN_CONFIDENCE:
        return "mastered"
    return "developing"
