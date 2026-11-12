"""Turns test results and static metrics into 0-100 scores: correctness, complexity,
efficiency, style, and their weighted overall."""

import re

from app.features.grading.agent.schemas import ScoreBreakdown
from app.features.grading.agent.static_metrics import Issue, StaticMetrics

WEIGHTS = {
    "correctness": 0.55,
    "complexity": 0.20,
    "efficiency": 0.15,
    "style": 0.10,
}

_COMPLEXITY_BANDS = [
    (r"o\(1\)|o\(log", 100.0),
    (r"o\(n\s*log|o\(n\)|o\(m\s*\+\s*n\)", 85.0),
    (r"o\(n\s*\^?\s*2\)|o\(n\s*\*\s*n\)|o\(n²\)", 60.0),
    (r"o\(n\s*\^?\s*3\)|o\(n³\)", 40.0),
    (r"o\(2\s*\^|o\(n!\)", 20.0),
]

UNKNOWN_EFFICIENCY = 75.0


def correctness_score(tests_passed: int, tests_total: int) -> float | None:
    if tests_total <= 0:
        return None
    return round(100.0 * tests_passed / tests_total, 1)


def complexity_score(metrics: StaticMetrics) -> float:
    score = 100.0
    if metrics.cyclomatic_complexity > 5:
        score -= min((metrics.cyclomatic_complexity - 5) * 4, 40)
    if metrics.max_function_length > 25:
        score -= min((metrics.max_function_length - 25) * 1.5, 25)
    if metrics.max_parameter_count > 4:
        score -= min((metrics.max_parameter_count - 4) * 5, 15)
    return round(max(score, 0.0), 1)


def efficiency_score(time_complexity: str | None) -> float:
    if not time_complexity:
        return UNKNOWN_EFFICIENCY
    text = time_complexity.lower().replace(" ", "")
    for pattern, value in _COMPLEXITY_BANDS:
        if re.search(pattern, text):
            return value
    return UNKNOWN_EFFICIENCY


def style_score(issues: list[Issue]) -> float:
    style_issues = [i for i in issues if i.category in ("style", "naming", "quality")]
    logic_issues = [i for i in issues if i.category == "logic"]
    score = 100.0 - len(style_issues) * 8 - len(logic_issues) * 12
    return round(max(score, 0.0), 1)


def overall_score(scores: dict[str, float | None]) -> float:
    """Weighted mean over the dimensions that carry a value.

    A NULL correctness means it could not be measured, so its weight is removed and
    the remaining weights are renormalised. The score is never padded with a guess.
    """
    usable = {k: v for k, v in scores.items() if v is not None and k in WEIGHTS}
    total_weight = sum(WEIGHTS[k] for k in usable)
    if total_weight == 0:
        return 0.0
    weighted = sum(WEIGHTS[k] * v for k, v in usable.items())
    return round(weighted / total_weight, 1)


def build_scores(
    *,
    tests_passed: int,
    tests_total: int,
    metrics: StaticMetrics,
    issues: list[Issue],
    time_complexity: str | None,
    verified: bool,
) -> ScoreBreakdown:
    correctness = correctness_score(tests_passed, tests_total) if verified else None
    dimensions = {
        "correctness": correctness,
        "complexity": complexity_score(metrics),
        "efficiency": efficiency_score(time_complexity),
        "style": style_score(issues),
    }
    return ScoreBreakdown(
        overall=overall_score(dimensions),
        correctness=correctness,
        complexity=dimensions["complexity"],
        efficiency=dimensions["efficiency"],
        style=dimensions["style"],
    )
