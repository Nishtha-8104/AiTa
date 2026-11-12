"""The Gamification Engine. The only writer of gamification_awards and of the
points/level/badges mirrors on users; it reads learning_events and nothing else."""

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.features.accounts.models import User
from app.features.gamification.logic import rules
from app.features.gamification.models import GamificationAward
from app.features.gamification.schemas import (
    AwardOut,
    GamificationSummary,
    SelfBoard,
    TopicProgress,
    Window,
)
from app.features.learner_model.logic.mastery import (
    GIVE_UP_REF,
    MASTERED_FROM,
    SEED_KINDS,
    WEAK_BELOW,
    band,
)
from app.features.learner_model.models import LearningEvent, TopicMastery
from app.features.learner_model.service import current_language

RECENT_AWARDS = 10


def snapshot(event: LearningEvent) -> rules.Ev:
    return rules.Ev(id=event.id, kind=event.kind, item_id=event.item_id, topic=event.topic,
                    score=event.score, hint_level_used=event.hint_level_used or 0,
                    mastery_after=event.mastery_after, mastery_before=event.mastery_before,
                    language=event.language, gave_up=event.source_ref == GIVE_UP_REF)


def _history(db: Session, user_id: int, before_id: int) -> list[rules.Ev]:
    rows = (db.query(LearningEvent)
            .filter(LearningEvent.user_id == user_id, LearningEvent.id < before_id,
                    LearningEvent.kind.notin_(SEED_KINDS))
            .order_by(LearningEvent.id).all())
    return [snapshot(r) for r in rows]


def _keys(db: Session, user_id: int) -> set[str]:
    rows = db.query(GamificationAward.dedupe_key).filter(GamificationAward.user_id == user_id)
    return {key for (key,) in rows}


def _insert(db: Session, event: LearningEvent,
            awards: list[rules.Award]) -> list[GamificationAward]:
    stamp = {"created_at": event.created_at} if event.created_at is not None else {}
    rows = [GamificationAward(user_id=event.user_id, learning_event_id=event.id, kind=a.kind,
                              code=a.code, dedupe_key=a.dedupe_key, points=a.points,
                              message=a.message, **stamp) for a in awards]
    db.add_all(rows)
    db.flush()
    return rows


def _lock_user(db: Session, user_id: int) -> None:
    """Two graded answers from one student at once would each miss the other's awards
    and then collide on a dedupe key; serialising per student avoids both."""
    db.query(User).filter(User.id == user_id).with_for_update().one()


def _totals(awards: list[GamificationAward]) -> tuple[int, int]:
    points = sum(a.points for a in awards)
    level = 1 + sum(1 for a in awards if a.kind == "level_up" and a.code.endswith(":mastered"))
    return points, level


def refresh_mirrors(db: Session, user_id: int) -> None:
    user = db.get(User, user_id)
    awards = (db.query(GamificationAward).filter(GamificationAward.user_id == user_id)
              .order_by(GamificationAward.id).all())
    user.points, user.level = _totals(awards)
    user.badges = [a.code for a in awards if a.kind == "badge"]
    db.flush()


def apply(db: Session, event: LearningEvent) -> list[GamificationAward]:
    if settings.GAMIFICATION_MODE == "off" or event.kind in SEED_KINDS:
        return []
    _lock_user(db, event.user_id)
    new = rules.evaluate(snapshot(event), _history(db, event.user_id, event.id),
                         _keys(db, event.user_id))
    rows = _insert(db, event, new)
    refresh_mirrors(db, event.user_id)
    return rows


def rebuild(db: Session, user_id: int) -> int:
    """Replay every event in order into an empty ledger. Ignores the mode: replay is
    how the ledger is audited, and how legacy mirror values are cleared."""
    _lock_user(db, user_id)
    db.query(GamificationAward).filter(GamificationAward.user_id == user_id).delete()
    rows = (db.query(LearningEvent)
            .filter(LearningEvent.user_id == user_id, LearningEvent.kind.notin_(SEED_KINDS))
            .order_by(LearningEvent.id).all())
    events = [snapshot(e) for e in rows]
    keys: set[str] = set()
    written = 0
    for i, (row, ev) in enumerate(zip(rows, events)):
        new = rules.evaluate(ev, events[:i], keys)
        _insert(db, row, new)
        keys |= {a.dedupe_key for a in new}
        written += len(new)
    refresh_mirrors(db, user_id)
    db.commit()
    return written


def _title(row: GamificationAward) -> str:
    if row.kind == "badge":
        return rules.BADGES.get(row.code, (row.code, ""))[0]
    if row.kind == "level_up":
        return rules.label(row.code.split(":")[0])
    return "Solved"


def _out(row: GamificationAward) -> AwardOut:
    return AwardOut(kind=row.kind, code=row.code, title=_title(row), message=row.message,
                    points=row.points, created_at=row.created_at)


def awards_for_event(db: Session, event_id: int | None) -> list[AwardOut]:
    if settings.GAMIFICATION_MODE != "live" or event_id is None:
        return []
    rows = (db.query(GamificationAward).filter(GamificationAward.learning_event_id == event_id)
            .order_by(GamificationAward.id).all())
    return [_out(r) for r in rows]


def _progress(row: TopicMastery) -> TopicProgress:
    if row.mastery < WEAK_BELOW:
        nxt, gap = "developing", WEAK_BELOW - row.mastery
    elif row.mastery < MASTERED_FROM:
        nxt, gap = "mastered", MASTERED_FROM - row.mastery
    else:
        nxt, gap = None, None
    return TopicProgress(topic=row.topic, label=rules.label(row.topic),
                         band=band(row.mastery, row.evidence_count),
                         mastery=round(row.mastery, 3), next_band=nxt,
                         gap_to_next=None if gap is None else round(gap, 2))


def _window(rows: list[GamificationAward]) -> Window:
    return Window(points=sum(r.points for r in rows),
                  solved=sum(1 for r in rows if r.kind == "points"),
                  level_ups=sum(1 for r in rows if r.kind == "level_up"))


def _utc(moment: datetime | None) -> datetime | None:
    if moment is None or moment.tzinfo is not None:
        return moment
    return moment.replace(tzinfo=timezone.utc)


def summary(db: Session, user_id: int) -> GamificationSummary:
    mode = settings.GAMIFICATION_MODE
    if mode == "off":
        return GamificationSummary(mode=mode)
    awards = (db.query(GamificationAward).filter(GamificationAward.user_id == user_id)
              .order_by(GamificationAward.id).all())
    points, level = _totals(awards)
    topics = (db.query(TopicMastery)
              .filter(TopicMastery.user_id == user_id,
                      TopicMastery.language == current_language(db, user_id))
              .order_by(TopicMastery.topic).all())

    now = datetime.now(timezone.utc)
    week = timedelta(days=7)
    dated = [(a, _utc(a.created_at)) for a in awards if a.created_at is not None]
    return GamificationSummary(
        mode=mode,
        points=points,
        level=level,
        topics=[_progress(t) for t in topics],
        badges=[_out(a) for a in awards if a.kind == "badge"],
        self_board=SelfBoard(
            last_7=_window([a for a, at in dated if now - week <= at]),
            prev_7=_window([a for a, at in dated if now - 2 * week <= at < now - week]),
        ),
        recent=[_out(a) for a in reversed(awards[-RECENT_AWARDS:])],
    )
