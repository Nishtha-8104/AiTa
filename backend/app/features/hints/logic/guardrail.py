"""A hint that contains the answer is not a hint. Every code block in a reply is run
against the problem's tests: if it passes them, it was the solution, and it is blocked.
Prose is checked too, statically: quoting a distinctive line of the reference solution
blocks the reply. A fix told in plain words is left to states_fix, an LLM judge."""

import re
from dataclasses import dataclass

from pydantic import BaseModel

from app.core import llm_gateway
from app.core.exceptions import ExecutorUnavailable
from app.features.grading.logic.execution.judge import judge
from app.features.grading.models import Language
from app.features.hints.logic.prompts import FIX_CHECK_PROMPT

_FENCE = re.compile(r"```[^\n]*\n(.*?)(?:```|$)", re.DOTALL)


def max_code_lines(level: int) -> int:
    return 2 if level >= 4 else 3


@dataclass(frozen=True)
class GuardVerdict:
    blocked: bool
    reason: str | None = None


def code_blocks(text: str) -> list[str]:
    return [block for block in _FENCE.findall(text or "") if block.strip()]


def _lines(block: str) -> int:
    return sum(1 for line in block.splitlines() if line.strip())


def _passes_tests(block: str, language: Language, test_cases, provider) -> bool:
    try:
        return judge(language, block, test_cases, provider).all_passed
    except ExecutorUnavailable:
        return False


_BOILERPLATE = re.compile(
    r"^(import|from|def|return|print\(|sys\.|out\.|else:|try:|except|if__name__|"
    r"for_inrange\(int\(|while|break|continue|pass)"
)
_READER_HELPERS = ("rd()", "_pos", "_data", "input()", "readline")
MIN_DISTINCTIVE = 10


def _squash(text: str) -> str:
    return re.sub(r"\s+", "", text or "")


def distinctive_lines(reference: str, student_code: str = "") -> set[str]:
    """Reference lines specific enough that quoting one gives the answer away: long
    enough to be more than a keyword, not I/O plumbing, and not something the student
    already wrote themselves."""
    own = {_squash(line) for line in (student_code or "").splitlines()}
    lines = set()
    for line in (reference or "").splitlines():
        squashed = _squash(line)
        if (len(squashed) >= MIN_DISTINCTIVE and squashed not in own
                and not _BOILERPLATE.match(squashed)
                and not any(h in squashed for h in _READER_HELPERS)):
            lines.add(squashed)
    return lines


def quotes_reference(text: str, references, student_code: str = "") -> bool:
    squashed = _squash(text)
    return any(line in squashed
               for reference in references or ()
               for line in distinctive_lines(reference, student_code))


class FixVerdict(BaseModel):
    change: str = ""
    states_fix: bool


def states_fix(hint: str, *, statement: str, language: str, code: str,
               user_id: int | None = None) -> bool:
    """Raises LLMUnavailable when the judge cannot run; an unparsed verdict counts as a
    leak, so a hint is only shown once it has been cleared."""
    prompt = FIX_CHECK_PROMPT.format(statement=statement, language=language, code=code,
                                     hint=hint)
    verdict = llm_gateway.invoke("hint_check", prompt, schema=FixVerdict, user_id=user_id).value
    return verdict is None or verdict.states_fix


_CODE_STARTS = ("for (", "while (", "if (", "def ", "return ", "#include", "elif ", "else:",
                "print(")
_CODE_ENDS = (";", "{", "}")
_LIST_ITEM = re.compile(r"^([-*•]|\d+[.)])\s")


def _code_like(line: str) -> bool:
    line = line.strip()
    return bool(line) and (
        line.endswith(_CODE_ENDS) or line.startswith(_CODE_STARTS)
        or (line.startswith("for ") and " in " in line)
        or (line.startswith("while ") and line.endswith(":")))


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip())


def _opens_block(header: str, body: str) -> bool:
    return (header.rstrip().endswith(":") and _indent(body) > _indent(header)
            and not _LIST_ITEM.match(body.strip()))


def check_multi_item(text: str, references: list[str]) -> GuardVerdict:
    """Feedback across many items has no single problem to run code against, so no
    code is allowed at all."""
    if code_blocks(text):
        return GuardVerdict(True, "code_block")
    lines = [line for line in (text or "").splitlines() if line.strip()]
    if any((_code_like(a) and _code_like(b)) or _opens_block(a, b)
           for a, b in zip(lines, lines[1:])):
        return GuardVerdict(True, "code_lines")
    if quotes_reference(text, references):
        return GuardVerdict(True, "quotes_reference")
    return GuardVerdict(False)


def check(text: str, level: int, language: Language, test_cases, provider=None, *,
          references=(), student_code: str = "") -> GuardVerdict:
    if quotes_reference(text, references, student_code):
        return GuardVerdict(True, "quotes_reference")
    blocks = code_blocks(text)
    if not blocks:
        return GuardVerdict(False)
    if sum(_lines(b) for b in blocks) > max_code_lines(level):
        return GuardVerdict(True, "too_much_code")
    if test_cases and any(_passes_tests(b, language, test_cases, provider) for b in blocks):
        return GuardVerdict(True, "passes_tests")
    return GuardVerdict(False)
