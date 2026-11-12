"""Moderation probe: block rate on messages that must be flagged, and false-block rate on
programming, Hinglish, frustrated and off-topic messages that must get through.

    python -m scripts.eval.chat.moderation_probe [--out DIR]

Runs moderation.check only: no DB, no LLM, free. Every run starts over, so the numbers
always reflect the current term list."""

from app.features.chat.logic import moderation
from scripts.eval.chat.results import Results, parser, pending
from scripts.eval.chat.scoring import load_moderation, moderation_summary


def main(argv=None) -> None:
    args = parser(__doc__.splitlines()[0], "moderation", "moderation_probe.jsonl").parse_args(argv)
    rows = load_moderation(args.data)
    results = Results(args.out)
    results.reset()
    for row in pending(rows, set(), ids=args.ids, limit=args.limit):
        verdict = moderation.check(row["text"])
        results.append({"id": row["id"], "label": row["label"], "kind": row.get("kind"),
                        "flagged": verdict.flagged, "category": verdict.category,
                        "text": row["text"]})
    results.finish(moderation_summary(results.rows()))


if __name__ == "__main__":
    main()
