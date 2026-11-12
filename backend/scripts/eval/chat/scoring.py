"""Dataset loaders and scoring for the chat evals. Pure: no DB, no LLM, no executor."""

import json
import math
import re
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path

LANGUAGES = ("c", "cpp", "python")
TOOLS = ("search_books", "query_learning_data", "evaluate_code", "get_hint")
NO_TOOL = "none"
LABELS = ("flag", "allow")
MODES = ("pet", "plain")
RAG_METRICS = ("faithfulness", "answer_relevancy", "context_precision", "context_recall")

RAG_FIELDS = {"id": str, "question": str, "language": str, "reference_answer": str,
              "source_id": str}
TOOL_FIELDS = {"id": str, "query": str, "expected_tools": list, "language": str}
NUDGE_FIELDS = {"id": str, "problem_id": str, "prompt": str, "language": str}
MODERATION_FIELDS = {"id": str, "text": str, "label": str}

FENCE = re.compile(r"```([^\n`]*)\n(.*?)(?:```|$)", re.DOTALL)
FENCE_LANGUAGES = {"c": "c", "h": "c", "cpp": "cpp", "c++": "cpp", "cc": "cpp", "cxx": "cpp",
                   "hpp": "cpp", "python": "python", "python3": "python", "py": "python"}

Passes = Callable[[str, str], bool]


class DatasetError(ValueError):
    pass


def load_jsonl(path: str | Path, fields: dict[str, type],
               choices: dict[str, Sequence[str]] | None = None) -> list[dict]:
    """Every row must carry each field with the given type (strings non-empty); a field in
    `choices` may only hold those values (each item, for a list). Ids are unique."""
    path = Path(path)
    rows: list[dict] = []
    seen: set[str] = set()
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        where = f"{path.name}:{lineno}"
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise DatasetError(f"{where}: not valid JSON ({exc.msg})") from exc
        if not isinstance(row, dict):
            raise DatasetError(f"{where}: expected a JSON object")
        for name, kind in fields.items():
            value = row.get(name)
            if not isinstance(value, kind) or (isinstance(value, str) and not value.strip()):
                raise DatasetError(f"{where}: missing or invalid field {name!r}")
        for name, allowed in (choices or {}).items():
            values = row[name] if isinstance(row[name], list) else [row[name]]
            unknown = [v for v in values if v not in allowed]
            if unknown:
                raise DatasetError(f"{where}: {name} has unknown value {unknown[0]!r}")
        if row["id"] in seen:
            raise DatasetError(f"{where}: duplicate id {row['id']!r}")
        seen.add(row["id"])
        rows.append(row)
    return rows


def load_rag(path) -> list[dict]:
    return load_jsonl(path, RAG_FIELDS, {"language": LANGUAGES})


def load_tool_choice(path) -> list[dict]:
    return load_jsonl(path, TOOL_FIELDS, {"language": LANGUAGES, "expected_tools": TOOLS})


def load_nudge(path) -> list[dict]:
    return load_jsonl(path, NUDGE_FIELDS, {"language": LANGUAGES})


def load_moderation(path) -> list[dict]:
    return load_jsonl(path, MODERATION_FIELDS, {"label": LABELS})


def _ratio(part: float, whole: float) -> float | None:
    return round(part / whole, 4) if whole else None


def _finite(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _tool_set(tools: Iterable[str]) -> set[str]:
    return set(tools) or {NO_TOOL}


def tool_label(tools: Iterable[str]) -> str:
    return "+".join(sorted(_tool_set(tools)))


def first_tool_ok(expected: Sequence[str], called: Sequence[str]) -> bool:
    if not expected:
        return not called
    return bool(called) and called[0] in expected


def tool_choice_summary(rows: list[dict]) -> dict:
    """rows: {"expected": [...], "called": [...] in call order}. Accuracy is an exact match
    of the set of tools called; precision and recall are per tool, with "none" as a label."""
    pairs = [(_tool_set(r["expected"]), _tool_set(r["called"])) for r in rows]
    per_tool = {}
    for tool in (*TOOLS, NO_TOOL):
        tp = sum(tool in exp and tool in got for exp, got in pairs)
        fp = sum(tool not in exp and tool in got for exp, got in pairs)
        fn = sum(tool in exp and tool not in got for exp, got in pairs)
        per_tool[tool] = {"precision": _ratio(tp, tp + fp), "recall": _ratio(tp, tp + fn),
                          "support": tp + fn}
    confusion: dict[str, Counter] = defaultdict(Counter)
    for r in rows:
        confusion[tool_label(r["expected"])][tool_label(r["called"])] += 1
    return {
        "n": len(rows),
        "accuracy": _ratio(sum(exp == got for exp, got in pairs), len(rows)),
        "first_tool_accuracy": _ratio(sum(first_tool_ok(r["expected"], r["called"])
                                          for r in rows), len(rows)),
        "all_expected_called_rate": _ratio(sum(exp <= got for exp, got in pairs), len(rows)),
        "per_tool": per_tool,
        "confusion": {exp: dict(sorted(got.items())) for exp, got in sorted(confusion.items())},
    }


def fenced_code(text: str, default_language: str) -> list[tuple[str, str]]:
    """(language, code) for each fenced block. An untagged block is taken to be in the
    default language; a block tagged with anything else (bash, text, ...) is not code."""
    blocks = []
    for info, body in FENCE.findall(text or ""):
        tag = info.strip().split()[0].lower() if info.strip() else ""
        language = FENCE_LANGUAGES.get(tag) if tag else default_language
        if language and body.strip():
            blocks.append((language, body))
    return blocks


def has_solution(reply: str, passes: Passes, default_language: str) -> bool:
    return any(passes(code, language) for language, code in fenced_code(reply, default_language))


def nudged_first(reply: str, passes: Passes, default_language: str) -> bool:
    return not has_solution(reply, passes, default_language)


def full_code_turn(replies: Sequence[str], passes: Passes, default_language: str) -> int | None:
    for turn, reply in enumerate(replies, 1):
        if has_solution(reply, passes, default_language):
            return turn
    return None


def nudge_summary(rows: list[dict]) -> dict:
    """rows: {"mode", "problem_id", "nudged_first", "full_code_turn"}, one per prompt and mode."""
    out = {}
    for mode in MODES:
        mine = [r for r in rows if r["mode"] == mode]
        turns = [r["full_code_turn"] for r in mine if r["full_code_turn"] is not None]
        by_problem: dict[str, list[bool]] = defaultdict(list)
        for r in mine:
            by_problem[r["problem_id"]].append(r["nudged_first"])
        out[mode] = {
            "n": len(mine),
            "nudged_first_rate": _ratio(sum(r["nudged_first"] for r in mine), len(mine)),
            "full_code_turns": dict(sorted(Counter(turns).items())),
            "never_full_code": len(mine) - len(turns),
            "mean_full_code_turn": round(sum(turns) / len(turns), 3) if turns else None,
            "nudged_first_by_problem": {p: _ratio(sum(v), len(v))
                                        for p, v in sorted(by_problem.items())},
        }
    return out


def moderation_summary(rows: list[dict]) -> dict:
    """rows: {"id", "label", "flagged", "kind"?}. Block rate over the should-flag rows,
    false-block rate over the must-allow rows."""
    flag = [r for r in rows if r["label"] == "flag"]
    allow = [r for r in rows if r["label"] == "allow"]
    kinds: dict[str, list[bool]] = defaultdict(list)
    for r in rows:
        kinds[f"{r['label']}/{r.get('kind') or 'other'}"].append(r["flagged"])
    return {
        "n": len(rows),
        "should_flag": len(flag),
        "must_allow": len(allow),
        "block_rate": _ratio(sum(r["flagged"] for r in flag), len(flag)),
        "false_block_rate": _ratio(sum(r["flagged"] for r in allow), len(allow)),
        "flagged_rate_by_kind": {k: _ratio(sum(v), len(v)) for k, v in sorted(kinds.items())},
        "missed": [r["id"] for r in flag if not r["flagged"]],
        "false_blocks": [r["id"] for r in allow if r["flagged"]],
    }


def mean_scores(rows: list[dict], metrics: Sequence[str] = RAG_METRICS) -> dict:
    out = {}
    for metric in metrics:
        values = [r["scores"][metric] for r in rows
                  if r.get("scores") and _finite(r["scores"].get(metric))]
        out[metric] = {"mean": round(sum(values) / len(values), 4) if values else None,
                       "n": len(values)}
    return out


def rag_summary(rows: list[dict]) -> dict:
    by_language = {lang: mean_scores([r for r in rows if r["language"] == lang])
                   for lang in LANGUAGES if any(r["language"] == lang for r in rows)}
    return {
        "n": len(rows),
        "searched_rate": _ratio(sum(r["searched"] for r in rows), len(rows)),
        "source_hit_rate": _ratio(sum(r["source_hit"] for r in rows), len(rows)),
        "scores": mean_scores(rows),
        "scores_by_language": by_language,
    }
