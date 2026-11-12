"""Which tools the pet agent picks for labelled student messages.

    DATABASE_URL=postgresql://pet:pet@localhost:5433/pet_db \\
        python -m scripts.eval.chat.tool_choice_eval [--out DIR] [--limit N] [--ids a,b]

Refuses to run against a non-local database. --ids reruns those ids even if done.

Each query is the first message of a new pet thread on the eval account, and the tools
the agent calls in that turn are compared with expected_tools: exact-set accuracy,
first-tool accuracy, per-tool precision and recall (with "none" for no tool), and a
confusion table. The tools really run, so evaluate_code and get_hint need the executor
and may make their own LLM calls (tests for pasted problems, hints). Spends free-tier LLM
calls: run it on purpose."""

from app.core.database import SessionLocal
from scripts.eval.chat import harness
from scripts.eval.chat.results import Results, parser, pending
from scripts.eval.chat.scoring import first_tool_ok, load_tool_choice, tool_choice_summary, tool_label

EMAIL = "chat-eval-tools@example.com"


def main(argv=None) -> None:
    p = parser(__doc__.splitlines()[0], "tool_choice", "tool_choice.jsonl")
    p.add_argument("--email", default=EMAIL, help="eval account (created if missing)")
    args = p.parse_args(argv)
    harness.require_local_db()

    rows = load_tool_choice(args.data)
    results = Results(args.out)
    todo = pending(rows, results.done(), ids=args.ids, limit=args.limit)
    print(f"{len(todo)} of {len(rows)} queries to run -> {results.dir}")

    with SessionLocal() as db:
        user = harness.eval_user(db, args.email)
        for n, row in enumerate(todo, 1):
            thread = harness.new_thread(db, user.id, "pet")
            turn = harness.ask(db, user.id, thread, row["query"], row["language"])
            if turn.failed:
                print(f"[{n}/{len(todo)}] {row['id']}: turn failed ({turn.flag or turn.error}); "
                      "left for the next run")
                continue
            results.append({
                "id": row["id"], "language": row["language"], "query": row["query"],
                "expected": row["expected_tools"], "called": turn.tools,
                "exact": tool_label(row["expected_tools"]) == tool_label(turn.tools),
                "first_tool_ok": first_tool_ok(row["expected_tools"], turn.tools),
                "tool_calls": turn.tool_calls, "flag": turn.flag,
                "reply": harness.clip(turn.content),
            })
            print(f"[{n}/{len(todo)}] {row['id']}: expected={row['expected_tools']} "
                  f"called={turn.tools}")

    results.finish(tool_choice_summary(results.rows()))


if __name__ == "__main__":
    main()
