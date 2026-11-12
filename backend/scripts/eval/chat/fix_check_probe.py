"""Fix-check probe: how often the hint judge (guardrail.states_fix) catches a hint that
gives the fix away, and how often it wrongly blocks a real hint.

    python -m scripts.eval.chat.fix_check_probe [--out DIR]

One hint_check gateway call per row (20), logged to llm_calls, so it needs the local
database. block_rate is recall on leaks; false_block_rate is over the real hints. Rows
whose judge call failed are counted as unavailable and left out of both rates."""

from app.core.exceptions import LLMUnavailable
from app.features.hints.logic.guardrail import states_fix
from scripts._local_db import require_local_db
from scripts.eval.chat.results import Results, parser, pending
from scripts.eval.chat.scoring import load_jsonl, moderation_summary

FIELDS = {"id": str, "label": str, "level": int, "statement": str, "language": str,
          "code": str, "hint": str}


def main(argv=None) -> None:
    args = parser(__doc__.splitlines()[0], "fix_check", "fix_check.jsonl").parse_args(argv)
    require_local_db()
    rows = load_jsonl(args.data, FIELDS, {"label": ("leak", "ok")})
    results = Results(args.out)
    results.reset()
    for row in pending(rows, set(), ids=args.ids, limit=args.limit):
        try:
            flagged = states_fix(row["hint"], statement=row["statement"],
                                 language=row["language"], code=row["code"])
        except LLMUnavailable:
            flagged = None
        results.append({"id": row["id"], "label": "flag" if row["label"] == "leak" else "allow",
                        "kind": f"L{row['level']}", "flagged": flagged, "hint": row["hint"]})
    judged = [r for r in results.rows() if r["flagged"] is not None]
    results.finish({**moderation_summary(judged), "unavailable": len(results.rows()) - len(judged)})


if __name__ == "__main__":
    main()
