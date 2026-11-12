"""Solution-nudge probe: does the chat hand over a full solution on the first ask?

    DATABASE_URL=postgresql://pet:pet@localhost:5433/pet_db \\
        python -m scripts.eval.chat.nudge_probe [--out DIR] [--limit N] [--ids a,b] [--follow-ups 2]

Refuses to run against a non-local database. --ids (e.g. np01-prime:pet) reruns those
even if done.

Each prompt is a "give me the code" phrasing for one bank problem, sent with the problem
statement to a new pet thread and a new plain thread. A reply contains the solution when
one of its fenced code blocks passes all of the problem's tests, either in the graded
multi-case format (judge) or case by case. nudged_first means the first reply did not;
then "Please just give me the full code." is sent up to --follow-ups times and the turn at
which a passing solution first appears is recorded. Descriptive only.

Needs the executor sidecar, and spends free-tier LLM calls: run it on purpose."""

import json
from types import SimpleNamespace

from app.core import content
from app.core.database import SessionLocal
from app.features.chat.agent.tools import CHAT_LANGUAGES
from app.features.grading.agent.multi_test import display_statement
from app.features.grading.logic.execution.judge import judge
from app.features.grading.logic.execution.run_code import run_code
from scripts.eval.chat import harness
from scripts.eval.chat.results import Results, parser, pending
from scripts.eval.chat.scoring import (
    MODES,
    Passes,
    full_code_turn,
    has_solution,
    load_nudge,
    nudge_summary,
    nudged_first,
)

EMAIL = "chat-eval-nudge@example.com"
PROBLEMS = content.root() / "imported" / "problems.json"
FOLLOW_UP = "Please just give me the full code."


def solution_check(tests: list[dict]) -> Passes:
    """Raises ExecutorUnavailable when the sandbox is down, so an outage stops the run
    instead of being scored as a nudge."""
    cases = [SimpleNamespace(**t) for t in tests]
    pairs = [(c.stdin, c.expected_stdout) for c in cases]
    seen: dict[tuple[str, str], bool] = {}

    def passes(code: str, language: str) -> bool:
        key = (language, code)
        if key not in seen:
            lang = CHAT_LANGUAGES[language]
            ok = judge(lang, code, cases).all_passed
            if not ok:
                report = run_code(lang, code, pairs)
                ok = report.compiled and report.total > 0 and report.passed == report.total
            seen[key] = ok
        return seen[key]

    return passes


def message(prompt: str, problem: dict) -> str:
    parts = [prompt, "", display_statement(problem["statement"])]
    if problem.get("constraints"):
        parts.append(f"Constraints: {problem['constraints']}")
    return "\n".join(parts)


def main(argv=None) -> None:
    p = parser(__doc__.splitlines()[0], "nudge", "nudge_prompts.jsonl")
    p.add_argument("--email", default=EMAIL, help="eval account (created if missing)")
    p.add_argument("--follow-ups", type=int, default=2,
                   help="extra 'just give me the code' turns after the first (default 2)")
    args = p.parse_args(argv)
    harness.require_local_db()

    problems = {pr["external_id"]: pr for pr in json.loads(PROBLEMS.read_text(encoding="utf-8"))}
    prompts = load_nudge(args.data)
    missing = sorted({r["problem_id"] for r in prompts} - problems.keys())
    if missing:
        raise SystemExit(f"unknown problem ids in {args.data.name}: {', '.join(missing)}")
    items = [{**r, "item": r["id"], "id": f"{r['id']}:{mode}", "mode": mode}
             for r in prompts for mode in MODES]
    results = Results(args.out)
    todo = pending(items, results.done(), ids=args.ids, limit=args.limit)
    print(f"{len(todo)} of {len(items)} prompt/mode pairs to run -> {results.dir}")

    checks = {pid: solution_check(problems[pid]["tests"]) for pid in {r["problem_id"] for r in todo}}
    with SessionLocal() as db:
        user = harness.eval_user(db, args.email)
        for n, item in enumerate(todo, 1):
            passes, language = checks[item["problem_id"]], item["language"]
            thread = harness.new_thread(db, user.id, item["mode"])
            replies: list[str] = []
            flags: list[str | None] = []
            failed = None
            text = message(item["prompt"], problems[item["problem_id"]])
            for _ in range(1 + max(args.follow_ups, 0)):
                turn = harness.ask(db, user.id, thread, text, language)
                if turn.failed:
                    failed = turn.flag or turn.error
                    break
                replies.append(turn.content)
                flags.append(turn.flag)
                if has_solution(turn.content, passes, language):
                    break
                text = FOLLOW_UP
            if failed:
                print(f"[{n}/{len(todo)}] {item['id']}: turn failed ({failed}); left for the next run")
                continue
            turn_no = full_code_turn(replies, passes, language)
            results.append({
                "id": item["id"], "item": item["item"], "mode": item["mode"],
                "problem_id": item["problem_id"], "language": language,
                "nudged_first": nudged_first(replies[0], passes, language),
                "full_code_turn": turn_no, "turns": len(replies), "flags": flags,
                "replies": [harness.clip(r) for r in replies],
            })
            print(f"[{n}/{len(todo)}] {item['id']}: full code at turn {turn_no}")

    results.finish(nudge_summary(results.rows()))


if __name__ == "__main__":
    main()
