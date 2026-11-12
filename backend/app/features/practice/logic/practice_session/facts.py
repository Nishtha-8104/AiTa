"""What one Practice session's learning events and hints say, read straight from the
database. Read-only: nothing here writes or commits."""

from collections import Counter
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.features.gamification.schemas import AwardOut
from app.features.gamification.service import awards_for_event
from app.features.hints.models import HintEvent
from app.features.learner_model.logic.mastery import MISS_BELOW, band, is_solved
from app.features.learner_model.models import LearningEvent, TopicMastery
from app.features.practice.logic.assessment.policy import STUCK_AFTER
from app.features.practice.models import PracticeSession

ITEM_TYPES = ("mcq", "theory", "debug", "coding")
EVENT_TYPES = {"mcq": "mcq", "diagnostic": "mcq", "theory": "theory", "debug": "debug",
               "code": "coding"}
HINT_LEVELS = (1, 2, 3, 4)
TOP_MISTAKES = 3


@dataclass(frozen=True)
class TypeCount:
    tried: int
    solved: int


@dataclass(frozen=True)
class TopicChange:
    topic: str
    before: float
    after: float
    band_after: str


@dataclass
class SessionFacts:
    language: str
    started_at: datetime
    ended_at: datetime | None
    duration_s: int
    by_type: dict[str, TypeCount]
    topics: list[TopicChange]
    hints: dict[int, int]
    mistakes: list[tuple[str, int]]
    stuck_topics: list[str]
    awards: list[AwardOut] | None


def _events(db: Session, session_id: int) -> list[LearningEvent]:
    return (db.query(LearningEvent).filter(LearningEvent.session_id == session_id)
            .order_by(LearningEvent.id).all())


def _duration(events: list[LearningEvent]) -> int:
    stamps = [e.created_at for e in events if e.created_at is not None]
    if len(stamps) < 2:
        return 0
    return int((max(stamps) - min(stamps)).total_seconds())


def _by_type(events: list[LearningEvent]) -> dict[str, TypeCount]:
    tried: dict[str, set[int]] = {t: set() for t in ITEM_TYPES}
    solved: dict[str, set[int]] = {t: set() for t in ITEM_TYPES}
    for e in events:
        item_type = EVENT_TYPES.get(e.kind)
        if item_type is None:
            continue
        tried[item_type].add(e.item_id)
        if is_solved(e.score, e.hint_level_used or 0):
            solved[item_type].add(e.item_id)
    return {t: TypeCount(len(tried[t]), len(solved[t])) for t in ITEM_TYPES}


def _topics(db: Session, s: PracticeSession, events: list[LearningEvent]) -> list[TopicChange]:
    first: dict[str, LearningEvent] = {}
    last: dict[str, LearningEvent] = {}
    for e in events:
        if e.topic is None:
            continue
        first.setdefault(e.topic, e)
        last[e.topic] = e
    if not first:
        return []
    evidence = dict(db.query(TopicMastery.topic, TopicMastery.evidence_count)
                    .filter(TopicMastery.user_id == s.user_id,
                            TopicMastery.language == s.language,
                            TopicMastery.topic.in_(first)).all())
    changes = []
    for topic, start in first.items():
        before = start.mastery_before if start.mastery_before is not None else 0.0
        after = last[topic].mastery_after
        after = before if after is None else after
        changes.append(TopicChange(topic, before, after, band(after, evidence.get(topic, 0))))
    return changes


def _hints(db: Session, session_id: int) -> dict[int, int]:
    counts = Counter(level for (level,) in db.query(HintEvent.level)
                     .filter(HintEvent.session_id == session_id))
    return {level: counts[level] for level in HINT_LEVELS}


def _mistakes(events: list[LearningEvent]) -> list[tuple[str, int]]:
    return Counter(tag for e in events for tag in e.misconceptions or []).most_common(TOP_MISTAKES)


def _stuck(events: list[LearningEvent]) -> list[str]:
    """The policy's stuck rule replayed over the session: STUCK_AFTER misses in a row on
    one topic, where any other event breaks the run."""
    stuck: list[str] = []
    topic, run = None, 0
    for e in events:
        if e.topic is None or e.score >= MISS_BELOW:
            topic, run = None, 0
            continue
        run = run + 1 if e.topic == topic else 1
        topic = e.topic
        if run >= STUCK_AFTER and topic not in stuck:
            stuck.append(topic)
    return stuck


def _awards(db: Session, events: list[LearningEvent]) -> list[AwardOut] | None:
    if settings.GAMIFICATION_MODE != "live":
        return None
    return [a for e in events for a in awards_for_event(db, e.id)]


def session_facts(db: Session, session: PracticeSession) -> SessionFacts:
    events = _events(db, session.id)
    return SessionFacts(
        language=session.language,
        started_at=session.started_at,
        ended_at=session.ended_at,
        duration_s=_duration(events),
        by_type=_by_type(events),
        topics=_topics(db, session, events),
        hints=_hints(db, session.id),
        mistakes=_mistakes(events),
        stuck_topics=_stuck(events),
        awards=_awards(db, events),
    )
