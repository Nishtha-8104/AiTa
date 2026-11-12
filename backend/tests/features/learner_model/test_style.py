"""The onboarding style line and where it reaches the agents. No LLM anywhere."""

from types import SimpleNamespace

from app.features.chat.agent import context
from app.features.chat.agent.prompts import system_prompt
from app.features.chat.models import ChatThread
from app.features.feedback.agent.nodes.gather_context import _user_context
from app.features.hints.service import request_hint
from app.features.learner_model.logic.personalisation import style_line
from app.features.onboarding.models import LearnerPreferences, OnboardingRecord
from tests.features.hints.test_hints import attempt, problem, user  # noqa: F401

SAMPLE = ("Prefers short explanations, examples first, Hinglish OK. Concept understanding: "
          "low, so explain ideas from the basics. Goal: placements. About 2–5 hours a week.")


def onboard(session, user, concept_level="low", **overrides):
    values = {"goal": "placements", "explanation_style": "short",
              "example_order": "examples_first", "chat_language": "hinglish",
              "hours_per_week": "2to5", **overrides}
    session.add(LearnerPreferences(user_id=user.id, **values))
    session.add(OnboardingRecord(user_id=user.id, concept_level=concept_level))
    session.commit()


def chat_prompt(session, user, mode="pet"):
    thread = ChatThread(user_id=user.id, mode=mode)
    session.add(thread)
    session.commit()
    return system_prompt(mode, context.load(session, user.id, thread))


def test_style_line_text(session, user):
    onboard(session, user)
    assert style_line(session, user.id) == SAMPLE

    record = session.get(OnboardingRecord, user.id)
    for level, sentence in (("medium", " Concept understanding: medium. "),
                            ("high", " Concept understanding: high, so keep explanations brief. "),
                            ("unknown", " ")):
        record.concept_level = level
        session.commit()
        assert style_line(session, user.id) == (
            "Prefers short explanations, examples first, Hinglish OK."
            f"{sentence}Goal: placements. About 2–5 hours a week.")


def test_style_line_empty_without_prefs(session, user):
    assert style_line(session, user.id) == ""


def test_chat_prompt_includes_style_only_in_pet_mode(session, user):
    onboard(session, user)
    assert f"- How this student learns: {SAMPLE}" in chat_prompt(session, user)
    assert SAMPLE not in system_prompt("plain", None)


def test_english_preference_rule(session, user):
    onboard(session, user, chat_language="english")
    prompt = chat_prompt(session, user)
    assert "Reply in English." in prompt
    assert "reply in simple Hinglish" not in prompt


def test_no_prefs_keeps_the_mirror_rule(session, user):
    prompt = chat_prompt(session, user)
    assert ("- Match the student's style: if they write in Hinglish, reply in simple "
            "Hinglish; otherwise use simple English.") in prompt
    assert "Reply in English." not in prompt


def test_hint_prompt_has_style(session, user, problem, monkeypatch):
    onboard(session, user)
    attempt(session, user, problem, "3\n0\n")
    prompts = []

    def fake_invoke(purpose, prompt, **kwargs):
        prompts.append(prompt)
        return SimpleNamespace(status="ok", value="What does your code assume at the start?")

    monkeypatch.setattr("app.features.hints.service.llm_gateway.invoke", fake_invoke)
    hint = request_hint(session, user.id, problem.id, level=2)

    assert hint.source == "llm"
    assert f"HOW THIS STUDENT LIKES TO LEARN: {SAMPLE}" in prompts[0]


def test_feedback_context_has_style(session, user):
    onboard(session, user)
    assert _user_context(session, user.id)["style"] == style_line(session, user.id) == SAMPLE
