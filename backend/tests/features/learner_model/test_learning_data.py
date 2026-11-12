import json
from datetime import datetime, timedelta, timezone
from itertools import count

from app.features.accounts.models import User
from app.features.feedback.models import FeedbackReport
from app.features.grading.models import CodeEvaluation, CodeSubmission, Language
from app.features.hints.models import HintEvent
from app.features.learner_model.logic.learning_data import SOURCES, query
from app.features.learner_model.models import LearningEvent, TopicMastery
from app.features.practice.models import (
    DebugAttempt,
    DebugChallenge,
    McqAttempt,
    McqQuestion,
)
from app.features.problems.models import Problem, ProblemSource

NOW = datetime(2026, 10, 12, 12, 0, tzinfo=timezone.utc)
_ids = count(1)


def make_user(session, name):
    u = User(email=f"{name}@example.com", username=name)
    session.add(u)
    session.commit()
    return u


def seed(session, user, marker, *, topic="dynamic_programming", when=NOW, tag="off_by_one",
         source="practice", evidence=3):
    n = next(_ids)
    problem = Problem(source=ProblemSource.DSA, statement=f"{marker} problem",
                      statement_hash=f"{n:064d}", topic=topic)
    session.add(problem)
    session.flush()
    submission = CodeSubmission(user_id=user.id, language=Language.C, code="x",
                                problem_id=problem.id, title=f"{marker} code")
    session.add(submission)
    session.flush()
    evaluation = CodeEvaluation(submission_id=submission.id, user_id=user.id,
                                tests_total=4, tests_passed=4, verification_status="verified",
                                created_at=when)
    question = McqQuestion(external_id=f"q{n}", topic=topic, difficulty="easy",
                           stem=f"{marker} question", options=[], answer_index=0,
                           verify_code="print(1)")
    challenge = DebugChallenge(external_id=f"d{n}", problem_id=problem.id, topic=topic,
                               difficulty="easy", language="c", statement=f"{marker} bug",
                               buggy_code="x", fixed_code="y", bug_type="off_by_one")
    session.add_all([evaluation, question, challenge])
    session.flush()
    session.add_all([
        McqAttempt(user_id=user.id, question_id=question.id, chosen_index=1, correct=False,
                   created_at=when),
        DebugAttempt(user_id=user.id, challenge_id=challenge.id, submitted_code="y",
                     tests_passed=2, tests_total=2, fixed=True, created_at=when),
        HintEvent(user_id=user.id, problem_id=problem.id, evaluation_id=evaluation.id,
                  level=1, source=source, created_at=when),
        LearningEvent(user_id=user.id, kind="code", topic=topic, score=1.0, weight=1.0,
                      hint_level_used=1, misconceptions=[tag], created_at=when,
                      language=user.preferred_language),
        FeedbackReport(user_id=user.id, headline=f"{marker} report", created_at=when),
    ])
    if session.get(TopicMastery, (user.id, topic, user.preferred_language)) is None:
        session.add(TopicMastery(user_id=user.id, topic=topic, language=user.preferred_language,
                                 mastery=0.6, evidence_count=evidence))
    session.commit()


def test_no_source_leaks_another_users_rows(session):
    alice, bob = make_user(session, "alice"), make_user(session, "bob")
    seed(session, alice, "ALICE")
    seed(session, bob, "BOBBY", tag="infinite_loop", source="chat", evidence=7319)

    for source in SOURCES:
        dumped = json.dumps(query(session, alice.id, source, now=NOW))
        assert "BOBBY" not in dumped, source
        assert "infinite_loop" not in dumped, source
        assert '"chat"' not in dumped, source
        assert "7319" not in dumped, source

    assert query(session, alice.id, "solved", now=NOW)["count"] == 2
    assert query(session, alice.id, "accuracy", now=NOW)["attempts"] == 3


def test_zero_attempt_user_gets_empty_answers(session):
    user = make_user(session, "fresh")
    for source in SOURCES:
        result = query(session, user.id, source, period="7d", topic="dp", now=NOW)
        assert "error" not in result
        json.dumps(result)

    assert query(session, user.id, "accuracy")["rate"] is None
    assert query(session, user.id, "solved")["count"] == 0
    assert query(session, user.id, "attempts")["items"] == []


def test_period_excludes_older_rows(session):
    user = make_user(session, "timed")
    seed(session, user, "NEW", when=NOW - timedelta(days=2))
    seed(session, user, "OLD", topic="arrays", when=NOW - timedelta(days=20))

    week = query(session, user.id, "solved", period="7d", now=NOW)
    assert week["count"] == 2
    assert all(i["topic"] == "dynamic_programming" for i in week["items"])
    assert query(session, user.id, "solved", period="30d", now=NOW)["count"] == 4
    assert len(query(session, user.id, "feedback_reports", period="7d", now=NOW)["reports"]) == 1
    assert query(session, user.id, "hints", period="7d", now=NOW)["total"] == 1


def test_topic_filter_and_error_dicts(session):
    user = make_user(session, "topical")
    seed(session, user, "DP")
    seed(session, user, "ARR", topic="arrays")
    submission = session.query(CodeSubmission).filter_by(title="DP code").one()
    session.add(CodeEvaluation(submission_id=submission.id, user_id=user.id,
                               tests_total=0, tests_passed=0, created_at=NOW))
    session.commit()

    solved = query(session, user.id, "solved", topic="dynamic_programming")
    assert solved["count"] == 2
    assert solved["by_topic"] == {"dynamic_programming": 2}
    accuracy = query(session, user.id, "accuracy", topic="dynamic_programming")
    assert (accuracy["attempts"], accuracy["passed"], accuracy["rate"]) == (3, 2, 0.667)
    assert accuracy["unverified"] == 1
    attempts = query(session, user.id, "attempts", topic="dynamic_programming")["items"]
    assert [a["verdict"] for a in attempts].count("unverified") == 1
    assert query(session, user.id, "feedback_reports", topic="dp")["scope"] == {
        "source": "feedback_reports", "period": "all"}
    assert query(session, user.id, "accuracy", item_type="mcq")["rate"] == 0.0
    assert query(session, user.id, "solved", language="c", item_type="coding")["count"] == 2

    assert query(session, user.id, "grades")["error"] == "unknown source"
    assert query(session, user.id, "grades")["valid"] == list(SOURCES)
    assert query(session, user.id, "solved", topic="astrology")["error"] == "unknown topic"
    assert "error" in query(session, user.id, "solved", period="1y")
    assert "error" in query(session, user.id, "solved", item_type="essay")
