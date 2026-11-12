"""The onboarding API end to end on SQLite, with a fake Sandbox and a fake theory judge."""

import json
from datetime import timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.dependencies import get_current_active_user
from app.core.topics import TOPICS
from app.features.accounts.models import User
from app.features.learner_model.models import LearningEvent, TopicMastery
from app.features.onboarding import service
from app.features.onboarding.logic import pending
from app.features.onboarding.logic.graders import theory
from app.features.onboarding.logic.walk import CODE_KINDS, WRITE_TOPICS
from app.features.onboarding.models import (
    DiagnosticItem,
    DiagnosticResponse,
    LearnerPreferences,
    OnboardingRecord,
)
from app.features.practice.models import McqQuestion
from tests.conftest import FakeExecutionProvider, ok
from tests.features.onboarding.test_bank_graders import strings
from tests.features.onboarding.test_theory_pending import Judge

API = "/api/v1/onboarding"
PASS_OUT = "sandbox-pass"
TESTS = [{"stdin": "stdin-secret", "expected_stdout": PASS_OUT}]
ABOUT = {"year_of_study": 2, "program": "B.Tech CSE", "institution": "NIT Surat",
         "experience": "6to12m", "goal": "placements"}
LEARNING = {"explanation_style": "short", "example_order": "concept_first",
            "chat_language": "hinglish", "hours_per_week": "5to10", "self_rating": 3}


@pytest.fixture
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as session:
        yield session


@pytest.fixture
def user(db):
    u = User(email="onboard@example.com", username="onboarder")
    db.add(u)
    db.commit()
    return u


@pytest.fixture
def client(db, user):
    from app.main import app

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_active_user] = lambda: user
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def sandbox(monkeypatch):
    provider = FakeExecutionProvider([ok(PASS_OUT + "\n")])
    monkeypatch.setattr("app.features.grading.logic.execution.run_code.get_provider", lambda: provider)
    return provider


@pytest.fixture(autouse=True)
def retries(monkeypatch):
    calls = []
    monkeypatch.setattr(pending, "retry_with_backoff", calls.append)
    return calls


@pytest.fixture
def judge(monkeypatch):
    def install(**kwargs):
        fake = Judge(**kwargs)
        monkeypatch.setattr(theory.llm_gateway, "invoke", fake)
        return fake
    return install


def add_item(db, topic, kind, difficulty, language="c"):
    tag = f"{topic}-{kind}-{difficulty}"
    body, key = {
        "predict_output": ({"code": f"/* {tag} */"}, {"expected_output": f"out of {tag}"}),
        "find_bug": ({"code": "line one\nline two"},
                     {"bug_line": 2, "fixed_code": f"fixed {tag}", "tests": TESTS}),
        "fill_blank": ({"code_with_blank": "x = ____;", "blank_marker": "____"},
                       {"answer": f"blank {tag}", "tests": TESTS}),
        "write_code": ({"statement": f"Write {tag}.", "starter_code": ""},
                       {"reference": f"reference {tag}", "tests": TESTS}),
        "theory": ({"question": f"Explain {topic}."},
                   {"rubric": [f"{tag} point {n}" for n in (1, 2, 3)],
                    "model_answer": f"model {tag}"}),
    }[kind]
    db.add(DiagnosticItem(external_id=f"{tag}-{language}", kind=kind, topic=topic, tier=1,
                          difficulty=difficulty, language=language, concept_key=tag,
                          body=body, key=key, reviewed=True))


def make_bank(db, theory_only=False):
    for topic in TOPICS:
        add_item(db, topic, "theory", "medium", language="any")
        if theory_only:
            continue
        for kind in CODE_KINDS:
            for difficulty in ("easy", "medium"):
                add_item(db, topic, kind, difficulty)
        if topic in WRITE_TOPICS:
            add_item(db, topic, "write_code", "medium")
        db.add(McqQuestion(external_id=f"mcq-{topic}", topic=topic, difficulty="easy",
                           stem="Pick one.", answer_index=0, verify_code="print('a')",
                           options=[{"text": "a", "misconception": None},
                                    {"text": "b", "misconception": None}],
                           reviewed=True, language="any"))
    db.commit()


def right_answer(db, item_id):
    item = db.get(DiagnosticItem, item_id)
    if item.kind == "predict_output":
        return {"text": item.key["expected_output"]}
    if item.kind == "find_bug":
        return {"line": item.key["bug_line"], "fix_code": "fixed"}
    if item.kind == "write_code":
        return {"code": "int f(void) { return 1; }"}
    return {"text": "A clear answer."}


def start(client):
    return client.post(f"{API}/diagnostic/next").json()


def put_background(client):
    for step, body in (("language", {"language": "c"}), ("about", ABOUT),
                       ("learning", LEARNING)):
        assert client.put(f"{API}/steps/{step}", json=body).status_code == 200


def begin(client):
    put_background(client)
    return start(client)


def submit(client, item_id, answer, ms_taken=1000):
    return client.post(f"{API}/diagnostic/answer",
                       json={"item_id": item_id, "answer": answer, "ms_taken": ms_taken})


def run_all(client, db):
    step, payloads = begin(client), []
    while not step["done"]:
        payloads.append(step["item"])
        assert step["topic_map"][step["item"]["topic"]] == "asking"
        out = submit(client, step["item"]["id"], right_answer(db, step["item"]["id"]))
        assert out.status_code == 200, out.text
        step = out.json()["next"]
    return payloads


def theory_answers(client, count):
    step, outs = begin(client), []
    for _ in range(count):
        out = submit(client, step["item"]["id"], {"text": "It repeats the work."}).json()
        outs.append(out)
        step = out["next"]
    return outs


def test_new_user_state_welcome(client):
    state = client.get(f"{API}/state").json()
    assert (state["current_step"], state["diagnostic"], state["card"]) == ("welcome", None, None)
    assert client.get("/api/v1/auth/me").json()["onboarding_done"] is False


def test_steps_save_and_resume(client, db, user):
    for step, body in (("language", {"language": "python"}), ("about", ABOUT),
                       ("learning", LEARNING)):
        assert client.put(f"{API}/steps/{step}", json=body).status_code == 200

    db.expire_all()
    assert user.preferred_language == "python"
    assert user.years_of_experience == 0.75
    assert (user.year_of_study, user.institution) == (2, "NIT Surat")
    prefs = db.get(LearnerPreferences, user.id)
    assert (prefs.goal, prefs.program, prefs.chat_language) == ("placements", "B.Tech CSE",
                                                                 "hinglish")
    record = db.get(OnboardingRecord, user.id)
    assert set(record.step_durations) == {"language", "about", "learning"}
    assert record.self_rating == 3
    state = client.get(f"{API}/state").json()
    assert state["current_step"] == "diagnostic"
    assert state["answers"] == {"language": "python", "about": ABOUT, "learning": LEARNING}


def test_invalid_step_payload_422(client):
    assert client.put(f"{API}/steps/language", json={"language": "java"}).status_code == 422
    assert client.put(f"{API}/steps/diagnostic", json={}).status_code == 422


def test_resent_step_keeps_first_duration(client, db, user, monkeypatch):
    put_background(client)
    first = dict(db.get(OnboardingRecord, user.id).step_durations)
    later = service.now() + timedelta(seconds=500)
    monkeypatch.setattr(service, "now", lambda: later)

    assert client.put(f"{API}/steps/about", json=ABOUT).status_code == 200

    db.expire_all()
    assert db.get(OnboardingRecord, user.id).step_durations == first


def test_next_requires_background_steps(client):
    assert client.post(f"{API}/diagnostic/next").status_code == 409
    client.put(f"{API}/steps/language", json={"language": "c"})
    assert client.post(f"{API}/diagnostic/next").status_code == 409


def test_language_locked_after_diagnostic_starts(client):
    begin(client)
    assert client.put(f"{API}/steps/language", json={"language": "cpp"}).status_code == 409


def test_finish_requires_walk_done(client, db, judge):
    make_bank(db, theory_only=True)
    judge()
    put_background(client)
    assert client.post(f"{API}/finish").status_code == 409

    theory_answers(client, 1)

    assert client.post(f"{API}/finish").status_code == 409
    assert db.query(LearningEvent).count() == 0


def test_next_payload_has_no_key(client, db, judge):
    make_bank(db)
    judge()

    payloads = run_all(client, db)

    assert len(payloads) == 12
    for payload in payloads:
        item = db.get(DiagnosticItem, payload["id"])
        dumped = json.dumps(payload)
        assert "key" not in payload
        for secret in strings(item.key):
            assert json.dumps(secret.strip())[1:-1] not in dumped, (item.kind, secret)


def test_answer_for_wrong_item_409(client, db):
    make_bank(db)
    current = begin(client)["item"]
    other = db.query(DiagnosticItem).filter(DiagnosticItem.id != current["id"]).first()

    assert submit(client, other.id, {"text": "x"}).status_code == 409
    assert db.query(DiagnosticResponse).count() == 0


def test_double_submit_idempotent(client, db):
    make_bank(db)
    current = begin(client)["item"]

    first = submit(client, current["id"], {"text": "not the output"})
    second = submit(client, current["id"], {"text": "a different guess"})

    assert first.status_code == second.status_code == 200
    assert first.json()["reveal"] == second.json()["reveal"]
    assert first.json()["reveal"]["correct"] is False
    assert first.json()["next"]["item"]["id"] == second.json()["next"]["item"]["id"]
    assert db.query(DiagnosticResponse).count() == 1


def test_find_bug_line_only_scores_half(client, db):
    make_bank(db)
    step = begin(client)
    while step["item"]["kind"] != "find_bug":
        step = submit(client, step["item"]["id"], right_answer(db, step["item"]["id"])).json()["next"]
    item = db.get(DiagnosticItem, step["item"]["id"])

    out = submit(client, item.id, {"line": item.key["bug_line"]}).json()

    assert (out["score"], out["reveal"]["correct"]) == (0.5, True)


def test_oversized_answer_422(client, db):
    make_bank(db, theory_only=True)
    current = begin(client)["item"]
    assert current["kind"] == "theory"

    for answer, ms_taken in (({"text": "x" * 2001}, 10), ({"code": "x" * 4001}, 10),
                             ({"line": 2.5}, 10), ({"text": "ok"}, -1),
                             ({"text": "ok"}, 3_600_001)):
        assert submit(client, current["id"], answer, ms_taken).status_code == 422, answer
    assert db.query(DiagnosticResponse).count() == 0


def test_theory_saved_then_one_call(client, db, judge):
    make_bank(db, theory_only=True)
    fake = judge()

    first, second = theory_answers(client, 2)
    assert (first["saved_only"], second["saved_only"]) == (True, True)
    assert first["reveal"] is None
    assert fake.calls == []

    third_id = second["next"]["item"]["id"]
    third = submit(client, third_id, {"text": "A base case."}).json()

    assert len(fake.calls) == 1
    assert third["saved_only"] is False
    assert len(third["theory_reveals"]) == 3
    assert all(r["reveal"]["model_answer"] for r in third["theory_reveals"])
    assert all(r["question"] == f"Explain {r['topic']}." for r in third["theory_reveals"])
    assert third["next"]["done"] is True
    assert submit(client, third_id, {"text": "A base case."}).json() == third
    assert len(fake.calls) == 1


def test_sweep_mid_block_keeps_one_call(client, db, judge):
    make_bank(db, theory_only=True)
    fake = judge()
    _, second = theory_answers(client, 2)

    assert pending.sweep_once(db) == 0
    submit(client, second["next"]["item"]["id"], {"text": "A base case."})

    assert len(fake.calls) == 1
    assert sorted(fake.calls[0]["ids"]) == sorted(r.id for r in db.query(DiagnosticResponse))
    assert len(fake.calls[0]["ids"]) == 3


def test_resume_mid_theory(client, db, judge):
    make_bank(db, theory_only=True)
    fake = judge()
    _, second = theory_answers(client, 2)
    third_id = second["next"]["item"]["id"]
    answered = {r.item_id for r in db.query(DiagnosticResponse)}

    state = client.get(f"{API}/state").json()

    assert state["diagnostic"]["item"]["id"] == third_id
    assert state["diagnostic"]["item"]["kind"] == "theory"
    assert third_id not in answered
    assert start(client)["item"]["id"] == third_id
    assert fake.calls == []


def test_finish_grades_unsent_theory(client, db, judge, monkeypatch):
    """The request that completed the block died before grading: the answers are still
    only saved, and finish sends them in one call."""
    make_bank(db, theory_only=True)
    fake = judge()
    with monkeypatch.context() as interrupted:
        interrupted.setattr(service, "_grade_theory_block", lambda *args: [])
        theory_answers(client, 3)
    saved = db.query(DiagnosticResponse).all()
    assert {r.graded_by for r in saved} == {"saved"}

    card = client.post(f"{API}/finish")

    assert card.status_code == 200
    assert card.json()["title"]
    assert [sorted(c["ids"]) for c in fake.calls] == [sorted(r.id for r in saved)]
    db.expire_all()
    assert {r.graded_by for r in saved} == {"llm"}


def test_finish_seeds_and_card(client, db, user, judge):
    make_bank(db)
    judge()
    run_all(client, db)

    card = client.post(f"{API}/finish").json()

    db.expire_all()
    assert db.get(TopicMastery, (user.id, "loops", "c")).mastery == pytest.approx(0.70)
    assert user.skill_level.value == "advanced"
    record = db.get(OnboardingRecord, user.id)
    assert record.title == card["title"] == "Recursion Ranger"
    practice = client.get("/api/v1/assessment/next").json()
    assert card["start_topic"] == practice["topic"]
    assert "mastery" not in card["start_reason"]
    assert client.get("/api/v1/auth/me").json()["onboarding_done"] is True
    seeded = db.query(LearningEvent).filter_by(kind="diagnostic_seed").count()

    assert client.post(f"{API}/finish").json() == card
    assert db.query(LearningEvent).filter_by(kind="diagnostic_seed").count() == seeded


def test_llm_busy_theory_pending_card_says_reviewing(client, db, user, judge, retries):
    make_bank(db, theory_only=True)
    fake = judge(busy=99)
    *_, last = theory_answers(client, 3)
    assert (last["saved_only"], last["theory_reveals"]) == (False, [])
    assert len(fake.calls) == 1

    card = client.post(f"{API}/finish")

    assert card.status_code == 200
    assert len(fake.calls) == 1
    assert (card.json()["concept_level"], card.json()["theory_pending"]) == ("unknown", True)
    assert {r.graded_by for r in db.query(DiagnosticResponse)} == {"pending"}
    assert retries and set(retries) == {user.id}


def test_slow_student_gets_full_walk(client, db, user, judge, monkeypatch):
    make_bank(db)
    step = begin(client)
    started = db.get(OnboardingRecord, user.id).diagnostic_started_at
    later = started.replace(tzinfo=timezone.utc) + timedelta(minutes=30)
    monkeypatch.setattr(service, "now", lambda: later)

    kinds = []
    while not step["done"]:
        kinds.append(step["item"]["kind"])
        out = submit(client, step["item"]["id"], right_answer(db, step["item"]["id"]))
        step = out.json()["next"]

    assert len(kinds) == 12 and kinds.count("theory") == 3


def finish_onboarding_in_c(client, db, judge):
    make_bank(db)
    for topic in TOPICS:
        for kind in CODE_KINDS:
            for difficulty in ("easy", "medium"):
                add_item(db, topic, kind, difficulty, language="python")
    db.commit()
    judge()
    run_all(client, db)
    client.post(f"{API}/finish")


def test_switch_to_new_language_requires_check_then_seeds_only_it(client, db, user, judge):
    finish_onboarding_in_c(client, db, judge)
    c_loops = db.get(TopicMastery, (user.id, "loops", "c")).mastery

    assert client.post(f"{API}/language", json={"language": "python"}).json() == {
        "language": "python", "needs_check": True}
    assert client.get("/api/v1/assessment/next").status_code == 428

    step, kinds = client.post(f"{API}/recheck/next").json(), []
    while not step["done"]:
        assert step["item"]["language"] == "python"
        kinds.append(step["item"]["kind"])
        out = client.post(f"{API}/recheck/answer", json={
            "item_id": step["item"]["id"], "ms_taken": 1000,
            "answer": right_answer(db, step["item"]["id"])})
        assert out.status_code == 200, out.text
        step = out.json()["next"]
    assert kinds and "theory" not in kinds

    result = client.post(f"{API}/recheck/finish").json()
    assert result["language"] == "python" and result["bands"]["basics_io"] == "strong"

    db.expire_all()
    assert db.get(TopicMastery, (user.id, "basics_io", "python")).mastery == pytest.approx(0.70)
    assert db.get(TopicMastery, (user.id, "loops", "c")).mastery == c_loops
    assert client.get("/api/v1/assessment/next").status_code == 200

    assert client.post(f"{API}/language", json={"language": "c"}).json()["needs_check"] is False
    mastery = client.get("/api/v1/profile/mastery").json()
    loops = next(t for t in mastery["topics"] if t["topic"] == "loops")
    assert loops["mastery"] == pytest.approx(c_loops, abs=1e-3)
    assert client.post(f"{API}/language", json={"language": "python"}).json()[
        "needs_check"] is False


def test_profile_patch_cannot_change_language_after_lock(client, db, user, judge):
    finish_onboarding_in_c(client, db, judge)

    out = client.patch("/api/v1/users/profile", json={"preferred_language": "python"})

    assert out.status_code == 409
    db.expire_all()
    assert user.preferred_language == "c"
