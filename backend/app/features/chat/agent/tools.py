"""The four tools the chat agent can call. Each returns a compact JSON string for the
LLM, never raises, and records exactly one ToolTrace on the context."""

import json
import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Literal

from langchain_core.tools import BaseTool, StructuredTool
from pydantic import BaseModel, Field, ValidationError

from app.core.exceptions import (
    ExecutorUnavailable, LLMUnavailable, ModelKeyError, PetError, ProblemNotFound,
)
from app.core.topics import TOPICS
from app.features.chat.logic.rag.search import search
from app.features.grading.agent.graph import evaluate_submission
from app.features.grading.agent.schemas import EvalReport
from app.features.grading.models import CodeEvaluation, CodeSubmission, Language
from app.features.grading.schemas import SubmitCodeRequest
from app.features.grading.service import CodeEvalService
from app.features.hints.service import NoHintAvailable, approach_hint, request_hint
from app.features.learner_model.logic import learning_data
from app.features.problems.logic.listing import is_curated
from app.features.problems.models import Problem, ProblemSource
from app.features.problems.service import get_or_create_problem

logger = logging.getLogger(__name__)

CHAT_LANGUAGES = {"c": Language.C, "cpp": Language.CPP, "python": Language.PYTHON}
LANGUAGE_ALIASES = {"c++": "cpp", "python3": "python", "py": "python"}
SEVERITY_RANK = {"critical": 0, "error": 1, "warning": 2, "info": 3}
FRIENDLY_ERRORS = {
    ExecutorUnavailable: "The code runner is unavailable right now. Ask the student to "
                         "try again in a minute.",
    LLMUnavailable: "The AI service is busy right now. Ask the student to try again shortly.",
}
BOOK_HITS = 5
TOP_ISSUES = 3
PASSAGE_CHARS = 700
CASE_CHARS = 400
COMPILE_CHARS = 600
FEEDBACK_CHARS = 400
ISSUE_CHARS = 200
ERROR_CHARS = 300
TRACE_ARG_CHARS = 200
SUMMARY_CHARS = 80


@dataclass
class LastAttempt:
    problem_id: int
    title: str
    verdict: str
    passed: int
    total: int


@dataclass
class ToolTrace:
    name: str
    args: dict
    summary: str
    ok: bool
    ms: int
    citations: list[dict] | None = None


@dataclass
class ToolContext:
    db: object
    user_id: int
    language: str
    last_attempt: LastAttempt | None = None
    provider: object = None
    eval_kwargs: dict = field(default_factory=dict)
    hint_runnable: object = None
    embed: object = None
    traces: list[ToolTrace] = field(default_factory=list)
    # A failing evaluation or a hint is shown exactly as built here; see FixedReply.
    fixed_reply: str | None = None
    # The agent may run one step's tool calls in parallel threads over this one Session.
    lock: threading.Lock = field(default_factory=threading.Lock)


@dataclass
class _Outcome:
    compiled: bool
    verified: bool
    passed: int
    total: int
    compile_output: str | None = None


class _Refusal(Exception):
    def __init__(self, error: str, message: str):
        super().__init__(message)
        self.error = error
        self.message = message


def _clip(text: str | None, limit: int) -> str | None:
    if text is None or len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _language(value: str | None) -> Language:
    key = (value or "").strip().lower()
    key = LANGUAGE_ALIASES.get(key, key)
    if key not in CHAT_LANGUAGES:
        raise _Refusal("invalid_language",
                       f"Unsupported language {value!r}. Use one of: c, cpp, python.")
    return CHAT_LANGUAGES[key]


def _rollback(db) -> None:
    try:
        db.rollback()
    except Exception:
        logger.exception("rollback after a chat tool failure failed")


def _end_transaction(db) -> None:
    """A read-only tool would otherwise leave the session idle in a transaction, holding
    a pooled connection through the agent's next LLM call."""
    try:
        db.commit()
    except Exception:
        logger.exception("ending a chat tool's transaction failed")
        _rollback(db)


def _invalid(exc: ValidationError) -> str:
    return "; ".join(f"{'.'.join(map(str, e['loc'])) or 'input'}: {e['msg']}"
                     for e in exc.errors())


def _failure(exc: Exception) -> str:
    for kind, text in FRIENDLY_ERRORS.items():
        if isinstance(exc, kind):
            return text
    if isinstance(exc, PetError):
        return exc.detail
    return "Unexpected failure."


def _traced(ctx: ToolContext, name: str, schema: type[BaseModel], body):
    """Validate the raw arguments, run a body returning (payload, summary, citations),
    and always yield a JSON string plus one trace, whatever happens inside."""
    def run(**kwargs) -> str:
        with ctx.lock:
            started = time.perf_counter()
            citations = None
            try:
                payload, summary, citations = body(**schema.model_validate(kwargs).model_dump())
                ok = "error" not in payload
            except ValidationError as exc:
                payload = {"error": "invalid_arguments", "message": _clip(_invalid(exc), ERROR_CHARS)}
                summary, ok = "invalid arguments", False
            except _Refusal as exc:
                payload = {"error": exc.error, "message": exc.message}
                summary, ok = exc.error.replace("_", " "), False
            except ModelKeyError:
                _rollback(ctx.db)
                raise
            except Exception as exc:
                _rollback(ctx.db)
                logger.exception("chat tool %s failed", name)
                payload = {"error": "tool_failed", "message": _clip(_failure(exc), ERROR_CHARS)}
                summary, ok = "failed", False
            _end_transaction(ctx.db)
            ctx.traces.append(ToolTrace(
                name=name,
                args={k: _clip(v, TRACE_ARG_CHARS) if isinstance(v, str) else v
                      for k, v in kwargs.items()},
                summary=_clip(summary, SUMMARY_CHARS),
                ok=ok,
                ms=int((time.perf_counter() - started) * 1000),
                citations=citations,
            ))
        return json.dumps(payload, ensure_ascii=False, default=str)
    return run


def _usable(ctx: ToolContext, problem_id: int) -> bool:
    if ctx.last_attempt is not None and ctx.last_attempt.problem_id == problem_id:
        return True
    problem = ctx.db.get(Problem, problem_id)
    if problem is None:
        return False
    if (is_curated(problem) or problem.source == ProblemSource.GENERATED
            or problem.created_by_user_id == ctx.user_id):
        return True
    return ctx.db.query(CodeSubmission.id).filter(
        CodeSubmission.user_id == ctx.user_id, CodeSubmission.problem_id == problem_id,
    ).first() is not None


def _resolve_problem(ctx: ToolContext, problem_id: int | None, problem_text: str | None) -> int:
    if problem_text and problem_text.strip():
        problem, _ = get_or_create_problem(ctx.db, problem_text.strip(),
                                           source=ProblemSource.STUDENT,
                                           created_by_user_id=ctx.user_id)
        return problem.id
    if problem_id is not None:
        if not _usable(ctx, problem_id):
            raise _Refusal("unknown_problem", f"Problem {problem_id} is not available. "
                           "Ask the student for the problem statement.")
        return problem_id
    if ctx.last_attempt is not None:
        return ctx.last_attempt.problem_id
    raise _Refusal("need_problem", "Ask the student for the problem statement.")


def _evaluate(ctx: ToolContext, code: str, language: Language, problem_id: int) -> EvalReport:
    if not code or not code.strip():
        raise _Refusal("empty_code", "The code is empty. Ask the student to paste their program.")
    submission = CodeEvalService.submit(ctx.db, ctx.user_id, SubmitCodeRequest(
        language=language, code=code, problem_id=problem_id,
    ))
    # Chat is not practice: no attempt here is ever mastery evidence.
    report = evaluate_submission(ctx.db, submission.id, ctx.user_id, provider=ctx.provider,
                                 emit=False, hint_source="chat", explain_failures=False,
                                 **ctx.eval_kwargs)
    ctx.last_attempt = LastAttempt(
        problem_id=report.problem_id or problem_id, title=submission.title or "",
        verdict=report.verdict or report.mode, passed=report.tests_passed,
        total=report.tests_total,
    )
    return report


def _outcome(report: EvalReport) -> _Outcome:
    return _Outcome(
        compiled=report.compiled,
        verified=report.verification_status == "verified" and report.tests_total > 0,
        passed=report.tests_passed, total=report.tests_total,
        compile_output=report.compile_output,
    )


def _previous_outcome(ctx: ToolContext, problem_id: int, code: str,
                      language: Language) -> _Outcome | None:
    """The latest evaluation on this problem, when it verified this exact code. Anything
    else (compile error, executor down, no tests) is re-run: the stored row cannot say
    which, and compile output is not kept."""
    row = (ctx.db.query(CodeEvaluation, CodeSubmission)
           .join(CodeSubmission, CodeSubmission.id == CodeEvaluation.submission_id)
           .filter(CodeEvaluation.user_id == ctx.user_id,
                   CodeSubmission.problem_id == problem_id)
           .order_by(CodeEvaluation.id.desc())
           .first())
    if row is None:
        return None
    evaluation, submission = row
    if (submission.language != language or submission.code.strip() != code.strip()
            or evaluation.verification_status != "verified" or not evaluation.tests_total):
        return None
    return _Outcome(compiled=True, verified=True, passed=evaluation.tests_passed or 0,
                    total=evaluation.tests_total)


UNVERIFIED_REPLY = ("**Not checked** · I couldn't build trusted tests for this problem, so I "
                    "can't tell yet whether your code is right.\n\nWant a hint? I can guide "
                    "you from the problem statement.")


def _keep_lines(text: str) -> str:
    """Hint templates are plain text with meaningful line breaks (a multi-line input);
    Markdown would join them, so each line outside code fences ends in a hard break."""
    lines, in_fence = [], False
    for line in text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        lines.append(line if in_fence or line.lstrip().startswith("```") else line + "  ")
    return "\n".join(lines).rstrip()


def _block(label: str, text: str | None) -> str:
    return f"{label}:\n```\n{_clip(text or '', CASE_CHARS).rstrip()}\n```"


def _failing_reply(report: EvalReport) -> str:
    case = report.first_failing_case
    parts = [f"**{report.verdict}** · {report.tests_passed}/{report.tests_total} tests passed",
             _block("Input", case.stdin), _block("Expected", case.expected_stdout),
             _block("Your output", case.actual_stdout)]
    if case.stderr:
        parts.append(_block("Error", case.stderr))
    parts.append("Want a hint? Ask and I'll start with a gentle one.")
    return "\n\n".join(parts)


def _eval_summary(report: EvalReport) -> str:
    if not report.compiled:
        return "compile error"
    if report.tests_total:
        return f"{report.tests_passed}/{report.tests_total} tests passed"
    return f"no tests ({report.unverified_reason or report.mode})"


def _eval_payload(report: EvalReport, problem_id: int) -> dict:
    failing = report.first_failing_case
    payload = {
        "problem_id": report.problem_id or problem_id,
        "mode": report.mode,
        "verdict": report.verdict,
        "passed": report.tests_passed,
        "total": report.tests_total,
        "first_failing": None if failing is None else {
            "input": _clip(failing.stdin, CASE_CHARS),
            "expected": _clip(failing.expected_stdout, CASE_CHARS),
            "actual": _clip(failing.actual_stdout, CASE_CHARS),
            "status": failing.status,
            **({"stderr": _clip(failing.stderr, CASE_CHARS)} if failing.stderr else {}),
        },
        "metrics": report.metrics.model_dump(exclude_none=True),
    }
    if not report.compiled:
        payload["compile_output"] = _clip(report.compile_output, COMPILE_CHARS)
    if report.unverified_reason:
        payload["unverified_reason"] = report.unverified_reason
    if failing is not None:
        # The diagnosis would be an unlogged hint; get_hint is the only way to the fix.
        return payload
    if report.summary:
        payload["feedback"] = _clip(report.summary, FEEDBACK_CHARS)
    issues = sorted(report.issues, key=lambda i: SEVERITY_RANK.get(i.severity, len(SEVERITY_RANK)))
    if issues:
        payload["issues"] = [{
            "line": issue.line, "severity": issue.severity,
            "message": _clip(issue.message, ISSUE_CHARS),
            "suggestion": _clip(issue.suggestion, ISSUE_CHARS),
        } for issue in issues[:TOP_ISSUES]]
    return payload


class SearchBooksArgs(BaseModel):
    query: str = Field(description="A short keyword phrase for the concept, e.g. "
                       "'pointer arithmetic' or 'scanf reading a string'.")
    language: str | None = Field(default=None, description="c, cpp or python. Restricts "
                                 "results to that language's books plus general ones. "
                                 "Omit to use the student's preferred language.")


class LearningDataArgs(BaseModel):
    source: Literal[learning_data.SOURCES] = Field(description="Which record to read.")
    topic: str | None = Field(default=None, description="Optional topic filter, one of: "
                              + ", ".join(TOPICS) + ".")
    language: str | None = Field(default=None, description="Optional: c, cpp or python. "
                                 "Filters coding and debug attempts only.")
    period: Literal["7d", "30d", "all"] = Field(default="all", description="Time window.")
    item_type: Literal[learning_data.ITEM_TYPES] | None = Field(
        default=None, description="Optional: only coding problems, MCQs or debug challenges.")


PROBLEM_ID = ("Id of the problem, from the context or an earlier tool result. Send "
              "problem_id or problem_text, not both.")
PROBLEM_TEXT = ("The problem statement in the student's words, even a one-line task such as "
                "'reverse a string', when no problem_id is known. If omitted, the student's "
                "last attempt is assumed, so always send it for a new problem. Send "
                "problem_id or problem_text, not both.")


class EvaluateCodeArgs(BaseModel):
    code: str = Field(description="The student's complete program exactly as they wrote "
                      "it. It reads stdin and prints to stdout.")
    language: str = Field(description="c, cpp or python.")
    problem_id: int | None = Field(default=None, description=PROBLEM_ID)
    problem_text: str | None = Field(default=None, description=PROBLEM_TEXT)


class GetHintArgs(BaseModel):
    level: int = Field(ge=1, le=4, description="1 = a nudge (with code: the failing input "
                       "to trace by hand); 2 = the concept involved; 3 = the steps in "
                       "plain words; 4 = most specific (with code: points at the faulty "
                       "line; without code: a pseudocode outline).")
    language: str = Field(description="c, cpp or python: the language the student is using.")
    problem_id: int | None = Field(default=None, description=PROBLEM_ID)
    problem_text: str | None = Field(default=None, description=PROBLEM_TEXT)
    code: str | None = Field(default=None, description="The student's current program, if "
                             "they have one. Omit when they have not started coding.")


SEARCH_BOOKS = (
    "Search the course textbooks (C, C++, Python and general programming guides) for "
    "passages explaining a programming concept, language feature, library function or "
    "error message. Use it for 'what is / how does / why' questions, then answer in your "
    "own words and cite each passage you use by its ref number, like [1]. Do not use "
    "it for questions about the student's own progress (use query_learning_data) or to "
    "check their code (use evaluate_code). Returns up to 5 passages."
)

QUERY_LEARNING_DATA = (
    "Look up the current student's own learning records. Use it for any question about "
    "their progress, scores, history or weak spots ('what's my accuracy', 'which topics "
    "am I weak in', 'what did I solve this week'); never guess these facts. Sources: "
    "mastery = per-topic mastery, band and unlock state; solved = count and list of "
    "solved items by topic; accuracy = pass rate overall, by item type and by topic; "
    "attempts = the 10 most recent graded attempts; hints = hints taken by level and "
    "source, and hint reliance; misconceptions = most frequent mistake tags; "
    "feedback_reports = latest feedback reports; recent_activity = latest learning "
    "events with scores. Zero counts or empty lists mean no data yet, not an error."
)

EVALUATE_CODE = (
    "Compile and run the student's program against the test cases of a problem. Returns "
    "the verdict, tests passed/total, the first failing case (input, expected, actual), "
    "compile errors and quality metrics; a short feedback summary and the main code "
    "issues only when every test passes. A failing run is shown to the student as is. "
    "Use it when the student shares code for a problem and asks whether it is correct, "
    "why it fails, or how to improve it. Send problem_id when known, or problem_text "
    "when the student pasted a statement, not both; with neither, the student's last "
    "attempted problem is used. If the tool answers need_problem, ask the student for "
    "the problem statement. Do not use it for code that is not a solution to a problem, "
    "or to run your own code."
)

GET_HINT = (
    "Give the student a hint for a problem without revealing the solution. Use it when "
    "they are stuck, ask for a hint, or ask how to start. Start at level 1 and go up one "
    "level at a time unless the student asks for more. Pass their current code when "
    "they have some: code identical to their last graded attempt reuses that result, "
    "while new code re-runs the tests first. The hint targets the first failing case; "
    "if every test passes or the code does not compile, no hint is given. Without code "
    "the hint comes from the problem statement alone. Identify the problem the same way "
    "as evaluate_code. Do not use it for general concept questions (use search_books) "
    "or to check whether code is correct (use evaluate_code)."
)


def build_tools(ctx: ToolContext) -> list[BaseTool]:
    def search_books(query: str, language: str | None = None):
        lang = _language(language).value if language else ctx.language
        hits = search(ctx.db, query, language=lang, k=BOOK_HITS, embed=ctx.embed)
        citations: list[dict] = []
        for hit in hits:
            cite = {"title": hit.source_title, "chapter": hit.chapter,
                    "section": hit.section, "url": hit.url}
            if cite not in citations:
                citations.append(cite)
        payload = {"results": [{
            "title": hit.source_title, "chapter": hit.chapter, "section": hit.section,
            "url": hit.url, "text": _clip(hit.text, PASSAGE_CHARS),
        } for hit in hits]}
        if not hits:
            payload["message"] = "No matching passages. Answer from general knowledge."
        return payload, f"{len(citations)} sources", citations

    def query_learning_data(source: str, topic: str | None = None,
                            language: str | None = None, period: str = "all",
                            item_type: str | None = None):
        lang = _language(language).value if language else None
        payload = learning_data.query(ctx.db, ctx.user_id, source, topic=topic,
                                      language=lang, period=period, item_type=item_type)
        if "error" in payload:
            return payload, payload["error"], None
        return payload, source if period == "all" else f"{source} ({period})", None

    def evaluate_code(code: str, language: str, problem_id: int | None = None,
                      problem_text: str | None = None):
        lang = _language(language)
        pid = _resolve_problem(ctx, problem_id, problem_text)
        report = _evaluate(ctx, code, lang, pid)
        if ctx.fixed_reply is None:
            if report.first_failing_case is not None:
                ctx.fixed_reply = _failing_reply(report)
            elif report.compiled and report.verification_status != "verified":
                ctx.fixed_reply = UNVERIFIED_REPLY
        return _eval_payload(report, pid), _eval_summary(report), None

    def get_hint(level: int, language: str, problem_id: int | None = None,
                 problem_text: str | None = None, code: str | None = None):
        lang = _language(language)
        pid = _resolve_problem(ctx, problem_id, problem_text)
        try:
            outcome = None
            if code and code.strip():
                outcome = (_previous_outcome(ctx, pid, code, lang)
                           or _outcome(_evaluate(ctx, code, lang, pid)))
            if outcome is not None and not outcome.compiled:
                payload = {"problem_id": pid, "compiled": False,
                           "message": "The code does not compile, so no hint was given. "
                                      "Help the student fix the compiler errors first."}
                if outcome.compile_output:
                    payload["compile_output"] = _clip(outcome.compile_output, COMPILE_CHARS)
                return payload, "compile error", None
            if outcome is not None and outcome.verified and outcome.passed == outcome.total:
                return {"passed": True, "problem_id": pid,
                        "message": f"All {outcome.total} tests pass, so no hint is "
                                   "needed."}, "all tests pass", None
            if outcome is not None and outcome.verified:
                hint = request_hint(ctx.db, ctx.user_id, pid, level=level, source="chat",
                                    runnable=ctx.hint_runnable, provider=ctx.provider)
            else:
                hint = approach_hint(ctx.db, ctx.user_id, pid, level=level, language=lang,
                                     has_code=outcome is not None,
                                     runnable=ctx.hint_runnable, provider=ctx.provider)
        except NoHintAvailable as exc:
            raise _Refusal("no_hint", exc.detail) from exc
        except ProblemNotFound as exc:
            raise _Refusal("problem_not_found", exc.detail) from exc
        ctx.fixed_reply = f"**Hint {hint.level}/4:** {_keep_lines(hint.text)}"
        return ({"level": hint.level, "hint": hint.text, "problem_id": pid},
                f"hint L{hint.level}", None)

    specs = [
        ("search_books", SEARCH_BOOKS, SearchBooksArgs, search_books),
        ("query_learning_data", QUERY_LEARNING_DATA, LearningDataArgs, query_learning_data),
        ("evaluate_code", EVALUATE_CODE, EvaluateCodeArgs, evaluate_code),
        ("get_hint", GET_HINT, GetHintArgs, get_hint),
    ]
    # A JSON-schema args_schema skips LangChain's own validation, so _traced validates
    # and can record the raw arguments of a malformed call in its trace.
    return [
        StructuredTool.from_function(
            func=_traced(ctx, name, schema, body), name=name, description=description,
            args_schema=schema.model_json_schema(),
        )
        for name, description, schema, body in specs
    ]
