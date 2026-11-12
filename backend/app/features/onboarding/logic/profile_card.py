"""The profile reveal card shown after the diagnostic. Pure: no LLM, no points."""

from app.core.topics import TOPICS
from app.features.onboarding.logic.seeding import SEED_VALUES, tier_level
from app.features.onboarding.logic.types import Card, Seed

TITLES = ["Fresh Starter", "Syntax Scout", "Loop Wrangler", "Array Ace", "Recursion Ranger",
          "Algorithm Architect"]
NOT_CHECKED = "not_checked"
START_REASONS = {
    "needs_work": "The check showed some gaps here, and the topics it builds on are in place.",
    NOT_CHECKED: "The check didn't reach this topic yet, and the topics it builds on are in place.",
    "inferred": "Your other answers suggest you know the basics here, so practice will confirm them.",
    "ok": "You have the basics here, and it is the least solid of the topics open to you.",
    "strong": "You did well across the board, so practice picks up from here.",
}


def band_of(seed: Seed | None) -> str:
    if seed is None:
        return NOT_CHECKED
    if seed.source == "inferred":
        return "ok"
    if seed.value >= SEED_VALUES["strong"]:
        return "strong"
    return "ok" if seed.value >= SEED_VALUES["ok"] else "needs_work"


def title_for(seeds: dict[str, Seed]) -> str:
    return TITLES[tier_level(seeds)]


def build(seeds: dict[str, Seed], concept: str, prefs: dict, start_topic: str) -> Card:
    inferred = [t for t in TOPICS if t in seeds and seeds[t].source == "inferred"]
    bands = {t: band_of(seeds.get(t)) for t in TOPICS}
    return Card(
        bands=bands,
        inferred=inferred,
        concept_level=concept,
        title=title_for(seeds),
        start_topic=start_topic,
        start_reason=START_REASONS["inferred" if start_topic in inferred else bands[start_topic]],
        preferences=prefs,
    )
