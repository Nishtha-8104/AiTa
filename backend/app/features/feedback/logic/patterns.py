from collections import Counter
from typing import Dict, Optional

from app.core.topics import TOPIC_LABELS

DETAILED_HINT_LEVELS = (3, 4)


def _label(topic: str) -> str:
    return TOPIC_LABELS.get(topic, topic)


def _activity_patterns(activity_ctx: Dict) -> tuple[list, list, list]:
    errors, weak_concepts, strengths = [], [], []
    for mistake in activity_ctx["mistakes"]:
        if mistake["count"] >= 2:
            errors.append(f"Repeated mistake: {mistake['misconception'].replace('_', ' ')} "
                          f"({mistake['count']}x)")
    detailed = sum(activity_ctx["hints"].get(level, 0) for level in DETAILED_HINT_LEVELS)
    if detailed:
        errors.append(f"Needed step-by-step hints (level 3 or 4) {detailed}x")

    items = [i for i in activity_ctx["items"] if i["topic"]]
    tried = Counter(i["topic"] for i in items)
    solved = Counter(i["topic"] for i in items if i["solved"])
    for topic, count in tried.items():
        if solved[topic] < count:
            weak_concepts.append(_label(topic))
        if solved[topic]:
            strengths.append(f"Solved {solved[topic]} of {count} on {_label(topic)}")
    for change in activity_ctx["topics"]:
        if change["after"] > change["before"]:
            strengths.append(f"Mastery of {_label(change['topic'])} went up")
    return errors, weak_concepts, strengths


def analyse_patterns(eval_ctx: Optional[Dict], activity_ctx: Optional[Dict]) -> Dict:
    errors, weak_concepts, strengths = [], [], []

    if eval_ctx:
        for issue in eval_ctx["issues"][:10]:
            if issue.get("severity") in ("error", "critical"):
                errors.append(f"[{issue.get('category', '?')}] {issue.get('message', '')}")
        for dim, score in [("correctness", eval_ctx["correctness"]),
                           ("complexity", eval_ctx["complexity"]),
                           ("efficiency", eval_ctx["efficiency"]),
                           ("style", eval_ctx["style"])]:
            if score is not None and score < 60:
                weak_concepts.append(dim)
        strengths.extend(eval_ctx.get("best_practices", [])[:3])

    if activity_ctx:
        more_errors, more_weak, more_strengths = _activity_patterns(activity_ctx)
        errors.extend(more_errors)
        weak_concepts.extend(more_weak)
        strengths.extend(more_strengths)

    return {
        "errors": list(dict.fromkeys(errors))[:8],
        "weak_concepts": list(dict.fromkeys(weak_concepts))[:6],
        "strengths": list(dict.fromkeys(strengths))[:5],
    }
