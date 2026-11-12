"""The short written feedback on a closed Practice session: generated once, checked by
the multi-item guardrail, and stored on the session. Flushes but never commits."""

import json
import logging

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core import llm_gateway
from app.core.exceptions import LLMUnavailable
from app.core.llm import invoke_with_retry
from app.features.feedback.logic.activity import activity_context, references_for
from app.features.hints.logic.guardrail import check_multi_item
from app.features.learner_model.models import LearningEvent
from app.features.practice.logic.practice_session.facts import SessionFacts, session_facts
from app.features.practice.models import PracticeSession

logger = logging.getLogger(__name__)

MAX_WORK_ON_NEXT = 2

SYSTEM_PROMPT = """You write the short feedback a student reads at the end of one \
practice session in PET, a teaching assistant for Indian programming students.

Rules:
- Use only the facts given; never invent work the student did not do
- Be specific, not generic: name the topics, the kinds of item and the mistakes that \
came up
- The summary is 2 to 4 sentences: what went well, then what did not
- Give 1 or 2 "work on next" items, each naming a topic and one concrete action, e.g. \
"Loops: try two more problems where the count starts at 0"
- NEVER write code, not even one line, and NEVER state a fix or a solution
- Describe mistakes in plain words, never as tag names like off_by_one
- Plain, simple English with short sentences
"""

SESSION_BLOCK = """PRACTICE SESSION (measured, not estimated):
Language: {language} | Length: {minutes} min
Items tried and solved, by type: {by_type}
Topic levels from 0 to 1, start to end of the session: {topics}
Hints used, by level: {hints}
Most frequent mistakes: {mistakes}
Topics where the student got stuck: {stuck}
Each graded answer, oldest first: {items}"""


class SessionNarrative(BaseModel):
    summary: str = Field(
        description="Two to four sentences on what went well and what did not, from the "
                    "student's facts only, never code"
    )
    work_on_next: list[str] = Field(
        min_length=1,
        description="One or two items, each a topic and a concrete action",
    )


def _events(db: Session, session_id: int) -> list[LearningEvent]:
    return (db.query(LearningEvent).filter(LearningEvent.session_id == session_id)
            .order_by(LearningEvent.id).all())


def _context(facts: SessionFacts, activity: dict) -> str:
    return SESSION_BLOCK.format(
        language=facts.language,
        minutes=facts.duration_s // 60,
        by_type=json.dumps({t: {"tried": c.tried, "solved": c.solved}
                            for t, c in facts.by_type.items()}),
        topics=json.dumps([{"topic": t.topic, "before": round(t.before, 2),
                            "after": round(t.after, 2), "level": t.band_after}
                           for t in facts.topics]),
        hints=json.dumps({f"L{level}": n for level, n in facts.hints.items()}),
        mistakes=json.dumps(dict(facts.mistakes)),
        stuck=", ".join(facts.stuck_topics) or "none",
        items=json.dumps(activity["items"]),
    )


def _narrate(payload, runnable, user_id: int) -> SessionNarrative | None:
    if runnable is not None:
        narrative, _ = invoke_with_retry(runnable, payload)
        return narrative
    return llm_gateway.invoke("session_feedback", payload, schema=SessionNarrative,
                              user_id=user_id).value


def _store(db: Session, session: PracticeSession, status: str,
           feedback: dict | None = None) -> PracticeSession:
    session.feedback = feedback
    session.feedback_status = status
    db.flush()
    return session


def generate_session_feedback(db: Session, session: PracticeSession, *, retry: bool = False,
                              runnable=None) -> PracticeSession:
    if session.feedback_status == "ready" and not retry:
        return session
    events = _events(db, session.id)
    payload = [("system", SYSTEM_PROMPT),
               ("human", _context(session_facts(db, session),
                                  activity_context(db, session.user_id, events)))]
    try:
        narrative = _narrate(payload, runnable, session.user_id)
    except LLMUnavailable as exc:
        logger.warning("Session %s feedback unavailable: %s", session.id, exc.detail)
        return _store(db, session, "unavailable")
    if narrative is None or not narrative.summary.strip():
        logger.warning("Session %s feedback returned no parsed narrative", session.id)
        return _store(db, session, "unavailable")

    items = narrative.work_on_next[:MAX_WORK_ON_NEXT]
    verdict = check_multi_item("\n".join([narrative.summary, *items]),
                               references_for(db, events))
    if verdict.blocked:
        logger.warning("Session %s feedback blocked by the guardrail: %s",
                       session.id, verdict.reason)
        return _store(db, session, "blocked")
    return _store(db, session, "ready", {"summary": narrative.summary, "work_on_next": items})
