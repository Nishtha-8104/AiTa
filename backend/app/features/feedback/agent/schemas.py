from pydantic import BaseModel, Field


class FeedbackNarrative(BaseModel):
    """The synthesised narrative, one field per column the report persists.

    The descriptions are the guidance the model actually reads under structured
    output, so the rules live here rather than in the prompt.
    """

    headline: str = Field(
        description="One-line overall verdict, at most about 120 characters"
    )
    summary: str = Field(
        description="Three or four sentences narrating what the student did and where "
                    "they stand, in language suited to their skill level"
    )
    strengths: list[str] = Field(
        default_factory=list,
        description="Specific things the student did well, not generic praise",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="Each mistake followed by why it matters for learning, never just "
                    "that something is wrong",
    )
    misconceptions: list[str] = Field(
        default_factory=list,
        description="Conceptual misunderstandings the work reveals",
    )
    action_items: list[str] = Field(
        default_factory=list,
        description="Two to four concrete tasks, each doable in one 30-minute session",
    )
    concept_map: dict[str, float] = Field(
        default_factory=dict,
        description="Concept name to an estimate of the student's current understanding, "
                    "each value between 0.0 and 1.0",
    )
    next_topics: list[str] = Field(
        default_factory=list,
        description="Two or three topics to study next, in order",
    )
    motivational: str = Field(
        default="",
        description="One encouraging sentence personal to this student, not generic",
    )
