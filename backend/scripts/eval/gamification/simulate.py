"""Offline check of the award rules against simulated students. No database, no LLM:
the real rules.evaluate and mastery maths run over generated event streams.

    python -m scripts.eval.gamification.simulate --seed 7 --students 200

Prints two markdown tables: strategies run by the same students (does gaming pay?),
and honest students of known ability (do awards track ability?)."""

import argparse
import math
import random
from dataclasses import dataclass, field

from app.features.gamification.logic.rules import Ev, evaluate, is_solved
from app.features.learner_model.logic.mastery import (
    MASTERED_FROM,
    PRIOR,
    WEAK_BELOW,
    WEIGHTS,
    code_score,
    debug_score,
    updated_mastery,
)

TOPICS = ("loops", "arrays", "recursion")
BANK = {"mcq": 8, "debug": 4, "code": 6}
MCQ_OPTIONS = 4
STEPS = 60


@dataclass(frozen=True)
class Item:
    id: int
    kind: str
    topic: str
    difficulty: float


@dataclass
class Run:
    ability: dict[str, float]
    rng: random.Random
    mastery: dict[str, float] = field(default_factory=lambda: dict.fromkeys(TOPICS, PRIOR))
    history: list[Ev] = field(default_factory=list)
    keys: set[str] = field(default_factory=set)
    points: int = 0
    badges: int = 0
    level_ups: int = 0
    solved: set[int] = field(default_factory=set)
    seen_mcq: set[int] = field(default_factory=set)

    def p_solve(self, item: Item, hint: int = 0) -> float:
        base = 1 / (1 + math.exp(-8 * (self.ability[item.topic] - item.difficulty)))
        return min(1.0, base + 0.1 * hint)

    def record(self, item: Item, score: float, hint: int = 0) -> bool:
        m = self.mastery[item.topic]
        repeat = item.id in self.solved or (item.kind == "mcq" and item.id in self.seen_mcq)
        if not repeat:
            m = updated_mastery(m, WEIGHTS[item.kind], score)
        self.mastery[item.topic] = m
        ev = Ev(id=len(self.history) + 1, kind=item.kind, item_id=item.id, topic=item.topic,
                score=score, hint_level_used=hint, mastery_after=m)
        for award in evaluate(ev, self.history, self.keys):
            self.keys.add(award.dedupe_key)
            self.points += award.points
            self.badges += award.kind == "badge"
            self.level_ups += award.kind == "level_up"
        self.history.append(ev)
        if item.kind == "mcq":
            self.seen_mcq.add(item.id)
        return is_solved(ev)

    @property
    def budget_left(self) -> bool:
        return len(self.history) < STEPS


def make_bank(rng: random.Random) -> list[Item]:
    items, next_id = [], 1
    for topic in TOPICS:
        for kind, count in BANK.items():
            for _ in range(count):
                items.append(Item(next_id, kind, topic, rng.uniform(0.1, 0.9)))
                next_id += 1
    return items


def next_item(run: Run, bank: list[Item], turn: int) -> Item | None:
    open_items = [i for i in bank if i.id not in run.solved]
    if not open_items:
        return None
    topic = min(TOPICS, key=lambda t: (run.mastery[t], TOPICS.index(t)))
    m = run.mastery[topic]
    wanted = "mcq" if m < WEAK_BELOW else ("code" if m >= MASTERED_FROM
                                           else ("code", "debug")[turn % 2])
    for pick in ([i for i in open_items if i.topic == topic and i.kind == wanted],
                 [i for i in open_items if i.topic == topic],
                 open_items):
        if pick:
            return min(pick, key=lambda i: i.difficulty)
    return None


def attempt_honest(run: Run, item: Item) -> None:
    if item.kind == "mcq":
        correct = item.id in run.seen_mcq or run.rng.random() < run.p_solve(item)
        if run.record(item, 1.0 if correct else 0.0):
            run.solved.add(item.id)
        return
    for hint in range(0, 5 if item.kind == "code" else 3):
        if not run.budget_left:
            return
        level = hint if item.kind == "code" else 0
        ok = run.rng.random() < run.p_solve(item, level)
        score = code_score(int(ok), 1, level) if item.kind == "code" else debug_score(ok, 0, 1)
        if run.record(item, score, level):
            run.solved.add(item.id)
            return


def attempt_hint_spammer(run: Run, item: Item) -> None:
    if item.kind != "code":
        return attempt_honest(run, item)
    while run.budget_left:
        ok = run.rng.random() < run.p_solve(item, 4)
        run.record(item, code_score(1 if ok else 0, 1, 4), 4)
        if ok:
            run.solved.add(item.id)
            return


def attempt_resubmitter(run: Run, item: Item) -> None:
    attempt_honest(run, item)
    if item.id in run.solved:
        for _ in range(5):
            if run.budget_left:
                run.record(item, 1.0)


def attempt_fail_on_purpose(run: Run, item: Item) -> None:
    if item.kind == "code":
        for _ in range(2):
            if run.budget_left:
                run.record(item, 0.0)
    if run.budget_left:
        attempt_honest(run, item)


def attempt_mcq_guesser(run: Run, item: Item) -> None:
    if item.kind != "mcq":
        return attempt_honest(run, item)
    correct = item.id in run.seen_mcq or run.rng.random() < 1 / MCQ_OPTIONS
    if run.record(item, 1.0 if correct else 0.0):
        run.solved.add(item.id)


STRATEGIES = {
    "honest": attempt_honest,
    "hint_spammer": attempt_hint_spammer,
    "resubmitter": attempt_resubmitter,
    "fail_on_purpose": attempt_fail_on_purpose,
    "mcq_guesser": attempt_mcq_guesser,
    "chat_copier": None,
}


def simulate(strategy: str, ability: dict[str, float], seed: int) -> Run:
    rng = random.Random(seed)
    bank = make_bank(random.Random(seed * 7919))
    run = Run(ability=ability, rng=rng)
    act = STRATEGIES[strategy]
    if act is None:
        return run
    turn = 0
    while run.budget_left:
        item = next_item(run, bank, turn)
        if item is None:
            break
        act(run, item)
        turn += 1
    return run


def ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    out = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        for k in range(i, j + 1):
            out[order[k]] = (i + j) / 2
        i = j + 1
    return out


def spearman(x: list[float], y: list[float]) -> float:
    rx, ry = ranks(x), ranks(y)
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    cov = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    sx = math.sqrt(sum((a - mx) ** 2 for a in rx))
    sy = math.sqrt(sum((b - my) ** 2 for b in ry))
    return cov / (sx * sy) if sx and sy else 0.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--students", type=int, default=200)
    args = parser.parse_args()

    pop = random.Random(args.seed)
    students = [{t: pop.uniform(0.1, 0.95) for t in TOPICS} for _ in range(args.students)]

    print(f"## Gaming resistance ({args.students} students, {STEPS} events each)\n")
    print("| strategy | points | vs honest | badges | level-ups | items solved | final mastery |")
    print("|---|---|---|---|---|---|---|")
    honest_points = None
    for name in STRATEGIES:
        runs = [simulate(name, a, args.seed + i) for i, a in enumerate(students)]
        n = len(runs)
        pts = sum(r.points for r in runs) / n
        honest_points = pts if name == "honest" else honest_points
        ratio = pts / honest_points if honest_points else 0.0
        print(f"| {name} | {pts:.1f} | {ratio:.2f} | {sum(r.badges for r in runs) / n:.2f} | "
              f"{sum(r.level_ups for r in runs) / n:.2f} | {sum(len(r.solved) for r in runs) / n:.1f} | "
              f"{sum(sum(r.mastery.values()) / len(TOPICS) for r in runs) / n:.3f} |")

    runs = [simulate("honest", a, args.seed + i) for i, a in enumerate(students)]
    mean_ability = [sum(a.values()) / len(TOPICS) for a in students]
    print("\n## Award validity (honest students, known ability)\n")
    print("| award | Spearman rho with true ability |")
    print("|---|---|")
    print(f"| points | {spearman(mean_ability, [r.points for r in runs]):.2f} |")
    print(f"| level-ups | {spearman(mean_ability, [r.level_ups for r in runs]):.2f} |")
    mastered = [sum(1 for k in r.keys if k.endswith(':mastered')) for r in runs]
    print(f"| topics mastered | {spearman(mean_ability, mastered):.2f} |")


if __name__ == "__main__":
    main()
