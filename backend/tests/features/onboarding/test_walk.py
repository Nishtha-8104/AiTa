"""Pure diagnostic walk: simulated students and hand-built response lists."""

import pytest

from app.core.topics import TOPICS
from app.features.onboarding.logic.types import Ask, Done, ItemRef, Resp
from app.features.onboarding.logic.walk import (
    CODE_CAP,
    CODE_KINDS,
    ITEM_CAP,
    TIERS,
    next_step,
    remaining,
    theory_topics,
    topic_scores,
)

TIER_OF = {topic: n for n, tier in enumerate(TIERS, 1) for topic in tier}
FULL_BANK = frozenset(
    {(t, k, d) for t in TOPICS for k in CODE_KINDS for d in ("easy", "medium")}
    | {(t, "theory", "medium") for t in TOPICS}
    | {(t, "write_code", "medium") for t in ("arrays", "strings")}
)
WARMUP = ItemRef("basics_io", "predict_output", "easy", "warmup")


def resp(topic, score, kind="predict_output", difficulty="medium", phase="code", graded_by="key"):
    return Resp(ItemRef(topic, kind, difficulty, phase), score, graded_by)


def walk(answer, responses=(), bank=FULL_BANK):
    responses = list(responses)
    while True:
        step = next_step(responses, bank)
        if isinstance(step, Done):
            return responses
        assert len(responses) < ITEM_CAP
        responses.append(Resp(step.ref, answer(step.ref), "key"))


def by_level(level):
    return lambda ref: 1.0 if TIER_OF[ref.topic] <= level else 0.0


def simulate(level, bank=FULL_BANK):
    return walk(by_level(level), bank=bank)


def code_refs(responses):
    return [r.ref for r in responses if r.ref.phase != "theory"]


def theory_refs(responses):
    return [r.ref for r in responses if r.ref.phase == "theory"]


T1_PASSED = [resp("basics_io", 1.0, difficulty="easy", phase="warmup"),
             resp("basics_io", 1.0, kind="find_bug"),
             resp("conditionals", 1.0, kind="fill_blank")]


def test_first_item_is_warmup():
    assert next_step([], FULL_BANK) == Ask(WARMUP)


def test_all_wrong_stops_after_t1_and_asks_theory():
    responses = simulate(0)
    code, theory = code_refs(responses), theory_refs(responses)
    assert {ref.topic for ref in code} <= set(TIERS[0])
    assert len(theory) == 3
    assert [r.ref.phase for r in responses[-3:]] == ["theory"] * 3
    assert len(responses) <= 8


def test_all_right_hits_caps():
    responses = simulate(5)
    code, theory = code_refs(responses), theory_refs(responses)
    assert len(responses) == ITEM_CAP
    assert len(code) <= CODE_CAP
    assert len(theory) == 3 and len({ref.topic for ref in theory}) == 3
    writes = [ref for ref in code if ref.kind == "write_code"]
    assert len(writes) == 1 and writes[0].topic in ("arrays", "strings")


@pytest.mark.parametrize("k", [1, 2, 3, 4])
def test_level_k_bands(k):
    responses = simulate(k)
    scores = topic_scores(responses)
    for topic, score in scores.items():
        if TIER_OF[topic] <= k:
            assert score >= 0.5, topic
        else:
            assert TIER_OF[topic] == k + 1 and score < 0.5, topic
    assert all(TIER_OF[ref.topic] <= k + 1 for ref in code_refs(responses))


def test_fail_gets_one_followup():
    responses = T1_PASSED + [resp("loops", 0.0)]
    step = next_step(responses, FULL_BANK)
    assert step.ref.topic == "loops" and step.ref.difficulty == "easy"
    assert step.ref.phase == "followup" and step.ref.kind != "predict_output"
    responses.append(Resp(step.ref, 0.0, "key"))
    rest = code_refs(walk(lambda ref: 1.0, responses))[len(responses):]
    assert rest and {ref.topic for ref in rest}.isdisjoint({"loops", "arrays", "strings"})


def test_failed_without_followup_in_bank_blocks_dependents():
    bank = frozenset((t, k, d) for t, k, d in FULL_BANK if (t, d) != ("loops", "easy"))
    responses = walk(lambda ref: 1.0, T1_PASSED + [resp("loops", 0.0)], bank)
    asked = {ref.topic for ref in code_refs(responses)}
    assert "functions" in asked and asked.isdisjoint({"arrays", "strings"})


def test_skipped_followup_after_used_retry_blocks_dependents():
    responses = T1_PASSED[:2] + [
        resp("conditionals", None, kind="fill_blank", graded_by="skipped"),
        resp("conditionals", 0.0, phase="retry"),
        resp("conditionals", None, kind="find_bug", difficulty="easy", phase="followup",
             graded_by="skipped"),
    ]
    asked = {ref.topic for ref in code_refs(walk(lambda ref: 1.0, responses))}
    assert "functions" in asked and asked.isdisjoint({"loops", "arrays", "strings"})


def test_basics_warmup_counts_as_followup():
    responses = [resp("basics_io", 1.0, difficulty="easy", phase="warmup"),
                 resp("basics_io", 0.0, kind="find_bug")]
    step = next_step(responses, FULL_BANK)
    assert step.ref.topic == "conditionals" and step.ref.phase == "code"


def test_followup_capped():
    responses = T1_PASSED + [resp("loops", 0.0),
                             resp("loops", 1.0, kind="find_bug", difficulty="easy", phase="followup")]
    assert topic_scores(responses)["loops"] == 0.6


def test_skipped_retries_as_predict_output_once():
    responses = T1_PASSED + [resp("loops", None, kind="find_bug", graded_by="skipped")]
    step = next_step(responses, FULL_BANK)
    assert step == Ask(ItemRef("loops", "predict_output", "medium", "retry"))
    responses.append(Resp(step.ref, None, "skipped"))
    step = next_step(responses, FULL_BANK)
    assert step.ref.topic != "loops"
    assert "loops" not in topic_scores(responses)


def test_skipped_retries_easy_predict_output_when_no_medium():
    bank = FULL_BANK - {("loops", "predict_output", "medium"),
                        ("basics_io", "predict_output", "medium")}
    responses = T1_PASSED + [resp("loops", None, kind="find_bug", graded_by="skipped")]
    step = next_step(responses, bank)
    assert step == Ask(ItemRef("loops", "predict_output", "easy", "retry"))
    responses.append(Resp(step.ref, 1.0, "key"))
    assert next_step(responses, bank).ref.topic != "loops"
    assert topic_scores(responses)["loops"] == 0.6

    warmup_used = [resp("basics_io", 1.0, difficulty="easy", phase="warmup"),
                   resp("basics_io", None, kind="find_bug", graded_by="skipped")]
    assert next_step(warmup_used, bank).ref.phase != "retry"


def test_scored_warmup_decides_basics_when_medium_skipped():
    bank = FULL_BANK - {("basics_io", "predict_output", "medium")}
    failed = [resp("basics_io", 0.0, difficulty="easy", phase="warmup"),
              resp("basics_io", None, kind="find_bug", graded_by="skipped")]
    assert next_step(failed, bank).ref.phase == "theory"
    passed = [resp("basics_io", 1.0, difficulty="easy", phase="warmup"), failed[1]]
    assert next_step(passed, bank).ref.topic == "conditionals"


def test_consecutive_code_items_vary_kind():
    bank = frozenset(entry for entry in FULL_BANK
                     if entry[2] != "medium" or entry[1] in ("predict_output", "find_bug",
                                                            "theory", "write_code"))
    for level in (1, 3, 5):
        code = code_refs(simulate(level, bank))
        assert len(code) >= 4
        assert all(a.kind != b.kind for a, b in zip(code, code[1:])), (level, code)


@pytest.mark.parametrize("level", [1, 5])
def test_missing_bank_kinds_skip_topic_and_terminate(level):
    bank = frozenset(entry for entry in FULL_BANK if entry[0] != "loops")
    responses = simulate(level, bank)
    refs = [r.ref for r in responses]
    assert "loops" not in {ref.topic for ref in code_refs(responses)}
    assert len(refs) <= ITEM_CAP and len(set(refs)) == len(refs)


def test_theory_topics_slots():
    responses = T1_PASSED + [resp("loops", 1.0), resp("functions", 0.6, kind="find_bug"),
                             resp("arrays", 0.0, kind="fill_blank"),
                             resp("arrays", 0.0, difficulty="easy", phase="followup")]
    assert theory_topics(responses) == ["loops", "arrays", "functions"]
    assert theory_topics(T1_PASSED + [resp("loops", 1.0)]) == ["loops", "functions", "basics_io"]


def test_pending_theory_counts_as_answered():
    responses = [r for r in simulate(0) if r.ref.phase != "theory"]
    asked = []
    for _ in range(3):
        step = next_step(responses, FULL_BANK)
        assert step.ref.phase == "theory" and step.ref.topic not in asked
        asked.append(step.ref.topic)
        responses.append(Resp(step.ref, None, "pending"))
    assert next_step(responses, FULL_BANK) == Done()


def test_remaining_estimate():
    assert remaining([], FULL_BANK) == ITEM_CAP
    full = simulate(5)
    assert remaining(full[:11], FULL_BANK) == 1
    assert remaining(full, FULL_BANK) == 0
    assert remaining(T1_PASSED, FULL_BANK) == ITEM_CAP - len(T1_PASSED)
    beginner = simulate(1)
    for n in range(len(beginner) + 1):
        left = remaining(beginner[:n], FULL_BANK)
        assert 0 <= left <= ITEM_CAP - n
