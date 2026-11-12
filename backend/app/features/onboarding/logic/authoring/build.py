"""Offline generation of the diagnostic bank: per topic, one Python draft call and one
C/C++ port call, then every variant verified by execution.

Raw replies are cached, so re-running re-parses and re-verifies without spending."""

from collections import Counter

from app.core import llm_gateway
from app.features.grading.logic.execution.base import ExecutionProvider
from app.features.onboarding.logic.authoring import parse, prompts, verify
from app.features.practice.logic.assessment.generation import RawCache


def ask_model(prompt: str) -> str:
    message = llm_gateway.invoke("assessment_gen", prompt).value
    return getattr(message, "content", message) or ""


def keep_verified(items: list[dict], provider: ExecutionProvider | None,
                  log: Counter) -> list[dict]:
    """The first item of each concept and language that passes verification."""
    kept, done = [], set()
    for item in items:
        if (item["concept_key"], item["language"]) in done:
            continue
        result = verify.check(item, provider)
        label = f"{item['language']} {item['kind']}"
        if not result.ok:
            log[f"dropped {label}: {result.reason}"] += 1
            continue
        if result.reason:
            log[result.reason] += 1
        log[f"kept {label}"] += 1
        kept.append(result.item)
        done.add((item["concept_key"], item["language"]))
    return kept


def generate(cache: RawCache, provider: ExecutionProvider | None = None,
             ask=ask_model) -> dict:
    log: Counter = Counter()
    items: list[dict] = []
    for topic in parse.TOPICS:
        raw = cache.get(f"draft:{topic}", lambda t=topic: ask(prompts.draft(t)))
        drafted = parse.parse_topic_draft(raw, topic, log)
        if not drafted:
            log[f"unparseable draft: {topic}"] += 1
            continue
        kept = keep_verified(drafted, provider, log)
        items += kept

        to_port = [item for item in kept if item["language"] == "python"]
        if not to_port:
            continue
        raw = cache.get(f"port:{topic}", lambda t=topic, p=to_port: ask(prompts.port(t, p)))
        for language, variants in parse.parse_port(raw, to_port).items():
            ported = keep_verified(variants, provider, log)
            if len(ported) < len(to_port):
                log[f"port missing {language}: {topic}"] += len(to_port) - len(ported)
            items += ported
    return {"items": items, "log": log}
