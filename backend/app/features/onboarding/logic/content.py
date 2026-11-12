"""The diagnostic bank in the content folder, one diagnostic.json per topic. The files hold
code, outputs and test streams as lists of lines; the rows here hold plain strings, as
diagnostic_items stores them."""

from app.core import content
from app.core.topics import TOPICS

LINE_FIELDS = ("code", "code_with_blank", "starter_code", "fixed_code", "reference",
               "expected_output")
TEST_FIELDS = ("stdin", "expected_stdout")


def item_id(item: dict) -> str:
    return f"{item['concept_key']}:{item['language']}"


def _convert(part: dict, change) -> dict:
    out = {k: change(v) if k in LINE_FIELDS else v for k, v in part.items()}
    if "tests" in out:
        out["tests"] = [{k: change(v) if k in TEST_FIELDS else v for k, v in case.items()}
                        for case in out["tests"]]
    return out


def load(topics=TOPICS) -> list[dict]:
    return [{"concept_key": item["concept_key"], "topic": topic, "tier": item["tier"],
             "kind": item["kind"], "difficulty": item["difficulty"],
             "language": item["language"], "body": _convert(item["body"], content.text),
             "key": _convert(item["key"], content.text)}
            for topic in topics for item in content.items(topic, "diagnostic")]


def save(items: list[dict]) -> None:
    for topic in TOPICS:
        content.write(topic, "diagnostic", [
            {"id": item_id(item), "concept_key": item["concept_key"], "tier": item["tier"],
             "kind": item["kind"], "language": item["language"],
             "difficulty": item["difficulty"], "body": _convert(item["body"], content.lines),
             "key": _convert(item["key"], content.lines)}
            for item in items if item["topic"] == topic])
