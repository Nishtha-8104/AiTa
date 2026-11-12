r"""One CSV row per onboarding participant for the W1 analysis, plus one per language
re-check (check = recheck), inside the backend container:

    docker compose exec backend \
        python -m scripts.eval.export_w1 /tmp/w1.csv
    docker compose cp \
        backend:/tmp/w1.csv G:/Study/BMP2/docs/study/w1.csv

Read-only. The output path is required and may not be inside the repo."""

import argparse
import csv
from collections import defaultdict
from datetime import timezone
from pathlib import Path
from statistics import median

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.topics import TOPICS
from app.features.accounts.models import User
from app.features.onboarding.logic.steps import utc
from app.features.onboarding.models import (
    DiagnosticItem,
    DiagnosticResponse,
    LanguageCheck,
    OnboardingRecord,
)

STEPS = ("welcome", "language", "about", "learning")
PENDING = ("pending", "saved")
COLUMNS = ("user_id", "check", "language", "started_at", "finished_at", "total_s",
           *(f"step_{step}_s" for step in STEPS), "step_diagnostic_s", "drop_off_step",
           "items_asked", "code_items", "theory_items", "skipped_items", "pending_items",
           "item_ms_median", "item_ms_total",
           *(f"seed_{topic}" for topic in TOPICS), "concept_level", "self_rating", "mean_seed",
           "calibration_gap", "title")
# Inside the container the scripts sit at /app/scripts, with no repo around them.
_ROOT = Path(__file__).resolve().parents[3]
REPO = _ROOT if (_ROOT / "backend").is_dir() else None


def _blank(value):
    return "" if value is None else value


def _stamp(moment) -> str:
    return utc(moment).astimezone(timezone.utc).isoformat() if moment else ""


def _seconds(start, end):
    return round((utc(end) - utc(start)).total_seconds(), 1) if start and end else None


def _check_columns(check, language: str, kind: str,
                   responses: list[DiagnosticResponse]) -> dict:
    """The columns an onboarding check and a language re-check share."""
    seeds = {topic: value for topic, (value, _source) in (check.seeds or {}).items()}
    theory = [r for r in responses if r.phase == "theory"]
    times = [r.ms_taken for r in responses]
    return {
        "user_id": check.user_id,
        "check": kind,
        "language": language,
        "started_at": _stamp(check.started_at),
        "finished_at": _stamp(check.finished_at),
        "total_s": _blank(_seconds(check.started_at, check.finished_at)),
        "step_diagnostic_s": _blank(_seconds(check.diagnostic_started_at, check.finished_at)),
        "items_asked": len(responses),
        "code_items": len(responses) - len(theory),
        "theory_items": len(theory),
        "skipped_items": sum(r.graded_by == "skipped" for r in responses),
        "pending_items": sum(r.graded_by in PENDING for r in responses),
        "item_ms_median": median(times) if times else "",
        "item_ms_total": sum(times) if times else "",
        **{f"seed_{topic}": _blank(seeds.get(topic)) for topic in TOPICS},
        "mean_seed": _blank(round(sum(seeds.values()) / len(seeds), 3) if seeds else None),
        "title": _blank(check.title),
    }


def _row(record: OnboardingRecord, language: str, responses: list[DiagnosticResponse]) -> dict:
    durations = record.step_durations or {}
    row = _check_columns(record, language, "onboarding", responses)
    mean_seed = row["mean_seed"]
    gap = (round(record.self_rating / 5 - mean_seed, 3)
           if record.self_rating is not None and mean_seed != "" else None)
    return {
        **row,
        **{f"step_{step}_s": _blank(durations.get(step)) for step in STEPS},
        "drop_off_step": "" if record.finished_at else record.current_step,
        "concept_level": record.concept_level,
        "self_rating": _blank(record.self_rating),
        "calibration_gap": _blank(gap),
    }


def _recheck_row(check: LanguageCheck, responses: list[DiagnosticResponse]) -> dict:
    return {**dict.fromkeys(COLUMNS, ""),
            **_check_columns(check, check.language, "recheck", responses),
            "drop_off_step": "" if check.finished_at else "recheck"}


def rows(db: Session) -> list[dict]:
    by_check: dict[tuple[int, str], list[DiagnosticResponse]] = defaultdict(list)
    served: dict[int, str] = {}
    responses = (db.query(DiagnosticResponse, DiagnosticItem.language)
                 .join(DiagnosticItem, DiagnosticItem.id == DiagnosticResponse.item_id)
                 .order_by(DiagnosticResponse.order))
    for response, language in responses:
        by_check[(response.user_id, response.language)].append(response)
        if language != "any":
            served.setdefault(response.user_id, language)
    records = (db.query(OnboardingRecord, User.preferred_language)
               .join(User, User.id == OnboardingRecord.user_id)
               .order_by(OnboardingRecord.user_id))
    out = []
    for record, preferred in records:
        language = record.language or served.get(record.user_id, preferred)
        out.append(_row(record, language, by_check[(record.user_id, language)]))
    checks = db.query(LanguageCheck).order_by(LanguageCheck.user_id, LanguageCheck.started_at)
    out += [_recheck_row(check, by_check[(check.user_id, check.language)]) for check in checks]
    return out


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("out", help="CSV path, outside the repo")
    out = Path(parser.parse_args(argv).out).resolve()
    if REPO is not None and out.is_relative_to(REPO):
        raise SystemExit(f"Refusing to write {out}: choose a path outside the repo ({REPO}).")
    with SessionLocal() as db:
        exported = rows(db)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(exported)
    print(f"Wrote {len(exported)} rows to {out}")


if __name__ == "__main__":
    main()
