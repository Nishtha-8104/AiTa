import re
from dataclasses import dataclass

from app.core.config import settings

_TERMS_PATH = settings.CONTENT_DIR / "moderation" / "terms.txt"
_CATEGORY_ORDER = ("self_harm", "slur", "sexual", "abuse")
_LEET = str.maketrans({"@": "a", "4": "a", "1": "i", "!": "i", "0": "o", "3": "e", "$": "s", "5": "s"})
_CODE = re.compile(r"```.*?(?:```|$)|`[^`\n]*`", re.DOTALL)
_LEET_TOKEN = re.compile(r"[a-z0-9@$!]+")
_RUN_OF_3 = re.compile(r"(.)\1{2,}")
_APOSTROPHE = re.compile(r"(?<=[a-z])['’](?=[a-z])")


@dataclass(frozen=True)
class ModerationResult:
    flagged: bool
    category: str | None


_PROGRAMMING_OFFER = "I'm happy to help with your programming questions, though. What are you working on?"

SAFE_REPLY: dict[str, str] = {
    "self_harm": (
        "I'm really sorry you're feeling this way, and I'm glad you said something. "
        "You don't have to go through this alone. Please talk to someone you trust, "
        "or call Tele-MANAS (free, 24x7): 14416 or 1-800-891-4416. "
        "If you're in immediate danger, call 112. "
        "Whenever you feel ready, I'm also here to help with your programming."
    ),
    "abuse": f"Let's keep things respectful, please. {_PROGRAMMING_OFFER}",
    "slur": f"I can't engage with that kind of language. {_PROGRAMMING_OFFER}",
    "sexual": f"That's not something I can help with here. {_PROGRAMMING_OFFER}",
}


def _alternation(terms: list[str]) -> str:
    return "|".join(
        r"[\s\-]+".join(map(re.escape, t.split())) for t in sorted(terms, key=len, reverse=True)
    )


def _directed(expletives: list[str]) -> str:
    words = _alternation(expletives)
    filler = r"(?:are|r|is|a|an|such|so|total|complete|little|stupid|dumb|useless|worthless|fucking|piece|of|hai|ho|h)"
    tail = r"(?=\s*(?:[.!?,;:]|$)|\s+(?:bot|pet|yaar|bro|bhai|hai|ho|h)\b)"
    return (
        rf"(?:you|u|ur|youre|tu|tum|aap|tujhe)(?:\s+{filler}){{0,4}}\s+(?:{words}){tail}"
        rf"|(?:{words})\s+(?:you|u){tail}"
        rf"|(?:{words})\s+(?:off|yourself|urself)"
        rf"|(?:{words})\s+(?:hai|ho|h)\s+(?:tu|tum|aap)"
    )


def _load_patterns() -> list[tuple[str, re.Pattern[str]]]:
    terms: dict[str, list[str]] = {c: [] for c in (*_CATEGORY_ORDER, "expletive")}
    for lineno, raw in enumerate(_TERMS_PATH.read_text(encoding="utf-8").splitlines(), 1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        category, _, term = line.partition(":")
        category = category.strip()
        if category not in terms or not term.strip():
            raise ValueError(f"{_TERMS_PATH.name}:{lineno}: bad entry {raw!r}")
        terms[category].append(term.strip().lower())
    bodies = {c: _alternation(terms[c]) for c in _CATEGORY_ORDER if terms[c]}
    if terms["expletive"]:
        directed = _directed(terms["expletive"])
        bodies["abuse"] = f"{bodies['abuse']}|{directed}" if "abuse" in bodies else directed
    return [
        (category, re.compile(rf"(?<![\w.$])(?:{body})(?![\w(])"))
        for category in _CATEGORY_ORDER
        if (body := bodies.get(category))
    ]


_PATTERNS = _load_patterns()


def _deleet(match: re.Match[str]) -> str:
    token = match.group()
    core = token.rstrip("0123456789")
    prefix = "$" if core.startswith("$") else ""
    return prefix + core[len(prefix):].translate(_LEET) + token[len(core):]


def _variants(text: str) -> set[str]:
    base = _APOSTROPHE.sub("", _CODE.sub(" ", text.lower()))
    out = set()
    for form in (base, _LEET_TOKEN.sub(_deleet, base)):
        out.add(_RUN_OF_3.sub(r"\1", form))
        out.add(_RUN_OF_3.sub(r"\1\1", form))
    return out


def check(text: str) -> ModerationResult:
    candidates = _variants(text)
    for category, pattern in _PATTERNS:
        if any(pattern.search(c) for c in candidates):
            return ModerationResult(True, category)
    return ModerationResult(False, None)
