"""The adaptive diagnostic walk. Pure: the next item is a function of the responses
so far and the student's bank index. There is no time limit, only item caps."""

from app.core.topics import PREREQUISITES, TOPICS
from app.features.onboarding.logic.types import Ask, BankIndex, Done, ItemRef, Resp

TIERS: tuple[tuple[str, ...], ...] = (
    ("basics_io", "conditionals"),
    ("loops", "functions"),
    ("arrays", "strings"),
    ("recursion", "sorting", "searching"),
    ("hashing_sets", "stacks_queues", "dynamic_programming"),
)
TIER_SAMPLE = {4: 2, 5: 1}
CODE_KINDS = ("predict_output", "find_bug", "fill_blank")

ITEM_CAP = 12
CODE_CAP = 9
THEORY_COUNT = 3
PASS = 0.5
FOLLOWUP_CAP = 0.6
STRONG = 0.75
WRITE_PASS = 1.0

CODE_PHASES = ("warmup", "code", "followup", "retry")
WRITE_TOPICS = ("arrays", "strings")
WARMUP = ItemRef("basics_io", "predict_output", "easy", "warmup")

UNTESTED, PASSED, FAILED_ONCE, NEEDS_WORK, BLOCKED, SKIPPED = (
    "untested", "passed", "failed_once", "needs_work", "blocked", "skipped")

_TIER_OF = {topic: n for n, tier in enumerate(TIERS, 1) for topic in tier}
_ORDER = {topic: i for i, topic in enumerate(TOPICS)}


def _ancestors(topic: str) -> frozenset[str]:
    found: set[str] = set()
    for parent in PREREQUISITES[topic]:
        found |= {parent} | _ancestors(parent)
    return frozenset(found)


ANCESTORS = {topic: _ancestors(topic) for topic in TOPICS}


def _attempts(responses: list[Resp], topic: str, difficulty: str) -> list[Resp]:
    return [r for r in responses if r.ref.topic == topic and r.ref.difficulty == difficulty
            and r.ref.phase in CODE_PHASES]


def _best(responses: list[Resp]) -> float | None:
    scores = [r.score for r in responses if r.score is not None]
    return max(scores) if scores else None


def _status(topic: str, code: list[Resp], bank: BankIndex) -> str:
    medium = _attempts(code, topic, "medium")
    if not medium:
        if any(_status(a, code, bank) == NEEDS_WORK for a in ANCESTORS[topic]):
            return BLOCKED
        return UNTESTED
    best_medium = _best(medium)
    if best_medium is None:
        easy = _best(_attempts(code, topic, "easy"))
        if easy is None:
            return SKIPPED
        return PASSED if easy >= PASS else NEEDS_WORK
    if best_medium >= PASS:
        return PASSED
    easy = _attempts(code, topic, "easy")
    best_easy = _best(easy)
    if best_easy is None:
        followup_possible = any((topic, k, "easy") in bank for k in CODE_KINDS)
        return FAILED_ONCE if followup_possible and not easy else NEEDS_WORK
    return PASSED if best_easy >= PASS else NEEDS_WORK


def topic_scores(responses: list[Resp]) -> dict[str, float]:
    scored = [r for r in responses if r.ref.phase in CODE_PHASES and r.score is not None]
    scores: dict[str, float] = {}
    for topic in dict.fromkeys(r.ref.topic for r in scored):
        medium = _best(_attempts(scored, topic, "medium")) or 0.0
        easy = _best(_attempts(scored, topic, "easy")) or 0.0
        scores[topic] = max(medium, min(easy, FOLLOWUP_CAP))
    return scores


def write_passed(responses: list[Resp]) -> bool:
    return any(r.ref.phase == "write" and r.score == WRITE_PASS for r in responses)


def _next_kind(code: list[Resp], topic: str, difficulty: str, bank: BankIndex) -> str | None:
    start = len(code) % len(CODE_KINDS)
    rotated = CODE_KINDS[start:] + CODE_KINDS[:start]
    available = [k for k in rotated if (topic, k, difficulty) in bank]
    fresh = [k for k in available if not code or k != code[-1].ref.kind]
    choices = fresh or available
    return choices[0] if choices else None


def _retry_ask(code: list[Resp], bank: BankIndex) -> Ask | None:
    last = code[-1]
    if last.graded_by != "skipped" or last.ref.phase not in CODE_PHASES:
        return None
    topic = last.ref.topic
    if any(r.ref.topic == topic and r.ref.phase == "retry" for r in code):
        return None
    if (topic, "predict_output", last.ref.difficulty) in bank:
        return Ask(ItemRef(topic, "predict_output", last.ref.difficulty, "retry"))
    asked_easy = any(r.ref.topic == topic and r.ref.kind == "predict_output"
                     and r.ref.difficulty == "easy" for r in code)
    if (topic, "predict_output", "easy") in bank and not asked_easy:
        return Ask(ItemRef(topic, "predict_output", "easy", "retry"))
    return None


def _followup_ask(code: list[Resp], bank: BankIndex) -> Ask | None:
    for topic in TOPICS:
        if _status(topic, code, bank) != FAILED_ONCE or _attempts(code, topic, "easy"):
            continue
        kind = _next_kind(code, topic, "easy", bank)
        if kind:
            return Ask(ItemRef(topic, kind, "easy", "followup"))
    return None


def _tier_stops(statuses: dict[str, str]) -> bool:
    values = statuses.values()
    return PASSED not in values and any(s in (FAILED_ONCE, NEEDS_WORK, BLOCKED) for s in values)


def _write_ask(code: list[Resp], statuses: dict[str, str], bank: BankIndex) -> Ask | None:
    if any(r.ref.phase == "write" for r in code):
        return None
    if any(s not in (PASSED, UNTESTED) for s in statuses.values()):
        return None
    for topic in WRITE_TOPICS:
        if statuses.get(topic) == PASSED and (topic, "write_code", "medium") in bank:
            return Ask(ItemRef(topic, "write_code", "medium", "write"))
    return None


def _tier_ask(code: list[Resp], bank: BankIndex) -> Ask | None:
    for tier_no, tier in enumerate(TIERS, 1):
        statuses = {topic: _status(topic, code, bank) for topic in tier}
        asked = sum(1 for s in statuses.values() if s not in (UNTESTED, BLOCKED))
        if asked < TIER_SAMPLE.get(tier_no, len(tier)):
            for topic in tier:
                if statuses[topic] != UNTESTED:
                    continue
                kind = _next_kind(code, topic, "medium", bank)
                if kind:
                    return Ask(ItemRef(topic, kind, "medium", "code"))
        if _tier_stops(statuses):
            return None
        if tier_no == 3:
            write = _write_ask(code, statuses, bank)
            if write:
                return write
    return None


def _next_code_ask(code: list[Resp], bank: BankIndex) -> Ask | None:
    if not code:
        if (WARMUP.topic, WARMUP.kind, WARMUP.difficulty) in bank:
            return Ask(WARMUP)
        return _tier_ask(code, bank)
    return _retry_ask(code, bank) or _followup_ask(code, bank) or _tier_ask(code, bank)


def _theory_candidates(code: list[Resp]) -> list[str]:
    scores = topic_scores(code)
    passed = sorted((t for t, s in scores.items() if s >= PASS),
                    key=lambda t: (-_TIER_OF[t], -scores[t], -_ORDER[t]))
    failed = [t for t in TOPICS if t in scores and scores[t] < PASS]
    middle = (PASS + STRONG) / 2
    borderline = sorted((t for t, s in scores.items() if PASS <= s < STRONG),
                        key=lambda t: (abs(scores[t] - middle), _ORDER[t]))
    slots = passed[:1] + failed[:1]
    slots += [t for t in borderline if t not in slots][:1]
    partners = list(TIERS[_TIER_OF[passed[0]] - 1]) if passed else []
    fill = borderline + partners + ["basics_io"] + list(scores) + list(TOPICS)
    return list(dict.fromkeys(slots + fill))


def theory_topics(responses: list[Resp]) -> list[str]:
    """The 3 preferred theory slots, before filtering by the bank. The topics actually
    asked are the ones with theory responses."""
    return _theory_candidates(_code(responses))[:THEORY_COUNT]


def _code(responses: list[Resp]) -> list[Resp]:
    return [r for r in responses if r.ref.phase != "theory"]


def _next_theory_ask(responses: list[Resp], bank: BankIndex) -> Ask | Done:
    asked = {r.ref.topic for r in responses if r.ref.phase == "theory"}
    candidates = [t for t in _theory_candidates(_code(responses))
                  if (t, "theory", "medium") in bank]
    for topic in candidates[:THEORY_COUNT]:
        if topic not in asked:
            return Ask(ItemRef(topic, "theory", "medium", "theory"))
    return Done()


def _code_walk_over(responses: list[Resp]) -> bool:
    theory_started = any(r.ref.phase == "theory" for r in responses)
    return theory_started or len(_code(responses)) >= CODE_CAP


def next_step(responses: list[Resp], bank: BankIndex) -> Ask | Done:
    if len(responses) >= ITEM_CAP:
        return Done()
    if not _code_walk_over(responses):
        ask = _next_code_ask(_code(responses), bank)
        if ask:
            return ask
    return _next_theory_ask(responses, bank)


def remaining(responses: list[Resp], bank: BankIndex) -> int:
    """Items still to ask if every remaining answer passed."""
    simulated = list(responses)
    step = next_step(simulated, bank)
    while isinstance(step, Ask):
        simulated.append(Resp(step.ref, 1.0, "estimate"))
        step = next_step(simulated, bank)
    left = len(simulated) - len(responses)
    return max(0, min(left, ITEM_CAP - len(responses)))
