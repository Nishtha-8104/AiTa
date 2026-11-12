"""One-off generation of the assessment banks: LLM drafts, execution decides.

Raw replies are cached, so re-running re-parses and re-verifies without spending."""

import json
import pathlib
from collections import Counter

from sqlalchemy.orm import Session

from app.core import llm_gateway
from app.core.llm import invoke_with_retry
from app.core.topics import MISCONCEPTIONS, TOPIC_LABELS, TOPICS
from app.features.grading.agent.multi_test import display_statement
from app.features.practice.logic.assessment.parsing import parse_debug, parse_mcqs
from app.features.practice.logic.assessment.prompts import BUG_DESCRIPTIONS, DEBUG_PROMPT, MCQ_PROMPT
from app.features.practice.logic.assessment.sanitize import strip_bug_annotations
from app.features.practice.logic.assessment.verify import verify_debug, verify_mcq
from app.features.problems.models import Problem

MCQS_PER_TOPIC = 4
MCQ_DRAFTS_PER_TOPIC = 6
DIAGNOSTIC_TOPICS = ("basics_io", "conditionals", "loops", "arrays", "strings", "functions")

DEBUG_PLAN = (
    ("dsa-fizzbuzz", "python", "off_by_one"),
    ("dsa-binary-search", "python", "wrong_comparison_operator"),
    ("dsa-valid-parentheses", "python", "empty_input_unhandled"),
    ("dsa-fibonacci", "python", "missing_base_case"),
    ("mbpp-284", "python", "wrong_loop_bound"),
    ("dsa-count-characters", "python", "uninitialised_variable"),
    ("dsa-max-subarray", "cpp", "wrong_initial_value"),
    ("dsa-second-largest", "cpp", "wrong_comparison_operator"),
    ("dsa-reverse-string", "cpp", "off_by_one"),
    ("dsa-merge-sorted", "cpp", "index_out_of_range"),
    ("mbpp-078", "cpp", "wrong_loop_bound"),
    ("mbpp-231", "cpp", "uninitialised_variable"),
)

_FENCES = {"python": "python", "cpp": "cpp"}
_LANGUAGE_NAMES = {"python": "Python 3", "cpp": "C++17"}


class RawCache:
    def __init__(self, path: pathlib.Path, refresh: bool = False):
        self.path = path
        self.data = {} if refresh or not path.exists() else json.loads(path.read_text("utf-8"))

    def get(self, key: str, produce) -> str:
        if key not in self.data:
            self.data[key] = produce()
            self.path.write_text(json.dumps(self.data, indent=2), "utf-8")
        return self.data[key]


def _ask(runnable, prompt: str) -> str:
    if runnable is None:
        message = llm_gateway.invoke("assessment_gen", prompt).value
    else:
        message, _ = invoke_with_retry(runnable, prompt)
    return getattr(message, "content", message) or ""


def _mcq_prompt(topic: str, count: int, difficulties: str) -> str:
    return MCQ_PROMPT.format(topic_label=TOPIC_LABELS[topic], count=count,
                             difficulties=difficulties, tags=", ".join(MISCONCEPTIONS))


def _keep_mcqs(drafts: list[dict], topic: str, limit: int, provider, log: Counter,
               prefix: str) -> list[dict]:
    kept, seen_stems = [], set()
    for n, item in enumerate(drafts):
        item = {**item, "topic": topic}
        check = verify_mcq(item, provider)
        if not check.ok:
            log[f"mcq dropped: {check.reason.split(' (')[0].split(' printed')[0]}"] += 1
            continue
        if item["stem"] in seen_stems:
            log["mcq dropped: duplicate stem"] += 1
            continue
        seen_stems.add(item["stem"])
        kept.append({
            "external_id": f"{prefix}-{topic}-{len(kept) + 1}",
            "topic": topic,
            "difficulty": item["difficulty"],
            "stem": item["stem"],
            "options": item["options"],
            "answer_index": item["answer_index"],
            "verify_code": item["verify_code"],
            "explanations": [item["explanation"]] if item["explanation"] else [],
        })
        if len(kept) == limit:
            break
    return kept


def generate(db: Session, cache: RawCache, *, runnable=None, provider=None) -> dict:
    log: Counter = Counter()

    mcqs = []
    for topic in TOPICS:
        raw = cache.get(f"mcq:{topic}", lambda t=topic: _ask(
            runnable, _mcq_prompt(t, MCQ_DRAFTS_PER_TOPIC, "2 easy, 2 medium, 2 hard")))
        mcqs += _keep_mcqs(parse_mcqs(raw), topic, MCQS_PER_TOPIC, provider, log, "mcq")

    diagnostic = []
    for topic in DIAGNOSTIC_TOPICS:
        raw = cache.get(f"diagnostic:{topic}", lambda t=topic: _ask(
            runnable, _mcq_prompt(t, 3, "all easy")))
        kept = _keep_mcqs(parse_mcqs(raw), topic, 1, provider, log, "diag")
        for item in kept:
            item["external_id"] = f"diag-{topic}"
            item["is_diagnostic"] = True
        diagnostic += kept
        if not kept:
            log[f"diagnostic missing: {topic}"] += 1

    debug = []
    for external_id, language, bug_type in DEBUG_PLAN:
        problem = db.query(Problem).filter(Problem.external_id == external_id).first()
        if problem is None:
            log[f"debug skipped: {external_id} not seeded"] += 1
            continue
        prompt = DEBUG_PROMPT.format(
            statement=display_statement(problem.statement),
            constraints=problem.constraints or "none stated",
            language=_LANGUAGE_NAMES[language], fence=_FENCES[language],
            bug_type=bug_type, bug_description=BUG_DESCRIPTIONS[bug_type],
        )
        item = None
        for attempt in range(2):
            raw = cache.get(f"debug:{external_id}:{language}:{attempt}",
                            lambda p=prompt: _ask(runnable, p))
            parsed = parse_debug(raw)
            if parsed is None:
                log["debug dropped: unparseable"] += 1
                continue
            candidate = {
                "external_id": f"debug-{language}-{external_id}",
                "problem_external_id": external_id,
                "topic": problem.topic,
                "difficulty": getattr(problem.difficulty, "value", problem.difficulty) or "easy",
                "language": language,
                "statement": display_statement(problem.statement),
                "fixed_code": parsed[0],
                "buggy_code": strip_bug_annotations(parsed[1], parsed[0], language),
                "bug_type": bug_type,
            }
            check = verify_debug(candidate, problem.test_cases, provider)
            if check.ok:
                item = candidate
                break
            log[f"debug dropped: {check.reason.split(' (')[0]}"] += 1
        if item:
            debug.append(item)

    return {"mcqs": mcqs, "diagnostic": diagnostic, "debug": debug, "log": dict(log)}
