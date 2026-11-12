import json

import pytest

from scripts.eval.chat import scoring
from scripts.eval.chat.results import DATA


def test_loaders_reject_bad_rows_and_accept_the_shipped_datasets(tmp_path):
    path = tmp_path / "rag.jsonl"
    good = {"id": "q1", "question": "What is a pointer?", "language": "c",
            "reference_answer": "An address.", "source_id": "beej-c"}
    path.write_text(json.dumps(good) + "\n" + json.dumps({**good, "id": "q2", "question": ""}) + "\n",
                    encoding="utf-8")
    with pytest.raises(scoring.DatasetError, match="rag.jsonl:2: .*'question'"):
        scoring.load_rag(path)

    path.write_text(json.dumps({"id": "t1", "query": "hi", "language": "c",
                                "expected_tools": ["run_code"]}), encoding="utf-8")
    with pytest.raises(scoring.DatasetError, match="unknown value 'run_code'"):
        scoring.load_tool_choice(path)

    assert len(scoring.load_rag(DATA / "rag_questions.jsonl")) >= 45
    assert len(scoring.load_tool_choice(DATA / "tool_choice.jsonl")) >= 45
    assert len(scoring.load_nudge(DATA / "nudge_prompts.jsonl")) >= 60
    assert len(scoring.load_moderation(DATA / "moderation_probe.jsonl")) >= 60


def test_tool_choice_accuracy_precision_recall_and_confusion():
    rows = [
        {"expected": ["search_books"], "called": ["search_books"]},
        {"expected": ["search_books"], "called": ["get_hint"]},
        {"expected": ["evaluate_code"], "called": ["evaluate_code", "get_hint"]},
        {"expected": [], "called": []},
    ]
    summary = scoring.tool_choice_summary(rows)

    assert summary["accuracy"] == 0.5
    assert summary["first_tool_accuracy"] == 0.75
    assert summary["all_expected_called_rate"] == 0.75
    assert summary["per_tool"]["search_books"] == {"precision": 1.0, "recall": 0.5, "support": 2}
    assert summary["per_tool"]["get_hint"]["precision"] == 0.0
    assert summary["per_tool"]["none"] == {"precision": 1.0, "recall": 1.0, "support": 1}
    assert summary["confusion"]["evaluate_code"] == {"evaluate_code+get_hint": 1}
    assert summary["confusion"]["search_books"] == {"get_hint": 1, "search_books": 1}


def test_evals_refuse_a_non_local_database():
    from scripts.eval.chat.harness import require_local_db

    with pytest.raises(SystemExit) as exc:
        require_local_db("postgresql://u:secret@ep-cool.neon.tech/pet")
    assert "localhost:5433" in str(exc.value) and "secret" not in str(exc.value)
    require_local_db("postgresql://pet:pet@localhost:5433/pet_db")
    require_local_db("postgresql://pet:pet@db:5432/pet_db")


def test_nudged_first_and_full_code_turn_use_the_judge_on_fenced_code():
    solution = "int main(void) { return 0; }"

    def passes(code, language):
        return language == "c" and code.strip() == solution

    nudge = "Try a loop from 2 to sqrt(n) first.\n```text\nfor each i: check n % i\n```"
    wrong = "```c\nint main(void) { return 1; }\n```"
    full = f"Here it is:\n```c\n{solution}\n```"
    untagged = f"```\n{solution}\n```"

    assert scoring.nudged_first(nudge, passes, "c")
    assert scoring.nudged_first(wrong, passes, "c")
    assert not scoring.nudged_first(full, passes, "c")
    assert not scoring.nudged_first(untagged, passes, "c")
    assert scoring.nudged_first(untagged, passes, "python")
    assert scoring.full_code_turn([nudge, wrong, full], passes, "c") == 3
    assert scoring.full_code_turn([nudge, wrong], passes, "c") is None
