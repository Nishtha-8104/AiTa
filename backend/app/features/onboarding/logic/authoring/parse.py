"""Turns the drafting model's plain-text replies into bank items. Code travels in fenced
blocks, never in JSON: the chat model strips line breaks from JSON strings."""

import re
from collections import Counter

from app.features.onboarding.logic.walk import TIERS

TOPICS = tuple(topic for tier in TIERS for topic in tier)
TIER_OF = {topic: n for n, tier in enumerate(TIERS, 1) for topic in tier}
BLANK_MARKER = "____"
CODE_KINDS = ("predict_output", "find_bug", "fill_blank")
PORT_LANGUAGES = {"c": "c", "cpp": "cpp", "c++": "cpp"}

# label, part of the item, field name, how it is written
FIELDS: dict[str, tuple[tuple[str, str, str, str], ...]] = {
    "predict_output": (("CODE", "body", "code", "code"),
                       ("EXPECTED_OUTPUT", "key", "expected_output", "output")),
    "find_bug": (("STATEMENT", "body", "statement", "text"),
                 ("FIXED", "key", "fixed_code", "code"),
                 ("CHANGE_FROM", "key", "change_from", "line"),
                 ("CHANGE_TO", "key", "change_to", "line"),
                 ("TESTS", "key", "tests", "tests")),
    "fill_blank": (("CODE", "body", "code_with_blank", "code"),
                   ("ANSWER", "key", "answer", "text"),
                   ("TESTS", "key", "tests", "tests")),
    "write_code": (("STATEMENT", "body", "statement", "text"),
                   ("STARTER", "body", "starter_code", "code"),
                   ("REFERENCE", "key", "reference", "code"),
                   ("TESTS", "key", "tests", "tests")),
    "theory": (("QUESTION", "body", "question", "text"),
               ("RUBRIC", "key", "rubric", "list"),
               ("MODEL_ANSWER", "key", "model_answer", "text")),
}
SHARED_WITH_PORT = ("STATEMENT", "TESTS")

_LABELS = sorted({f[0] for fields in FIELDS.values() for f in fields}
                 | {"KIND", "DIFFICULTY", "LANGUAGE_SPECIFIC", "CONCEPT", "LANGUAGE"})
_STOP = "|".join(_LABELS)
# the model often drops the last END marker, so the next block or the reply's end also closes one
_ITEM = re.compile(r"=== ITEM ===(.*?)(?:=== END ===|(?==== ITEM ===)|\Z)", re.DOTALL)
_PORT = re.compile(r"=== PORT ===(.*?)(?:=== END ===|(?==== PORT ===)|\Z)", re.DOTALL)
_BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s*")
_TEST_MARKER = re.compile(r"^\s*###\s*(input|output)\s*:?\s*$", re.IGNORECASE)


def _fenced(block: str, label: str) -> str:
    """A model sometimes forgets the closing fence, so the next label also ends the code."""
    match = re.search(rf"^{label}:[ \t]*\n?```[^\n]*\n(.*?)(?:```|(?=^(?:{_STOP}):)|\Z)",
                      block, re.DOTALL | re.MULTILINE)
    return match.group(1) if match else ""


def _code(block: str, label: str) -> str:
    code = _fenced(block, label).strip("\n")
    return code + "\n" if code else ""


def _text(block: str, label: str) -> str:
    match = re.search(rf"^{label}:[ \t]*(.*?)(?=^(?:{_STOP}):|\Z)", block,
                      re.DOTALL | re.MULTILINE)
    return match.group(1).strip() if match else ""


def _word(block: str, label: str) -> str:
    words = _text(block, label).split()
    return words[0].strip("`*").lower() if words else ""


def _line(block: str, label: str) -> str:
    lines = _text(block, label).splitlines()
    return lines[0].strip().strip("`").strip() if lines else ""


def _list(block: str, label: str) -> list[str]:
    points = (_BULLET.sub("", line).strip() for line in _text(block, label).splitlines())
    return [point for point in points if point]


def _tests(block: str, label: str) -> list[dict]:
    cases, field = [], None
    for line in (_fenced(block, label) or _text(block, label)).split("\n"):
        marker = _TEST_MARKER.match(line)
        name = marker.group(1).lower() if marker else None
        if name == "input":
            cases.append({"stdin": [], "expected_stdout": []})
            field = "stdin"
        elif name == "output" and cases:
            field = "expected_stdout"
        elif cases and field:
            cases[-1][field].append(line)
    return [{name: "\n".join(lines).rstrip("\n") for name, lines in case.items()}
            for case in cases]


_READERS = {"code": _code, "output": _code, "text": _text, "line": _line, "list": _list,
            "tests": _tests}


def _plant_bug(fixed: str, change_from: str, change_to: str) -> tuple[str, int | None]:
    """BUGGY is built, not drafted: the model copies a program twice unreliably, so it names
    one line of FIXED and its buggy form. The line must occur exactly once."""
    lines = fixed.split("\n")
    hits = [n for n, line in enumerate(lines) if change_from and line.strip() == change_from]
    if len(hits) != 1 or not change_to or change_to == change_from:
        return "", None
    n = hits[0]
    lines[n] = lines[n][:len(lines[n]) - len(lines[n].lstrip())] + change_to
    return "\n".join(lines), n + 1


def _fields(block: str, kind: str, source: dict | None = None) -> tuple[dict, dict]:
    parts: dict[str, dict] = {"body": {}, "key": {}}
    for label, part, name, form in FIELDS[kind]:
        if source is not None and label in SHARED_WITH_PORT:
            parts[part][name] = source[part][name]
        else:
            parts[part][name] = _READERS[form](block, label)
    if kind == "fill_blank":
        parts["body"]["blank_marker"] = BLANK_MARKER
        parts["key"]["answer"] = parts["key"]["answer"].strip("`").strip()
    if kind == "find_bug":
        key = parts["key"]
        parts["body"]["code"], key["bug_line"] = _plant_bug(
            key["fixed_code"], key["change_from"], key["change_to"])
    return parts["body"], parts["key"]


def parse_topic_draft(text: str, topic: str, log: Counter | None = None) -> list[dict]:
    """Python items in draft order; a block of an unknown kind keeps its number. Theory is
    Python too: the model calls Python-only questions language-neutral, so every theory
    item is ported like code."""
    items = []
    for n, block in enumerate(_ITEM.findall(text or ""), 1):
        kind = _word(block, "KIND")
        if kind not in FIELDS:
            if log is not None:
                log["unknown_kind"] += 1
            continue
        body, key = _fields(block, kind)
        items.append({
            "concept_key": f"{topic}:{n}",
            "topic": topic,
            "tier": TIER_OF[topic],
            "kind": kind,
            "difficulty": _word(block, "DIFFICULTY") if kind in CODE_KINDS else "medium",
            "language": "python",
            "body": body,
            "key": key,
        })
    return items


def parse_port(text: str, items: list[dict]) -> dict[str, list[dict]]:
    """C and C++ candidates for the Python `items`, matched by concept_key; a concept may get
    several, and the first that verifies wins. Tests and the write-code statement are
    shared with the Python item, so the variants agree."""
    sources = {item["concept_key"]: item for item in items if item["language"] == "python"}
    ported: dict[str, list[dict]] = {"c": [], "cpp": []}
    for block in _PORT.findall(text or ""):
        concept = _text(block, "CONCEPT").strip("`* ")
        language = PORT_LANGUAGES.get(_word(block, "LANGUAGE"))
        source = sources.get(concept)
        kind = _word(block, "KIND")
        if source is None or language is None or kind not in ("", source["kind"]):
            continue
        body, key = _fields(block, source["kind"], source)
        ported[language].append({**source, "language": language, "body": body, "key": key})
    return ported
