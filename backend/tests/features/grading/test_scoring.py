from app.features.grading.agent import scoring
from app.features.grading.agent.static_metrics import Issue, StaticMetrics


def metrics(**overrides) -> StaticMetrics:
    base = dict(lines_of_code=10, comment_ratio=0.1, cyclomatic_complexity=3,
                max_function_length=10, max_parameter_count=2, function_count=1,
                token_count=50)
    base.update(overrides)
    return StaticMetrics(**base)


def issue(category: str) -> Issue:
    return Issue(severity="info", category=category, message="m", suggestion="s")


def test_correctness_is_a_pass_rate():
    assert scoring.correctness_score(7, 9) == round(700 / 9, 1)
    assert scoring.correctness_score(9, 9) == 100.0
    assert scoring.correctness_score(0, 9) == 0.0


def test_correctness_is_none_without_tests():
    assert scoring.correctness_score(0, 0) is None


def test_weights_sum_to_one():
    assert abs(sum(scoring.WEIGHTS.values()) - 1.0) < 1e-9


def test_efficiency_bands():
    assert scoring.efficiency_score("O(1)") == 100.0
    assert scoring.efficiency_score("O(log n)") == 100.0
    assert scoring.efficiency_score("O(n)") == 85.0
    assert scoring.efficiency_score("O(n log n)") == 85.0
    assert scoring.efficiency_score("O(n^2)") == 60.0
    assert scoring.efficiency_score("O(n^3)") == 40.0
    assert scoring.efficiency_score("O(2^n)") == 20.0


def test_unparseable_or_missing_complexity_is_neutral():
    assert scoring.efficiency_score(None) == scoring.UNKNOWN_EFFICIENCY
    assert scoring.efficiency_score("linear-ish") == scoring.UNKNOWN_EFFICIENCY


def test_complexity_penalises_branching_and_length():
    assert scoring.complexity_score(metrics()) == 100.0
    assert scoring.complexity_score(metrics(cyclomatic_complexity=15)) < 100.0
    assert scoring.complexity_score(metrics(max_function_length=60)) < 100.0
    assert scoring.complexity_score(metrics(max_parameter_count=9)) < 100.0


def test_complexity_never_negative():
    worst = metrics(cyclomatic_complexity=200, max_function_length=500,
                    max_parameter_count=50)
    assert scoring.complexity_score(worst) >= 0.0


def test_style_drops_with_issues():
    assert scoring.style_score([]) == 100.0
    assert scoring.style_score([issue("style")]) == 92.0
    assert scoring.style_score([issue("logic")]) == 88.0


def test_overall_uses_all_four_weights_when_verified():
    result = scoring.build_scores(
        tests_passed=10, tests_total=10, metrics=metrics(), issues=[],
        time_complexity="O(n)", verified=True,
    )
    expected = 0.55 * 100 + 0.20 * 100 + 0.15 * 85 + 0.10 * 100
    assert result.correctness == 100.0
    assert result.overall == round(expected, 1)


def test_unverified_leaves_correctness_null_and_renormalises():
    result = scoring.build_scores(
        tests_passed=0, tests_total=0, metrics=metrics(), issues=[],
        time_complexity="O(n)", verified=False,
    )
    assert result.correctness is None
    expected = (0.20 * 100 + 0.15 * 85 + 0.10 * 100) / 0.45
    assert result.overall == round(expected, 1)


def test_unverified_score_is_not_dragged_down_by_missing_correctness():
    verified = scoring.build_scores(
        tests_passed=10, tests_total=10, metrics=metrics(), issues=[],
        time_complexity="O(n)", verified=True,
    )
    unverified = scoring.build_scores(
        tests_passed=0, tests_total=0, metrics=metrics(), issues=[],
        time_complexity="O(n)", verified=False,
    )
    assert abs(verified.overall - unverified.overall) < 8.0


def test_failing_every_test_tanks_the_overall_score():
    result = scoring.build_scores(
        tests_passed=0, tests_total=8, metrics=metrics(), issues=[],
        time_complexity="O(n)", verified=True,
    )
    assert result.correctness == 0.0
    assert result.overall < 50.0
