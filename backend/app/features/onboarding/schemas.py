"""Onboarding requests and responses. Answer fields are size-capped here; the tighter
theory cap needs the item's kind, so the service checks that one."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

CODE_CAP = 4000
THEORY_CAP = 2000
MS_CAP = 3_600_000

Step = Literal["welcome", "language", "about", "learning"]
TopicState = Literal["unknown", "asking", "strong", "ok", "needs_work", "inferred", "skipped"]


class _Closed(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WelcomeIn(_Closed):
    pass


class LanguageIn(_Closed):
    language: Literal["c", "cpp", "python"]


class SwitchOut(BaseModel):
    language: str
    needs_check: bool


class RecheckOut(BaseModel):
    language: str
    bands: dict[str, str]
    title: str


class AboutIn(_Closed):
    year_of_study: int | None = Field(None, ge=1, le=6)
    program: str | None = Field(None, max_length=100)
    institution: str | None = Field(None, max_length=255)
    experience: Literal["none", "lt6m", "6to12m", "1to2y", "2yplus"]
    goal: Literal["course", "placements", "competitive", "hobby"]


class LearningIn(_Closed):
    explanation_style: Literal["step_by_step", "short"]
    example_order: Literal["examples_first", "concept_first"]
    chat_language: Literal["english", "hinglish"]
    hours_per_week: Literal["lt2", "2to5", "5to10", "10plus"]
    self_rating: int = Field(ge=1, le=5)


STEP_MODELS: dict[str, type[BaseModel]] = {
    "welcome": WelcomeIn, "language": LanguageIn, "about": AboutIn, "learning": LearningIn,
}


class AnswerBody(_Closed):
    """predict_output and fill_blank: text; find_bug: line + fix_code; write_code: code;
    theory: text."""

    text: str | None = Field(None, max_length=CODE_CAP)
    line: int | None = Field(None, strict=True)
    fix_code: str | None = Field(None, max_length=CODE_CAP)
    code: str | None = Field(None, max_length=CODE_CAP)


class AnswerIn(BaseModel):
    item_id: int
    answer: AnswerBody
    ms_taken: int = Field(ge=0, le=MS_CAP)


class ProfilePatch(_Closed):
    about: AboutIn | None = None
    learning: LearningIn | None = None


class DiagOut(BaseModel):
    item: dict | None
    order: int
    remaining: int
    topic_map: dict[str, TopicState]
    phase: str | None
    done: bool


class TheoryReveal(BaseModel):
    item_id: int
    topic: str
    question: str
    score: float | None
    reveal: dict | None
    feedback: str | None


class AnswerOut(BaseModel):
    reveal: dict | None
    score: float | None = None
    saved_only: bool
    theory_reveals: list[TheoryReveal] = []
    topic_map: dict[str, TopicState]
    next: DiagOut


class CardOut(BaseModel):
    bands: dict[str, str]
    inferred: list[str]
    concept_level: str
    title: str
    start_topic: str
    start_reason: str
    preferences: dict
    theory_pending: bool


class StateOut(BaseModel):
    current_step: str
    answers: dict
    diagnostic: DiagOut | None
    card: CardOut | None
