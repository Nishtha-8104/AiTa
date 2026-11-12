"""A student's evaluation stats: submission and evaluation counts, averages and score
history."""

from collections import Counter

from sqlalchemy.orm import Session

from app.features.grading.models import CodeEvaluation, CodeSubmission, EvalHistoryEntry


def user_stats(db: Session, user_id: int) -> dict:
    history = (
        db.query(EvalHistoryEntry)
        .filter(EvalHistoryEntry.user_id == user_id)
        .order_by(EvalHistoryEntry.created_at.asc())
        .all()
    )
    submissions = (
        db.query(CodeSubmission).filter(CodeSubmission.user_id == user_id).count()
    )
    evaluations = (
        db.query(CodeEvaluation).filter(CodeEvaluation.user_id == user_id).all()
    )

    scores = [h.overall_score for h in history if h.overall_score is not None]
    avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0
    best = round(max(scores), 1) if scores else 0.0

    recent = scores[-5:]
    trend = 0.0
    if len(recent) >= 2:
        trend = round((recent[-1] - recent[0]) / max(len(recent) - 1, 1), 2)

    all_issues = []
    for evaluation in evaluations:
        all_issues.extend(evaluation.issues or [])
    categories = [i.get("category", "") for i in all_issues if isinstance(i, dict)]

    verified = [e for e in evaluations if e.verification_status == "verified"]
    verified_scores = [e.correctness_score for e in verified if e.correctness_score is not None]

    return {
        "total_submissions": submissions,
        "total_evaluations": len(evaluations),
        "avg_overall_score": avg_score,
        "best_score": best,
        "languages_used": sorted({h.language.value for h in history}),
        "most_common_issues": [c for c, _ in Counter(categories).most_common(5)],
        "improvement_trend": trend,
        "verified_evaluations": len(verified),
        "avg_verified_correctness": (
            round(sum(verified_scores) / len(verified_scores), 1)
            if verified_scores else None
        ),
        "recent_history": history[-10:],
    }
