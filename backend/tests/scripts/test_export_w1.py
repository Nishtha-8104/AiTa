from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.core.topics import TOPICS
from app.features.accounts.models import User
from app.features.onboarding.models import (
    DiagnosticItem,
    DiagnosticResponse,
    LanguageCheck,
    OnboardingRecord,
)
from scripts.eval import export_w1

START = datetime(2026, 10, 17, 10, 0, tzinfo=timezone.utc)


def _user(db, name: str, language: str) -> User:
    user = User(email=f"{name}@example.com", username=name,
                preferred_language=language)
    db.add(user)
    db.flush()
    return user


def _item(db, tag: str, kind: str, topic: str) -> DiagnosticItem:
    item = DiagnosticItem(external_id=tag, kind=kind, topic=topic, tier=1, difficulty="medium",
                          language="any" if kind == "theory" else "c", concept_key=tag,
                          body={}, key={})
    db.add(item)
    db.flush()
    return item


def _answer(db, user, item, order, phase, graded_by, score=None):
    db.add(DiagnosticResponse(user_id=user.id, item_id=item.id, order=order, phase=phase,
                              language=user.preferred_language, answer={}, score=score,
                              graded_by=graded_by, ms_taken=order * 1000))


def test_one_row_per_record_with_drop_off_and_calibration(session):
    finished = _user(session, "finisher", "c")
    dropped = _user(session, "dropper", "python")
    session.add(OnboardingRecord(
        user_id=finished.id, current_step="done", started_at=START,
        finished_at=START + timedelta(minutes=8),
        diagnostic_started_at=START + timedelta(minutes=2),
        step_durations={"welcome": 5.0, "language": 10.0, "about": 40.0, "learning": 30.0},
        self_rating=4, title="Loop Tamer", concept_level="medium",
        seeds={"basics_io": [0.7, "asked"], "loops": [0.5, "asked"]}))
    session.add(OnboardingRecord(user_id=dropped.id, current_step="about", started_at=START,
                                 step_durations={"welcome": 4.0, "language": 9.0},
                                 seeds=None))
    code = _item(session, "c1", "predict_output", "basics_io")
    skipped = _item(session, "c2", "fill_blank", "loops")
    theory = [_item(session, f"t{i}", "theory", "loops") for i in range(3)]
    _answer(session, finished, code, 1, "warmup", "key", 1.0)
    _answer(session, finished, skipped, 2, "code", "skipped")
    _answer(session, finished, theory[0], 3, "theory", "llm", 0.8)
    _answer(session, finished, theory[1], 4, "theory", "pending")
    _answer(session, finished, theory[2], 5, "theory", "saved")
    finished.preferred_language = "cpp"
    session.add(LanguageCheck(user_id=finished.id, language="cpp", started_at=START,
                              diagnostic_started_at=START, finished_at=START + timedelta(minutes=3),
                              seeds={"loops": [0.25, "asked"]}, title="Fresh Starter"))
    _answer(session, finished, _item(session, "p1", "predict_output", "loops"), 1, "warmup",
            "key", 0.0)
    session.commit()

    exported = export_w1.rows(session)
    recheck = next(row for row in exported if row["check"] == "recheck")
    rows = {row["user_id"]: row for row in exported if row["check"] == "onboarding"}

    assert (recheck["user_id"], recheck["language"], recheck["items_asked"]) == (finished.id,
                                                                                "cpp", 1)
    assert (recheck["seed_loops"], recheck["step_diagnostic_s"]) == (0.25, 180.0)
    assert recheck["self_rating"] == recheck["step_about_s"] == ""
    assert len(rows) == 2
    done, gone = rows[finished.id], rows[dropped.id]
    assert done["language"] == "c" and done["drop_off_step"] == ""
    assert done["total_s"] == 480.0
    assert done["step_about_s"] == 40.0
    assert (done["items_asked"], done["code_items"], done["theory_items"]) == (5, 2, 3)
    assert (done["skipped_items"], done["pending_items"]) == (1, 2)
    assert done["step_diagnostic_s"] == 360.0
    assert (done["item_ms_median"], done["item_ms_total"]) == (3000, 15000)
    assert done["started_at"] == "2026-10-17T10:00:00+00:00"
    assert done["seed_basics_io"] == 0.7 and done["seed_sorting"] == ""
    assert done["mean_seed"] == 0.6
    assert done["calibration_gap"] == 0.2
    assert gone["language"] == "python"
    assert gone["drop_off_step"] == "about" and gone["total_s"] == ""
    assert gone["step_about_s"] == "" and gone["items_asked"] == 0
    assert gone["step_diagnostic_s"] == gone["item_ms_median"] == gone["item_ms_total"] == ""
    assert gone["mean_seed"] == "" and gone["calibration_gap"] == ""
    assert all(f"seed_{topic}" in gone for topic in TOPICS)


def test_cli_refuses_a_path_inside_the_repo():
    inside = Path(export_w1.__file__).resolve().parents[3] / "w1.csv"
    with pytest.raises(SystemExit, match="outside the repo"):
        export_w1.main([str(inside)])
    assert not inside.exists()
