"""Turns the generator's plain-text replies into items. Code never travels in JSON:
the chat model strips its line breaks there."""

import re

_QUESTION = re.compile(r"=== QUESTION ===(.*?)=== END ===", re.DOTALL)
_OPTION = re.compile(r"^\s*([A-E])\)\s*(.*?)\s*\|\|\s*(\S+)\s*$", re.MULTILINE)
_FENCE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)


def _section(block: str, name: str, following: tuple[str, ...]) -> str:
    stops = "|".join(re.escape(f) for f in following)
    pattern = rf"^{name}:\s*(.*?)(?=^(?:{stops}):|\Z)" if stops else rf"^{name}:\s*(.*)"
    match = re.search(pattern, block, re.DOTALL | re.MULTILINE)
    return match.group(1).strip() if match else ""


def parse_mcqs(text: str) -> list[dict]:
    items = []
    for block in _QUESTION.findall(text or ""):
        difficulty = _section(block, "DIFFICULTY", ("STEM",)).split()[0:1]
        stem = _section(block, "STEM", ("OPTIONS",))
        options_text = _section(block, "OPTIONS", ("VERIFY",))
        verify_block = _section(block, "VERIFY", ("EXPLANATION",))
        explanation = _section(block, "EXPLANATION", ())

        options, answer = [], None
        for index, (_, option, tag) in enumerate(_OPTION.findall(options_text)):
            tag = tag.strip().lower()
            if tag == "correct":
                answer = index if answer is None else -1
                tag = None
            elif tag == "none":
                tag = None
            options.append({"text": option.strip().strip("`"), "misconception": tag})

        fenced = _FENCE.search(verify_block)
        items.append({
            "language": _section(block, "LANGUAGE", ("DIFFICULTY",)).lower() or "python",
            "difficulty": difficulty[0].lower() if difficulty else "",
            "stem": stem,
            "options": options,
            "answer_index": answer if answer is not None and answer >= 0 else -1,
            "verify_code": (fenced.group(1) if fenced else verify_block).strip("\n"),
            "explanation": explanation,
        })
    return items


def parse_debug(text: str) -> tuple[str, str] | None:
    """(correct, buggy) programs, or None when the reply is not in the expected shape."""
    correct = re.search(r"CORRECT:\s*```[^\n]*\n(.*?)```", text or "", re.DOTALL)
    buggy = re.search(r"BUGGY:\s*```[^\n]*\n(.*?)```", text or "", re.DOTALL)
    if not correct or not buggy:
        return None
    return correct.group(1), buggy.group(1)
