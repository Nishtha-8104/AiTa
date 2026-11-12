"""Generated buggy programs tend to annotate their own bug ("# BUG: should be =="),
which hands the student the answer. Comments carry no behaviour, so they are removed
from every line the bug touched, and any that still talk about the bug are rejected."""

import re

_COMMENT_MARKER = {"python": "#", "cpp": "//", "c": "//"}
_REVEALING = re.compile(r"\b(bug|buggy|fix|fixed|should|changed|wrong|incorrect|error|"
                        r"off[- ]by[- ]one|planted)\b", re.IGNORECASE)


def _split_comment(line: str, marker: str) -> tuple[str, str | None]:
    """Code part and comment part, ignoring markers inside string literals."""
    quote = None
    i = 0
    while i < len(line):
        ch = line[i]
        if quote:
            if ch == "\\":
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
        elif line.startswith(marker, i):
            return line[:i].rstrip(), line[i + len(marker):]
        i += 1
    return line, None


def strip_bug_annotations(buggy: str, fixed: str, language: str) -> str:
    marker = _COMMENT_MARKER.get(language)
    if marker is None:
        return buggy
    fixed_lines = {line.strip() for line in fixed.splitlines()}
    out = []
    for line in buggy.splitlines():
        if line.strip() in fixed_lines:
            out.append(line)
            continue
        code, comment = _split_comment(line, marker)
        if comment is None:
            out.append(line)
        elif code.strip():
            out.append(code)
    return "\n".join(out) + ("\n" if buggy.endswith("\n") else "")


def reveals_bug(buggy: str, fixed: str, language: str) -> bool:
    """A comment the fixed program does not share that talks about the bug."""
    marker = _COMMENT_MARKER.get(language)
    if marker is None:
        return False
    fixed_lines = {line.strip() for line in fixed.splitlines()}
    for line in buggy.splitlines():
        if line.strip() in fixed_lines:
            continue
        _, comment = _split_comment(line, marker)
        if comment and _REVEALING.search(comment):
            return True
    return False
