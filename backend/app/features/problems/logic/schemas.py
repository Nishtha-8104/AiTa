from pydantic import BaseModel, Field

MAX_HINTS = 2


class ProblemDraft(BaseModel):
    """What the model is asked for when the bank has nothing to offer.

    Under structured output these descriptions are the only instructions the model
    reads for each field, so the rules live here rather than in the prompt.
    """

    title: str = Field(
        description="A short name for the problem, at most six words, with no "
                    "difficulty label and no numbering"
    )
    statement: str = Field(
        description="The problem itself, describing exactly ONE test case: what the "
                    "program reads from standard input and what it prints to standard "
                    "output. Three to six sentences. Never mention a number of test "
                    "cases, and never show the answer or the algorithm."
    )
    constraints: list[str] = Field(
        default_factory=list,
        description="Bounds on the input, one per entry, such as '1 <= n <= 1000'. "
                    "Keep every bound small enough that a plain Python 3 solution "
                    "finishes in under a second.",
    )
    hints: list[str] = Field(
        default_factory=list,
        description="Exactly two entries, each one sentence, each with a fixed job. "
                    "The first names the data structure or idea the problem turns on "
                    "and stops there — name it, do not say what to do with it. The "
                    "second states the single observation or invariant that makes the "
                    "problem tractable, as a fact about the input or about the answer. "
                    "Neither entry describes a procedure: no steps, no ordering, no "
                    "'first ... then ...', no loops, no pointer or window movement, "
                    "no complexity claim, no code. Four hints that read in sequence "
                    "are a walkthrough and are wrong here.",
    )
