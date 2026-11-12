"""The content folder (backend/content, or CONTENT_DIR): every topic folder holds the same
seven JSON files. Each is {"schema": "<kind>/v1", "topic": <topic>, ...}; all but
topic.json carry an "items" list. Code and other multi-line text is stored as a list of
lines, which `text()` joins back exactly."""

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, create_model

from app.core.config import settings

KINDS: tuple[str, ...] = ("topic", "explanation", "problems", "mcq", "debug", "theory", "diagnostic")
VERSION = "v1"

Lines = list[str]
Difficulty = Literal["easy", "medium", "hard"]
CodeLanguage = Literal["c", "cpp", "python"]
AnyLanguage = Literal["c", "cpp", "python", "any"]


class ContentError(ValueError):
    pass


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class ExplanationItem(_Strict):
    id: str
    language: CodeLanguage
    title: str
    markdown: Lines


class Reference(_Strict):
    language: Literal["python"]
    code: Lines


class Test(_Strict):
    input: Lines
    output: Lines


class ProblemItem(_Strict):
    id: str
    title: str
    difficulty: Difficulty
    statement: str
    constraints: str
    reference: Reference
    tests: list[Test]


class Option(_Strict):
    text: str
    misconception: str | None


class McqItem(_Strict):
    id: str
    language: AnyLanguage
    difficulty: Difficulty
    stem: Lines
    options: list[Option]
    answer_index: int
    explanation: str
    verify_code: Lines = []


class DebugItem(_Strict):
    id: str
    language: CodeLanguage
    problem_id: str
    bug_type: str
    fixed_code: Lines
    buggy_code: Lines


class TheoryItem(_Strict):
    id: str
    language: CodeLanguage
    difficulty: Difficulty
    question: str
    model_answer: str
    key_points: list[str]


class DiagnosticItem(_Strict):
    id: str
    concept_key: str
    tier: int
    kind: Literal["predict_output", "fill_blank", "find_bug", "write_code", "theory"]
    language: AnyLanguage
    difficulty: Difficulty
    body: dict[str, Any]
    key: dict[str, Any]


def _schema(kind: str):
    return (Literal[f"{kind}/{VERSION}"], Field(alias="schema"))


def _items_file(kind: str, item: type[BaseModel]) -> type[BaseModel]:
    return create_model(f"{kind.title()}File", __base__=_Strict, format=_schema(kind),
                        topic=(str, ...), items=(list[item], ...))


FILES: dict[str, type[BaseModel]] = {
    "topic": create_model("TopicFile", __base__=_Strict, format=_schema("topic"),
                          topic=(str, ...), title=(str, ...), order=(int, ...)),
    "explanation": _items_file("explanation", ExplanationItem),
    "problems": _items_file("problems", ProblemItem),
    "mcq": _items_file("mcq", McqItem),
    "debug": _items_file("debug", DebugItem),
    "theory": _items_file("theory", TheoryItem),
    "diagnostic": _items_file("diagnostic", DiagnosticItem),
}


def root() -> Path:
    return Path(settings.CONTENT_DIR)


def topic_path(topic: str, kind: str) -> Path:
    return root() / "topics" / topic / f"{kind}.json"


def lines(value: str) -> Lines:
    return value.split("\n")


def text(value: Lines) -> str:
    return "\n".join(value)


def validate(kind: str, doc: dict, topic: str) -> dict:
    try:
        model = FILES[kind].model_validate(doc)
    except ValidationError as exc:
        raise ContentError(f"{topic}/{kind}.json: {exc}") from exc
    if model.topic != topic:
        raise ContentError(f"{topic}/{kind}.json says topic {model.topic!r}")
    return model.model_dump(by_alias=True)


def read(topic: str, kind: str) -> dict:
    path = topic_path(topic, kind)
    if not path.exists():
        raise ContentError(f"missing {path}")
    return validate(kind, json.loads(path.read_text("utf-8")), topic)


def items(topic: str, kind: str) -> list[dict]:
    return read(topic, kind)["items"]


def dumps(doc: dict) -> str:
    return json.dumps(doc, indent=2, ensure_ascii=False) + "\n"


def write(topic: str, kind: str, rows: list[dict]) -> Path:
    doc = validate(kind, {"schema": f"{kind}/{VERSION}", "topic": topic, "items": rows}, topic)
    path = topic_path(topic, kind)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dumps(doc), "utf-8")
    return path


def json_schema(kind: str) -> dict:
    return FILES[kind].model_json_schema(by_alias=True)
