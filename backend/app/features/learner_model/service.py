"""The Profiling Agent's steps. The only code allowed to write learning_events,
topic_mastery, and the mirrored fields of LearningProfile."""

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.topics import PREREQUISITES, TOPIC_LABELS, TOPICS, clean_misconceptions, normalise_topic
from app.features.accounts.models import LearningProfile, User
from app.features.learner_model.logic.mastery import (
    GIVE_UP_REF,
    ONE_SHOT_KINDS,
    PRIOR,
    SEED_KINDS,
    WEAK_BELOW,
    WEIGHTS,
    band,
    confidence,
    is_solved,
    updated_mastery,
)
from app.features.learner_model.models import LearningEvent, TopicMastery

MISCONCEPTION_WINDOW = 30
HINT_WINDOW = 10
RECENT_EVENTS = 10


@dataclass
class EventInput:
    user_id: int
    kind: str
    score: float
    raw_topic: str | None
    item_id: int | None = None
    hint_level: int = 0
    misconceptions: list[str] = field(default_factory=list)
    source_ref: str | None = None
    # The language the evidence happened in; None means the student's current one.
    language: str | None = None


DEFAULT_LANGUAGE = "c"


def current_language(db: Session, user_id: int) -> str:
    user = db.get(User, user_id)
    return (user.preferred_language if user else None) or DEFAULT_LANGUAGE


def record_event(db: Session, event_in: EventInput) -> LearningEvent:
    if event_in.kind not in WEIGHTS:
        raise ValueError(f"unknown event kind: {event_in.kind}")
    event = LearningEvent(
        language=event_in.language or current_language(db, event_in.user_id),
        user_id=event_in.user_id,
        kind=event_in.kind,
        item_id=event_in.item_id,
        topic=normalise_topic(event_in.raw_topic),
        raw_topic=(event_in.raw_topic or None) and event_in.raw_topic[:100],
        score=max(0.0, min(1.0, event_in.score)),
        weight=WEIGHTS[event_in.kind],
        hint_level_used=event_in.hint_level,
        misconceptions=clean_misconceptions(event_in.misconceptions),
        source_ref=event_in.source_ref,
    )
    db.add(event)
    db.flush()
    return event


def no_new_evidence(db: Session, event: LearningEvent) -> bool:
    """Any attempt on an item already solved or given up on, and any retry of a
    multiple-choice or theory item (the first answer reveals the key), is logged but says nothing new
    about the topic. Counting it would let a student pump mastery by resubmitting one answer."""
    if event.item_id is None:
        return False
    earlier = (db.query(LearningEvent.score, LearningEvent.hint_level_used,
                        LearningEvent.source_ref)
               .filter(LearningEvent.user_id == event.user_id, LearningEvent.kind == event.kind,
                       LearningEvent.item_id == event.item_id, LearningEvent.id < event.id)
               .all())
    if event.kind in ONE_SHOT_KINDS:
        return bool(earlier)
    return any(is_solved(score, hint) or ref == GIVE_UP_REF for score, hint, ref in earlier)


def update_mastery(db: Session, event: LearningEvent) -> TopicMastery | None:
    if event.topic is None:
        return None
    row = _mastery_row(db, event.user_id, event.topic, event.language)
    event.mastery_before = row.mastery
    if no_new_evidence(db, event):
        event.mastery_after = row.mastery
        db.flush()
        return row
    row.mastery = updated_mastery(row.mastery, event.weight, event.score)
    row.evidence_count += 1
    row.last_event_at = datetime.now(timezone.utc)
    event.mastery_after = row.mastery
    db.flush()
    return row


def _mastery_rows(db: Session, user_id: int) -> dict[str, TopicMastery]:
    rows = (db.query(TopicMastery)
            .filter(TopicMastery.user_id == user_id,
                    TopicMastery.language == current_language(db, user_id)).all())
    return {r.topic: r for r in rows}


def derive_profile(db: Session, user_id: int) -> LearningProfile:
    """Mirror topic_mastery into LearningProfile so existing readers keep working. This
    is the only writer of every field it sets."""
    rows = _mastery_rows(db, user_id)
    profile = db.query(LearningProfile).filter(LearningProfile.user_id == user_id).first()
    if profile is None:
        profile = LearningProfile(user_id=user_id)
        db.add(profile)

    profile.topic_scores = {t: round(r.mastery, 3) for t, r in rows.items()}
    profile.weak_areas = [t for t, r in rows.items()
                          if band(r.mastery, r.evidence_count) == "weak"]
    profile.strong_areas = [t for t, r in rows.items()
                            if band(r.mastery, r.evidence_count) == "mastered"]

    def value(topic: str) -> float:
        return rows[topic].mastery if topic in rows else PRIOR

    open_topics = [t for t in TOPICS
                   if all(value(p) >= WEAK_BELOW for p in PREREQUISITES[t])
                   and band(value(t), rows[t].evidence_count if t in rows else 0) != "mastered"]
    profile.recommended_next = sorted(open_topics, key=value)[:3]
    profile.error_patterns = [tag for tag, _ in top_misconceptions(db, user_id)[:5]]

    scores = [s for (s,) in db.query(LearningEvent.score)
              .filter(LearningEvent.user_id == user_id,
                      LearningEvent.language == current_language(db, user_id),
                      LearningEvent.kind.notin_(SEED_KINDS)).all()]
    profile.accuracy_rate = round(sum(scores) / len(scores), 3) if scores else 0.0
    profile.last_updated_by_agent = datetime.now(timezone.utc)
    db.flush()
    return profile


def _mastery_row(db: Session, user_id: int, topic: str, language: str) -> TopicMastery:
    row = db.get(TopicMastery, (user_id, topic, language))
    if row is None:
        row = TopicMastery(user_id=user_id, topic=topic, language=language,
                           mastery=PRIOR, evidence_count=0)
        db.add(row)
    return row


def _seed_event(db: Session, user_id: int, kind: str, topic: str, value: float,
                language: str) -> LearningEvent | None:
    """A one-time diagnostic reading sets mastery outright instead of nudging it, and
    never goes through ingest, so it awards nothing."""
    if normalise_topic(topic) is None:
        return None
    event = record_event(db, EventInput(user_id, kind, score=value, raw_topic=topic,
                                        language=language))
    row = _mastery_row(db, user_id, event.topic, language)
    event.mastery_before = row.mastery
    row.mastery = event.score
    row.evidence_count = max(row.evidence_count, 1)
    row.last_event_at = datetime.now(timezone.utc)
    event.mastery_after = row.mastery
    db.flush()
    return event


def record_diagnostic_seed(db: Session, user_id: int, seeds: dict[str, float],
                           language: str) -> list[LearningEvent]:
    seeded = (db.query(LearningEvent.id)
              .filter(LearningEvent.user_id == user_id, LearningEvent.kind == "diagnostic_seed",
                      LearningEvent.language == language)
              .first())
    if seeded:
        return []
    events = []
    for topic in TOPICS:
        if topic in seeds:
            event = _seed_event(db, user_id, "diagnostic_seed", topic, seeds[topic], language)
            if event is not None:
                events.append(event)
    derive_profile(db, user_id)
    db.commit()
    return events


def has_practice_on(db: Session, user_id: int, topic: str, language: str) -> bool:
    return (db.query(LearningEvent.id)
            .filter(LearningEvent.user_id == user_id, LearningEvent.topic == topic,
                    LearningEvent.language == language,
                    LearningEvent.kind.notin_(SEED_KINDS))
            .first()) is not None


def apply_theory_adjustment(db: Session, user_id: int, topic: str, new_seed: float,
                            language: str) -> LearningEvent | None:
    topic = normalise_topic(topic)
    if topic is None or has_practice_on(db, user_id, topic, language):
        return None
    current = db.get(TopicMastery, (user_id, topic, language))
    if current is not None and abs(current.mastery - new_seed) < 1e-9:
        return None
    event = _seed_event(db, user_id, "diagnostic_theory", topic, new_seed, language)
    derive_profile(db, user_id)
    db.commit()
    return event


def _recent_events(db: Session, user_id: int, limit: int, kinds=None) -> list[LearningEvent]:
    query = db.query(LearningEvent).filter(LearningEvent.user_id == user_id)
    if kinds:
        query = query.filter(LearningEvent.kind.in_(kinds))
    return query.order_by(LearningEvent.id.desc()).limit(limit).all()


def top_misconceptions(db: Session, user_id: int) -> list[tuple[str, int]]:
    counts = Counter()
    for event in _recent_events(db, user_id, MISCONCEPTION_WINDOW):
        counts.update(event.misconceptions or [])
    return counts.most_common()


def hint_reliance(db: Session, user_id: int) -> float:
    events = _recent_events(db, user_id, HINT_WINDOW, kinds=("code", "debug"))
    if not events:
        return 0.0
    return round(sum(e.hint_level_used for e in events) / len(events), 2)


def mastery_snapshot(db: Session, user_id: int) -> dict:
    rows = _mastery_rows(db, user_id)

    def value(topic: str) -> float:
        return rows[topic].mastery if topic in rows else PRIOR

    topics = []
    for topic in TOPICS:
        row = rows.get(topic)
        count = row.evidence_count if row else 0
        mastery = value(topic)
        topics.append({
            "topic": topic,
            "label": TOPIC_LABELS[topic],
            "mastery": round(mastery, 3),
            "evidence_count": count,
            "confidence": round(confidence(count), 2),
            "band": band(mastery, count),
            "last_event_at": row.last_event_at if row else None,
            "prerequisites": list(PREREQUISITES[topic]),
            "unlocked": all(value(p) >= WEAK_BELOW for p in PREREQUISITES[topic]),
        })

    return {
        "topics": topics,
        "top_misconceptions": [
            {"tag": tag, "count": count} for tag, count in top_misconceptions(db, user_id)
        ],
        "hint_reliance": hint_reliance(db, user_id),
        "recent_events": _recent_events(db, user_id, RECENT_EVENTS),
    }
