"""Award rules. Pure and deterministic: each award is a function of one verified
learning event and the events before it, so the ledger can be replayed from
learning_events at any time."""

from dataclasses import dataclass

from app.core.topics import TOPIC_LABELS
from app.features.learner_model.logic.mastery import MISS_BELOW, ONE_SHOT_KINDS, band, hint_multiplier
from app.features.learner_model.logic.mastery import is_solved as solved_score

BASE_POINTS = {"code": 10, "debug": 8, "mcq": 5, "theory": 5}
BAND_RANK = {"developing": 1, "mastered": 2}
STUCK_RUN = 3
BUG_HUNTER_FIXES = 3
LESS_HELP_DROP = 2

BADGES: dict[str, tuple[str, str]] = {
    "comeback": ("Comeback", "You were stuck on {topic} and worked through it."),
    "fixed_it": ("Fixed it", "Your code failed, you found why, and fixed it. "
                             "That is how programmers work."),
    "less_help": ("Less help", "You solved {topic} with much less help than before."),
    "bug_hunter": ("Bug hunter", "You've repaired 3 broken programs. "
                                 "Reading code is a core skill."),
    "first_mastery": ("First mastery", "You mastered your first topic: {topic}."),
}


@dataclass(frozen=True)
class Ev:
    id: int
    kind: str
    item_id: int | None
    topic: str | None
    score: float
    hint_level_used: int
    mastery_after: float | None
    mastery_before: float | None = None
    language: str | None = None
    gave_up: bool = False


@dataclass(frozen=True)
class Award:
    kind: str
    code: str
    dedupe_key: str
    points: int
    title: str
    message: str


def label(topic: str | None) -> str:
    return TOPIC_LABELS.get(topic, topic) if topic else ""


def is_solved(ev: Ev) -> bool:
    return solved_score(ev.score, ev.hint_level_used)


def gave_up_before(ev: Ev, history: list[Ev]) -> bool:
    return ev.item_id is not None and any(
        h.gave_up and h.kind == ev.kind and h.item_id == ev.item_id for h in history)


def points(ev: Ev, history: list[Ev]) -> list[Award]:
    if ev.kind not in BASE_POINTS or ev.item_id is None or not is_solved(ev):
        return []
    if ev.kind in ONE_SHOT_KINDS and any(h.kind == ev.kind and h.item_id == ev.item_id
                                         for h in history):
        return []
    if gave_up_before(ev, history):
        return []
    value = int(BASE_POINTS[ev.kind] * hint_multiplier(ev.hint_level_used) + 0.5)
    code = f"{ev.kind}:{ev.item_id}"
    return [Award("points", code, f"points:{code}", value, "Solved",
                  f"+{value} for solving a {ev.kind} item.")]


def _rank(mastery: float | None, evidence: int) -> int:
    return 0 if mastery is None else BAND_RANK.get(band(mastery, evidence), 0)


def level_up(ev: Ev, history: list[Ev]) -> list[Award]:
    """The band the event started from counts as reached: a diagnostic seed can place a
    student in a band without any history event to show for it."""
    if ev.kind == "diagnostic" or not ev.topic or ev.mastery_after is None:
        return []
    same = [h for h in history if h.topic == ev.topic and h.language == ev.language]
    best_before = max([_rank(h.mastery_after, i + 1) for i, h in enumerate(same)]
                      + [_rank(ev.mastery_before, max(len(same), 1))])
    reached = band(ev.mastery_after, len(same) + 1)
    if BAND_RANK.get(reached, 0) <= best_before:
        return []
    code = f"{ev.topic}:{reached}"
    return [Award("level_up", code, f"level:{code}", 0, label(ev.topic),
                  f"{label(ev.topic)} is now {reached}.")]


def _badge(code: str, topic: str | None = None) -> Award:
    title, template = BADGES[code]
    return Award("badge", code, f"badge:{code}", 0, title, template.format(topic=label(topic)))


def first_solve(ev: Ev, history: list[Ev]) -> bool:
    """The same rule Profiling uses for evidence: a retried MCQ or a re-solved item
    proves nothing new, so it can't earn a process badge either."""
    if not is_solved(ev):
        return False
    if ev.item_id is None:
        return True
    same = [h for h in history if h.kind == ev.kind and h.item_id == ev.item_id]
    if ev.kind in ONE_SHOT_KINDS:
        return not same
    return not any(is_solved(h) or h.gave_up for h in same)


def comeback(ev: Ev, history: list[Ev]) -> bool:
    if not ev.topic or not first_solve(ev, history) or ev.kind == "diagnostic":
        return False
    run = [h for h in history if h.topic == ev.topic and h.kind != "diagnostic"][-STUCK_RUN:]
    return len(run) == STUCK_RUN and all(h.score < MISS_BELOW for h in run)


def fixed_it(ev: Ev, history: list[Ev]) -> bool:
    return (ev.kind == "code" and ev.item_id is not None and first_solve(ev, history)
            and any(h.kind == "code" and h.item_id == ev.item_id and not is_solved(h)
                    for h in history))


def less_help(ev: Ev, history: list[Ev]) -> bool:
    if ev.kind != "code" or not ev.topic or not first_solve(ev, history):
        return False
    earlier =[h.hint_level_used for h in history if h.kind == "code" and h.topic == ev.topic]
    return bool(earlier) and ev.hint_level_used <= max(earlier) - LESS_HELP_DROP


def bug_hunter(ev: Ev, history: list[Ev]) -> bool:
    if ev.kind != "debug" or not is_solved(ev):
        return False
    fixed = {h.item_id for h in history + [ev]
             if h.kind == "debug" and h.item_id is not None and is_solved(h)}
    return len(fixed) >= BUG_HUNTER_FIXES


def badges(ev: Ev, history: list[Ev], levels: list[Award]) -> list[Award]:
    earned = [_badge(code, ev.topic) for code, rule in
              (("comeback", comeback), ("fixed_it", fixed_it),
               ("less_help", less_help), ("bug_hunter", bug_hunter))
              if rule(ev, history)]
    if any(a.code.endswith(":mastered") for a in levels):
        earned.append(_badge("first_mastery", ev.topic))
    return earned


def evaluate(ev: Ev, history: list[Ev], existing_keys: set[str]) -> list[Award]:
    levels = [a for a in level_up(ev, history) if a.dedupe_key not in existing_keys]
    awards = points(ev, history) + levels + badges(ev, history, levels)
    return [a for a in awards if a.dedupe_key not in existing_keys]
