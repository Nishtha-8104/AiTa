"""Read-only answers about one student's own learning, shaped for an LLM tool call:
small JSON-serialisable dicts, every query scoped to the caller's user_id."""

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Literal

from sqlalchemy.orm import Session

from app.core.topics import TOPIC_LABELS, TOPICS, normalise_topic
from app.features.feedback.models import FeedbackReport
from app.features.grading.models import CodeEvaluation, CodeSubmission, Language
from app.features.hints.models import HintEvent
from app.features.learner_model.logic.mastery import SEED_KINDS
from app.features.learner_model.models import LearningEvent
from app.features.learner_model.service import (
    MISCONCEPTION_WINDOW,
    hint_reliance,
    mastery_snapshot,
    top_misconceptions,
)
from app.features.practice.models import (
    DebugAttempt,
    DebugChallenge,
    McqAttempt,
    McqQuestion,
)
from app.features.problems.models import Problem

SOURCES = ("mastery", "solved", "accuracy", "attempts", "hints", "misconceptions",
           "feedback_reports", "recent_activity")
PERIODS = {"7d": 7, "30d": 30, "all": None}
ITEM_TYPES = ("coding", "mcq", "debug")
LANGUAGES = ("c", "cpp", "python")
EVENT_KINDS = {"coding": ("code",), "mcq": ("mcq", "diagnostic"), "debug": ("debug",)}
_ATTEMPT_FILTERS = frozenset({"period", "topic", "language", "item_type"})
APPLIED_FILTERS = {
    "mastery": frozenset({"topic"}),
    "solved": _ATTEMPT_FILTERS,
    "accuracy": _ATTEMPT_FILTERS,
    "attempts": _ATTEMPT_FILTERS,
    "hints": frozenset({"period", "topic"}),
    "misconceptions": frozenset({"period", "topic", "item_type"}),
    "feedback_reports": frozenset({"period"}),
    "recent_activity": frozenset({"period", "topic", "item_type"}),
}

SOLVED_ITEMS = 20
LAST_ATTEMPTS = 10
FEEDBACK_REPORTS = 3
RECENT_ACTIVITY = 15
TOP_TAGS = 10
TITLE_CHARS = 80
SUMMARY_CHARS = 400


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _label(topic: str | None) -> str | None:
    return TOPIC_LABELS.get(topic) if topic else None


def _short(text: str | None, limit: int = TITLE_CHARS) -> str | None:
    if not text:
        return None
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _rate(passed: int, attempts: int) -> float | None:
    return round(passed / attempts, 3) if attempts else None


def _verified(evaluation: CodeEvaluation) -> bool:
    return evaluation.verification_status == "verified" and bool(evaluation.tests_total)


def _coding_attempts(db, user_id, since, topic, language, limit=None) -> list[dict]:
    query = (db.query(CodeEvaluation, CodeSubmission, Problem)
             .join(CodeSubmission, CodeEvaluation.submission_id == CodeSubmission.id)
             .outerjoin(Problem, CodeSubmission.problem_id == Problem.id)
             .filter(CodeEvaluation.user_id == user_id, CodeSubmission.user_id == user_id))
    if since:
        query = query.filter(CodeEvaluation.created_at >= since)
    if language:
        query = query.filter(CodeSubmission.language == Language(language))
    if limit:
        query = query.order_by(CodeEvaluation.created_at.desc(), CodeEvaluation.id.desc())
        if not topic:
            query = query.limit(limit)
    rows = []
    for evaluation, submission, problem in query:
        item_topic = normalise_topic(problem.topic) if problem else None
        if topic and item_topic != topic:
            continue
        total = evaluation.tests_total or 0
        passed = evaluation.tests_passed or 0
        verified = _verified(evaluation)
        rows.append({
            "type": "coding",
            "key": ("coding", submission.problem_id or f"s{submission.id}"),
            "id": evaluation.id,
            "title": _short(submission.title or (problem.statement if problem else None)),
            "topic": item_topic,
            "language": getattr(submission.language, "value", submission.language),
            "verified": verified,
            "passed": verified and passed == total,
            "verdict": ("passed" if passed == total else "failed") if verified else "unverified",
            "tests": f"{passed}/{total}",
            "at": evaluation.created_at,
        })
        if limit and len(rows) == limit:
            break
    return rows


def _mcq_attempts(db, user_id, since, topic, limit=None) -> list[dict]:
    query = (db.query(McqAttempt, McqQuestion)
             .join(McqQuestion, McqAttempt.question_id == McqQuestion.id)
             .filter(McqAttempt.user_id == user_id))
    if since:
        query = query.filter(McqAttempt.created_at >= since)
    if topic:
        query = query.filter(McqQuestion.topic == topic)
    if limit:
        query = query.order_by(McqAttempt.created_at.desc(), McqAttempt.id.desc()).limit(limit)
    return [{
        "type": "mcq",
        "key": ("mcq", question.id),
        "id": attempt.id,
        "title": _short(question.stem),
        "topic": question.topic,
        "language": None,
        "verified": True,
        "passed": bool(attempt.correct),
        "verdict": "passed" if attempt.correct else "failed",
        "tests": None,
        "at": attempt.created_at,
    } for attempt, question in query]


def _debug_attempts(db, user_id, since, topic, language, limit=None) -> list[dict]:
    query = (db.query(DebugAttempt, DebugChallenge)
             .join(DebugChallenge, DebugAttempt.challenge_id == DebugChallenge.id)
             .filter(DebugAttempt.user_id == user_id))
    if since:
        query = query.filter(DebugAttempt.created_at >= since)
    if topic:
        query = query.filter(DebugChallenge.topic == topic)
    if language:
        query = query.filter(DebugChallenge.language == language)
    if limit:
        query = query.order_by(DebugAttempt.created_at.desc(), DebugAttempt.id.desc()).limit(limit)
    return [{
        "type": "debug",
        "key": ("debug", challenge.id),
        "id": attempt.id,
        "title": _short(challenge.statement),
        "topic": challenge.topic,
        "language": challenge.language,
        "verified": True,
        "passed": bool(attempt.fixed),
        "verdict": "passed" if attempt.fixed else "failed",
        "tests": f"{attempt.tests_passed}/{attempt.tests_total}",
        "at": attempt.created_at,
    } for attempt, challenge in query]


def _attempts(db, user_id, since, topic, language, item_type, limit=None) -> list[dict]:
    rows = []
    if item_type in (None, "coding"):
        rows += _coding_attempts(db, user_id, since, topic, language, limit)
    if item_type in (None, "mcq") and not language:
        rows += _mcq_attempts(db, user_id, since, topic, limit)
    if item_type in (None, "debug"):
        rows += _debug_attempts(db, user_id, since, topic, language, limit)
    floor = datetime.min
    rows.sort(key=lambda r: (r["at"].replace(tzinfo=None) if r["at"] else floor, r["id"]),
              reverse=True)
    return rows[:limit] if limit else rows


def _solved(rows) -> dict:
    first_seen: dict = {}
    for row in rows:
        if row["passed"] and row["key"] not in first_seen:
            first_seen[row["key"]] = row
    solved = list(first_seen.values())
    by_topic = Counter(r["topic"] or "unknown" for r in solved)
    return {
        "count": len(solved),
        "by_topic": dict(by_topic.most_common()),
        "items": [{"title": r["title"], "type": r["type"], "topic": r["topic"],
                   "solved_at": _iso(r["at"])} for r in solved[:SOLVED_ITEMS]],
        "unverified": sum(not r["verified"] for r in rows),
    }


def _tally(rows) -> dict:
    graded = [r for r in rows if r["verified"]]
    passed = sum(r["passed"] for r in graded)
    return {"attempts": len(graded), "passed": passed, "rate": _rate(passed, len(graded)),
            "unverified": len(rows) - len(graded)}


def _accuracy(rows) -> dict:
    by_topic: dict[str, list] = {}
    by_type: dict[str, list] = {}
    for row in rows:
        by_topic.setdefault(row["topic"] or "unknown", []).append(row)
        by_type.setdefault(row["type"], []).append(row)
    return {
        **_tally(rows),
        "by_type": {t: _tally(rs) for t, rs in by_type.items()},
        "by_topic": {t: {"label": _label(t), **_tally(rs)} for t, rs in by_topic.items()},
    }


def _last_attempts(rows) -> dict:
    return {"items": [{
        "type": r["type"], "title": r["title"], "topic": r["topic"],
        "language": r["language"], "verdict": r["verdict"], "tests": r["tests"],
        "at": _iso(r["at"]),
    } for r in rows]}


def _mastery(db, user_id, topic) -> dict:
    snapshot = mastery_snapshot(db, user_id)
    return {
        "topics": [{
            "topic": t["topic"], "label": t["label"], "mastery": t["mastery"],
            "evidence_count": t["evidence_count"], "band": t["band"],
            "unlocked": t["unlocked"], "last_event_at": _iso(t["last_event_at"]),
        } for t in snapshot["topics"] if not topic or t["topic"] == topic],
        "top_misconceptions": snapshot["top_misconceptions"][:5],
        "hint_reliance_all_time": snapshot["hint_reliance"],
    }


def _hints(db, user_id, since, topic) -> dict:
    query = (db.query(HintEvent, Problem.topic)
             .outerjoin(Problem, HintEvent.problem_id == Problem.id)
             .filter(HintEvent.user_id == user_id))
    if since:
        query = query.filter(HintEvent.created_at >= since)
    events = [e for e, raw in query if not topic or normalise_topic(raw) == topic]
    by_level = Counter(str(e.level) for e in events if not e.was_blocked)
    return {
        "total": len(events),
        "by_level": dict(sorted(by_level.items())),
        "blocked": sum(e.was_blocked for e in events),
        "by_source": dict(Counter(e.source for e in events)),
        "hint_reliance_all_time": hint_reliance(db, user_id),
    }


def _events_query(db, user_id, since, topic, item_type):
    query = db.query(LearningEvent).filter(LearningEvent.user_id == user_id,
                                           LearningEvent.kind.notin_(SEED_KINDS))
    if since:
        query = query.filter(LearningEvent.created_at >= since)
    if topic:
        query = query.filter(LearningEvent.topic == topic)
    if item_type:
        query = query.filter(LearningEvent.kind.in_(EVENT_KINDS[item_type]))
    return query.order_by(LearningEvent.id.desc())


def _misconceptions(db, user_id, since, topic, item_type) -> dict:
    if since or topic or item_type:
        counts = Counter()
        for event in _events_query(db, user_id, since, topic, item_type).limit(MISCONCEPTION_WINDOW):
            counts.update(event.misconceptions or [])
        tags = counts.most_common()
    else:
        tags = top_misconceptions(db, user_id)
    return {"tags": [{"tag": t, "count": n} for t, n in tags[:TOP_TAGS]]}


def _feedback_reports(db, user_id, since) -> dict:
    query = db.query(FeedbackReport).filter(FeedbackReport.user_id == user_id)
    if since:
        query = query.filter(FeedbackReport.created_at >= since)
    reports = query.order_by(FeedbackReport.id.desc()).limit(FEEDBACK_REPORTS)
    return {"reports": [{
        "headline": r.headline,
        "summary": _short(r.summary, SUMMARY_CHARS),
        "strengths": (r.strengths or [])[:3],
        "errors": (r.errors or [])[:3],
        "action_items": (r.action_items or [])[:3],
        "next_topics": (r.next_topics or [])[:3],
        "pattern_only": r.pattern_only,
        "created_at": _iso(r.created_at),
    } for r in reports]}


def _recent_activity(db, user_id, since, topic, item_type) -> dict:
    events = _events_query(db, user_id, since, topic, item_type).limit(RECENT_ACTIVITY)
    return {"events": [{
        "kind": e.kind, "topic": e.topic, "label": _label(e.topic),
        "score": round(e.score, 2), "hint_level": e.hint_level_used,
        "misconceptions": e.misconceptions or [], "at": _iso(e.created_at),
    } for e in events]}


def query(db: Session, user_id: int, source: str, *, topic: str | None = None,
          language: str | None = None, period: Literal["7d", "30d", "all"] = "all",
          item_type: str | None = None, now: datetime | None = None) -> dict:
    if source not in SOURCES:
        return {"error": "unknown source", "valid": list(SOURCES)}
    if period not in PERIODS:
        return {"error": "unknown period", "valid": list(PERIODS)}
    if item_type is not None and item_type not in ITEM_TYPES:
        return {"error": "unknown item_type", "valid": list(ITEM_TYPES)}
    if language is not None:
        language = language.strip().lower()
        if language not in LANGUAGES:
            return {"error": "unknown language", "valid": list(LANGUAGES)}
    if topic is not None:
        resolved = normalise_topic(topic)
        if resolved is None:
            return {"error": "unknown topic", "valid": list(TOPICS)}
        topic = resolved

    days = PERIODS[period]
    since = (now or datetime.now(timezone.utc)) - timedelta(days=days) if days else None
    filters = {"period": period, "topic": topic, "label": _label(topic),
               "language": language, "item_type": item_type}
    applied = APPLIED_FILTERS[source] | ({"label"} if "topic" in APPLIED_FILTERS[source] else set())
    scope = {"source": source,
             **{k: v for k, v in filters.items() if k in applied and v is not None}}

    if source == "mastery":
        data = _mastery(db, user_id, topic)
    elif source == "attempts":
        data = _last_attempts(_attempts(db, user_id, since, topic, language, item_type,
                                        LAST_ATTEMPTS))
    elif source in ("solved", "accuracy"):
        rows = _attempts(db, user_id, since, topic, language, item_type)
        data = _solved(rows) if source == "solved" else _accuracy(rows)
    elif source == "hints":
        data = _hints(db, user_id, since, topic)
    elif source == "misconceptions":
        data = _misconceptions(db, user_id, since, topic, item_type)
    elif source == "feedback_reports":
        data = _feedback_reports(db, user_id, since)
    else:
        data = _recent_activity(db, user_id, since, topic, item_type)
    return {"scope": scope, **data}
