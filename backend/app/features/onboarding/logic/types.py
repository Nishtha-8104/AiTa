"""Value types shared by the onboarding walk, graders, seeding and service."""

from dataclasses import dataclass

BankIndex = frozenset[tuple[str, str, str]]


@dataclass(frozen=True)
class ItemRef:
    topic: str
    kind: str
    difficulty: str
    phase: str


@dataclass(frozen=True)
class Resp:
    ref: ItemRef
    score: float | None
    graded_by: str


@dataclass(frozen=True)
class Ask:
    ref: ItemRef


@dataclass(frozen=True)
class Done:
    pass


@dataclass(frozen=True)
class Grade:
    score: float | None
    graded_by: str
    reveal: dict
    feedback: str | None = None


@dataclass(frozen=True)
class Seed:
    value: float
    source: str


@dataclass(frozen=True)
class Card:
    bands: dict[str, str]
    inferred: list[str]
    concept_level: str
    title: str
    start_topic: str
    start_reason: str
    preferences: dict
