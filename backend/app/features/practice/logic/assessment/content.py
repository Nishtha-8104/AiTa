"""The hand-written practice and theory banks from the content folder, as the rows the
seeders take. MCQ, debug and theory ids are written in the files, never derived."""

from app.core import content


def problem_row(item: dict, topic: str) -> dict:
    return {
        "external_id": item["id"],
        "title": item["title"],
        "topic": topic,
        "difficulty": item["difficulty"],
        "statement": item["statement"],
        "constraints": item["constraints"],
        "reference": content.text(item["reference"]["code"]),
        "tests": [{"kind": "sample" if n == 0 else "normal",
                   "stdin": content.text(case["input"]) + "\n",
                   "expected_stdout": content.text(case["output"])}
                  for n, case in enumerate(item["tests"])],
    }


def mcq_row(item: dict, topic: str) -> dict:
    return {
        "external_id": item["id"],
        "topic": topic,
        "language": item["language"],
        "difficulty": item["difficulty"],
        "stem": content.text(item["stem"]),
        "options": item["options"],
        "answer_index": item["answer_index"],
        "verify_code": content.text(item["verify_code"]),
        "explanation": item["explanation"],
        "explanations": [item["explanation"]] if item["explanation"] else [],
    }


def debug_row(item: dict) -> dict:
    return {
        "external_id": item["id"],
        "problem_external_id": item["problem_id"],
        "language": item["language"],
        "bug_type": item["bug_type"],
        "fixed_code": content.text(item["fixed_code"]),
        "buggy_code": content.text(item["buggy_code"]),
    }


def theory_row(item: dict, topic: str) -> dict:
    return {
        "external_id": item["id"],
        "topic": topic,
        "language": item["language"],
        "difficulty": item["difficulty"],
        "question": item["question"],
        "model_answer": item["model_answer"],
        "key_points": item["key_points"],
    }


def load_practice(topic: str) -> dict:
    return {
        "problems": [problem_row(i, topic) for i in content.items(topic, "problems")],
        "mcqs": [mcq_row(i, topic) for i in content.items(topic, "mcq")],
        "debug": [debug_row(i) for i in content.items(topic, "debug")],
    }


def load_theory(topics) -> list[dict]:
    return [theory_row(i, topic) for topic in topics for i in content.items(topic, "theory")]
