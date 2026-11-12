"""Verification of drafted diagnostic items. Nothing here asks a model: a code item is kept
only if running it proves it, through the same judge path the runtime graders use."""

from dataclasses import dataclass

from app.core.exceptions import ExecutorUnavailable
from app.core.text import normalize_output
from app.features.grading.logic.execution.base import ExecStatus, ExecutionProvider
from app.features.grading.logic.execution.judge import Judgement
from app.features.grading.logic.execution.run_code import run_code
from app.features.onboarding.logic.authoring.parse import TOPICS
from app.features.onboarding.logic.bank import LANGUAGES, SHARED, language_of
from app.features.onboarding.logic.graders.sandbox import run_tests
from app.features.onboarding.models import DiagnosticItem
from app.features.practice.logic.assessment.sanitize import reveals_bug

DIFFICULTIES = ("easy", "medium")
MIN_TESTS = 2
MIN_WRITE_TESTS = 3
PREDICT_RUNS = 2
RUBRIC_SIZE = (3, 4)


@dataclass(frozen=True)
class Check:
    ok: bool
    reason: str = ""
    item: dict | None = None


def _fail(reason: str) -> Check:
    return Check(False, reason)


def _blank(*values) -> bool:
    return any(not isinstance(v, str) or not v.strip() for v in values)


def _judge(item: dict, code: str, provider: ExecutionProvider | None) -> Judgement:
    judgement = run_tests(DiagnosticItem(language=item["language"], key=item["key"]),
                          code, provider)
    if judgement is None:
        raise ExecutorUnavailable("executor unavailable")
    return judgement


def _tests_problem(item: dict, minimum: int) -> str:
    """An empty expected output consumes no lines when the judge splits the output, so
    such a test passes for any program."""
    tests = item["key"].get("tests") or []
    if len(tests) < minimum:
        return "too_few_tests"
    if any(not (t.get("expected_stdout") or "").strip() for t in tests):
        return "empty_expected"
    return ""


def _differing_lines(a: str, b: str) -> set[int]:
    lines_a, lines_b = normalize_output(a).split("\n"), normalize_output(b).split("\n")
    if len(lines_a) != len(lines_b):
        return set()
    return {n for n, (x, y) in enumerate(zip(lines_a, lines_b), 1) if x != y}


def _predict_output(item: dict, provider) -> Check:
    code = item["body"].get("code")
    if _blank(code):
        return _fail("missing_field")
    report = run_code(language_of(item["language"]), code, [("", None)] * PREDICT_RUNS,
                      provider=provider)
    if (not report.compiled or not report.outcomes
            or any(o.status is not ExecStatus.OK for o in report.outcomes)):
        return _fail("did_not_run")
    outputs = {normalize_output(o.actual_stdout) for o in report.outcomes}
    if len(outputs) > 1:
        return _fail("nondeterministic")
    actual = outputs.pop()
    if not actual:
        return _fail("no_output")
    claimed = normalize_output(item["key"].get("expected_output") or "")
    stored = {**item, "key": {**item["key"], "expected_output": actual}}
    return Check(True, "" if claimed == actual else "mismatch_fixed", stored)


def _find_bug(item: dict, provider) -> Check:
    buggy, fixed = item["body"].get("code"), item["key"].get("fixed_code")
    bug_line = item["key"].get("bug_line")
    if _blank(fixed, item["body"].get("statement")):
        return _fail("missing_field")
    if _blank(buggy):
        return _fail("bug_not_planted")
    if _differing_lines(buggy, fixed) != {bug_line}:
        return _fail("bug_line_mismatch")
    if reveals_bug(buggy, fixed, item["language"]):
        return _fail("bug_revealed")
    if problem := _tests_problem(item, MIN_TESTS):
        return _fail(problem)
    if not _judge(item, fixed, provider).all_passed:
        return _fail("fixed_fails")
    bad = _judge(item, buggy, provider)
    if not bad.compiled:
        return _fail("buggy_does_not_compile")
    if bad.all_passed:
        return _fail("buggy_passes")
    return Check(True, item=item)


def _fill_blank(item: dict, provider) -> Check:
    code, marker = item["body"].get("code_with_blank"), item["body"].get("blank_marker")
    answer = item["key"].get("answer")
    if _blank(code, marker) or code.count(marker) != 1:
        return _fail("marker_count")
    if _blank(answer):
        return _fail("missing_field")
    if problem := _tests_problem(item, MIN_TESTS):
        return _fail(problem)
    if not _judge(item, code.replace(marker, answer, 1), provider).all_passed:
        return _fail("completed_fails")
    if _judge(item, code.replace(marker, "", 1), provider).all_passed:
        return _fail("blank_not_required")
    return Check(True, item=item)


def _write_code(item: dict, provider) -> Check:
    if _blank(item["body"].get("statement"), item["body"].get("starter_code"),
              item["key"].get("reference")):
        return _fail("missing_field")
    if problem := _tests_problem(item, MIN_WRITE_TESTS):
        return _fail(problem)
    if not _judge(item, item["key"]["reference"], provider).all_passed:
        return _fail("reference_fails")
    starter = _judge(item, item["body"]["starter_code"], provider)
    if not starter.compiled:
        return _fail("starter_does_not_compile")
    if starter.all_passed:
        return _fail("starter_passes")
    return Check(True, item=item)


def _theory(item: dict, provider) -> Check:
    rubric = item["key"].get("rubric") or []
    if _blank(item["body"].get("question")):
        return _fail("missing_field")
    if not RUBRIC_SIZE[0] <= len(rubric) <= RUBRIC_SIZE[1] or _blank(*rubric):
        return _fail("rubric_size")
    if _blank(item["key"].get("model_answer")):
        return _fail("missing_model_answer")
    return Check(True, item=item)


_CHECKS = {"predict_output": _predict_output, "find_bug": _find_bug,
           "fill_blank": _fill_blank, "write_code": _write_code, "theory": _theory}


def check(item: dict, provider: ExecutionProvider | None = None) -> Check:
    kind, language = item.get("kind"), item.get("language")
    if kind not in _CHECKS:
        return _fail("unknown_kind")
    if language not in LANGUAGES and not (kind == "theory" and language == SHARED):
        return _fail("unknown_language")
    if item.get("topic") not in TOPICS:
        return _fail("unknown_topic")
    if item.get("difficulty") not in DIFFICULTIES:
        return _fail("unknown_difficulty")
    try:
        return _CHECKS[kind](item, provider)
    except ExecutorUnavailable:
        return _fail("executor_unavailable")
