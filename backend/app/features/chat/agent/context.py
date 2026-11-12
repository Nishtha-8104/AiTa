"""What the agent is told about the student before its first model call."""

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.features.accounts.models import User
from app.features.chat.agent.tools import CHAT_LANGUAGES, LastAttempt
from app.features.chat.models import ChatThread
from app.features.grading.models import CodeEvaluation, CodeSubmission
from app.features.learner_model.logic.personalisation import chat_language, style_line
from app.features.learner_model.service import mastery_snapshot
from app.features.problems.models import ExecRole, ExecutionResult, Problem

DEFAULT_LANGUAGE = "c"
TITLE_CHARS = 80
MISTAKES_SHOWN = 3
BANDS_SHOWN = (("weak", "Weak"), ("developing", "Developing"), ("mastered", "Mastered"))


@dataclass
class ChatContext:
    language: str
    last_attempt: LastAttempt | None
    mastery_line: str
    summary: str | None
    passages: list[dict] = field(default_factory=list)
    style: str = ""
    chat_language: str = "auto"


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _title(problem: Problem, submission: CodeSubmission) -> str:
    first_line = next((line.strip() for line in (problem.statement or "").splitlines()
                       if line.strip()), "")
    return _clip(first_line or submission.title or f"Problem {problem.id}", TITLE_CHARS)


def _verdict(db: Session, evaluation: CodeEvaluation) -> str:
    compile_failed = db.query(ExecutionResult.id).filter(
        ExecutionResult.evaluation_id == evaluation.id,
        ExecutionResult.role == ExecRole.STUDENT,
        ExecutionResult.status == "compile_error",
    ).first() is not None
    if compile_failed:
        return "Compilation error"
    total = evaluation.tests_total or 0
    if evaluation.verification_status != "verified" or not total:
        return "Ran without verified tests"
    return "Accepted" if (evaluation.tests_passed or 0) == total else "Failed some tests"


def last_attempt(db: Session, user_id: int) -> LastAttempt | None:
    row = (db.query(CodeEvaluation, CodeSubmission, Problem)
           .join(CodeSubmission, CodeSubmission.id == CodeEvaluation.submission_id)
           .join(Problem, Problem.id == CodeSubmission.problem_id)
           .filter(CodeEvaluation.user_id == user_id, CodeSubmission.user_id == user_id)
           .order_by(CodeEvaluation.id.desc())
           .first())
    if row is None:
        return None
    evaluation, submission, problem = row
    return LastAttempt(problem_id=problem.id, title=_title(problem, submission),
                       verdict=_verdict(db, evaluation), passed=evaluation.tests_passed or 0,
                       total=evaluation.tests_total or 0)


def mastery_line(db: Session, user_id: int) -> str:
    snapshot = mastery_snapshot(db, user_id)
    parts = []
    for band, heading in BANDS_SHOWN:
        labels = [t["label"] for t in snapshot["topics"] if t["band"] == band]
        if labels:
            parts.append(f"{heading}: {', '.join(labels)}")
    if not parts:
        return "No graded practice yet."
    mistakes = [m["tag"] for m in snapshot["top_misconceptions"][:MISTAKES_SHOWN]]
    if mistakes:
        parts.append(f"Frequent mistakes: {', '.join(mistakes)}")
    return "; ".join(parts) + "."


def load(db: Session, user_id: int, thread: ChatThread, *,
         language: str | None = None) -> ChatContext:
    if language not in CHAT_LANGUAGES:
        user = db.get(User, user_id)
        language = user.preferred_language if user and user.preferred_language else None
    return ChatContext(
        language=language if language in CHAT_LANGUAGES else DEFAULT_LANGUAGE,
        last_attempt=last_attempt(db, user_id),
        mastery_line=mastery_line(db, user_id),
        summary=thread.summary,
        style=style_line(db, user_id),
        chat_language=chat_language(db, user_id),
    )
