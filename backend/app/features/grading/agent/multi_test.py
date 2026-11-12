"""Competitive-programming input format.

The student's program is run ONCE. Its stdin is a test count followed by that many
sub-case blocks, and it is expected to loop over them. Scoring is still per sub-case:
we know each sub-case's expected output, so the single output stream is split back
apart by line count and each sub-case judged on its own.

Generation and cross-checking stay per sub-case — a sub-case is validated by feeding
the reference a batch of exactly one.
"""

from pydantic import BaseModel

from app.core.text import normalize_output

MULTI_TEST_PREAMBLE = (
    "The first line of input contains an integer T, the number of test cases. "
    "T test cases follow, each in the format described below. Print the answer for "
    "every test case, in order."
)


def display_statement(statement: str | None) -> str | None:
    """What the student should actually read.

    Stored statements describe ONE test case, because that is what the generator is
    asked for and what each test case block contains. The batch convention lives here
    rather than in the stored text, so seeded problems stay correct without rewriting
    them (which would change their hash and orphan their test cases).
    """
    if not statement:
        return statement
    return f"{MULTI_TEST_PREAMBLE}\n\n{statement}"


class SubCaseResult(BaseModel):
    ordinal: int
    kind: str
    stdin: str
    expected_stdout: str
    actual_stdout: str
    passed: bool
    rationale: str | None = None


class SplitReport(BaseModel):
    results: list[SubCaseResult]
    passed: int
    total: int
    extra_output: bool
    missing_output: bool

    @property
    def first_failing(self) -> SubCaseResult | None:
        return next((r for r in self.results if not r.passed), None)

    @property
    def produced_nothing(self) -> bool:
        """The program ran but printed nothing at all.

        Worth separating from a wrong answer: "Wrong answer on test 1" sends a
        student hunting a logic bug in the first case, when the real story is that
        their program never printed anything - usually a loop that never ran.
        """
        return bool(self.results) and all(not r.actual_stdout for r in self.results)


def _kind(case) -> str:
    """`kind` arrives as a TestCaseKind enum from the ORM and as a plain string from
    generated cases, so unwrap whichever it is."""
    kind = getattr(case, "kind", None)
    if kind is None:
        return "normal"
    return getattr(kind, "value", kind)


def _lines(text: str) -> list[str]:
    normalised = normalize_output(text or "")
    return normalised.split("\n") if normalised else []


def _block(stdin: str) -> str:
    """A sub-case block must end in a newline or the next block runs into it."""
    if not stdin:
        return "\n"
    return stdin if stdin.endswith("\n") else stdin + "\n"


def merge_cases(cases) -> tuple[str, str]:
    """Build the single stdin the student's program receives, and the full expected
    output it should print. `cases` is any sequence with .stdin and .expected_stdout."""
    stdin = f"{len(cases)}\n" + "".join(_block(c.stdin) for c in cases)
    expected = "\n".join(normalize_output(c.expected_stdout or "") for c in cases)
    return stdin, expected


def split_actual(actual: str, cases) -> SplitReport:
    """Cut one output stream back into per-sub-case verdicts.

    Alignment is positional: each sub-case consumes as many lines as its expected
    output has. A student who prints one stray line early therefore fails everything
    after it — which is correct, since their output genuinely is wrong, but the hint
    needs to say so rather than leave them hunting a logic bug.
    """
    actual_lines = _lines(actual)
    cursor = 0
    results: list[SubCaseResult] = []

    for index, case in enumerate(cases, start=1):
        expected_lines = _lines(case.expected_stdout or "")
        chunk = actual_lines[cursor:cursor + len(expected_lines)]
        # A sub-case expecting no output cannot be judged positionally; treat the
        # absence of extra lines as a pass.
        passed = chunk == expected_lines
        results.append(SubCaseResult(
            ordinal=index,
            kind=_kind(case),
            stdin=case.stdin,
            expected_stdout="\n".join(expected_lines),
            actual_stdout="\n".join(chunk),
            passed=passed,
            rationale=getattr(case, "rationale", None),
        ))
        cursor += len(expected_lines)

    return SplitReport(
        results=results,
        passed=sum(1 for r in results if r.passed),
        total=len(results),
        extra_output=cursor < len(actual_lines),
        missing_output=cursor > len(actual_lines),
    )


def all_failed(cases, actual: str = "") -> SplitReport:
    """Every sub-case fails — the run crashed, timed out, or never compiled."""
    results = [
        SubCaseResult(
            ordinal=index,
            kind=_kind(case),
            stdin=case.stdin,
            expected_stdout=normalize_output(case.expected_stdout or ""),
            actual_stdout="",
            passed=False,
            rationale=getattr(case, "rationale", None),
        )
        for index, case in enumerate(cases, start=1)
    ]
    return SplitReport(results=results, passed=0, total=len(results),
                       extra_output=False, missing_output=bool(actual))


def verdict_for(status: str, split: SplitReport | None) -> str:
    """A Codeforces-style one-liner: the thing a competitive programmer reads first."""
    if status == "compile_error":
        return "Compilation error"
    if status == "timeout":
        return "Time limit exceeded"
    if status == "memory_exceeded":
        return "Memory limit exceeded"
    if status == "runtime_error":
        return "Runtime error"
    if split is None or split.total == 0:
        return "No tests run"
    failing = split.first_failing
    if failing is None:
        return "Accepted" if not split.extra_output else "Wrong answer (extra output)"
    if split.produced_nothing:
        return "No output"
    return f"Wrong answer on test {failing.ordinal}"
