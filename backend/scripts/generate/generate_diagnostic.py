"""Run once, inside the backend container (the Sandbox is on an internal network):

    docker compose exec backend \\
        python -m scripts.generate.generate_diagnostic

Writes content/topics/<topic>/diagnostic.json. Raw model replies are cached in
content/_drafts/diagnostic_raw.json; pass --refresh to pay for new drafts, --refresh-key
draft:loops to redraft one topic (its port is redone too, since concept keys follow the
draft), or --refresh-key port:loops to redo only that topic's C/C++ port."""

import argparse
from collections import Counter

from app.core import content
from app.features.onboarding.logic import content as bank_file
from app.features.onboarding.logic.authoring.build import generate
from app.features.onboarding.logic.authoring.parse import CODE_KINDS, TOPICS
from app.features.onboarding.logic.bank import LANGUAGES, SHARED
from app.features.practice.logic.assessment.generation import RawCache


def gaps(items: list[dict]) -> list[str]:
    found = []
    for topic in TOPICS:
        for language in LANGUAGES:
            mine = [i for i in items if i["topic"] == topic and i["language"] in (language, SHARED)]
            if not any(i["kind"] in CODE_KINDS and i["difficulty"] == "medium" for i in mine):
                found.append(f"{topic} {language}: no medium code item")
            if not any(i["kind"] == "predict_output" and i["difficulty"] == "easy" for i in mine):
                found.append(f"{topic} {language}: no easy predict_output item")
            if not any(i["kind"] == "theory" for i in mine):
                found.append(f"{topic} {language}: no theory item")
    return found


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--refresh-key", action="append", default=[],
                        help="redraft one cached reply, e.g. draft:loops or port:loops")
    args = parser.parse_args()

    cache = RawCache(content.root() / "_drafts" / "diagnostic_raw.json", refresh=args.refresh)
    for key in args.refresh_key:
        cache.data.pop(key, None)
        if key.startswith("draft:"):
            cache.data.pop(f"port:{key.removeprefix('draft:')}", None)
    result = generate(cache)

    items = result["items"]
    bank_file.save(items)
    print(f"items={len(items)}")
    for (kind, language), count in sorted(Counter((i["kind"], i["language"]) for i in items).items()):
        print(f"  {count:3d}  {kind} {language}")
    for reason, count in sorted(result["log"].items()):
        print(f"  {count:3d}  {reason}")
    for gap in gaps(items):
        print(f"  gap: {gap}")


if __name__ == "__main__":
    main()
