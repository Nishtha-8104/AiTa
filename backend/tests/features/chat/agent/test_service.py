"""A chat turn end to end: worker thread, events, persistence, memory. Scripted models only."""

import json
import threading

import pytest

from app.core.exceptions import LLMUnavailable, TurnInProgress
from app.features.chat.agent.middleware import BUDGET_FALLBACK, CODE_HIDDEN, REWRITE
from app.features.chat.agent.prompts import PLAIN_PROMPT
from app.features.chat.logic.moderation import SAFE_REPLY
from app.features.chat.models import EMBED_DIM, BookChunk, ChatMessage, ChatThread
from app.features.chat.service import (
    BUSY_REPLY,
    FAILED,
    Error,
    Final,
    Token,
    ToolEnd,
    ToolStart,
    _title,
    run_turn,
)
from tests.features.chat.agent.conftest import ScriptedModel, new_thread, tool_call
from tests.features.hints.test_hints import FakeHintLLM

HINT = "What does your program read first, and what must it print for it?"


def finish(turn) -> list:
    events = list(turn)
    assert turn.wait(timeout=30)
    return events


def stored(db) -> list[ChatMessage]:
    db.expire_all()
    return db.query(ChatMessage).order_by(ChatMessage.id).all()


def unit(axis: int) -> list[float]:
    return [1.0 if i == axis else 0.0 for i in range(EMBED_DIM)]


def test_books_are_searched_before_the_model_and_agent_searches_continue_the_refs(db, student):
    for source_id, position, vector in (
            ("beej", 0, [1.0, 0.1]), ("beej", 7, [1.0, 0.2]), ("modernc", 0, [1.0, 0.3]),
            ("kr", 0, [0.0, 1.0])):
        db.add(BookChunk(source_id=source_id, source_title=source_id.title(), license="CC",
                         url=f"https://x/{source_id}", chapter="Pointers", section="Arithmetic",
                         lang_tag="c", position=position, text=f"{source_id} passage",
                         embedding=vector + [0.0] * (EMBED_DIM - 2)))
    thread = new_thread(db, student)
    model = ScriptedModel(script=[tool_call("search_books", "c1", query="pointer to pointer"),
                                  "Adding 1 moves it one element on [1]; see also [3]."])

    events = finish(run_turn(
        db, student.id, thread.id, "How does pointer arithmetic work in C?", model=model,
        summary_model=ScriptedModel(),
        tool_ctx_overrides={"embed": lambda text: unit(0) if "arithmetic" in text else unit(1)},
    ))

    assert [type(e) for e in events] == [ToolStart, ToolEnd] * 2 + [Token, Final]
    auto, auto_end, agent, agent_end, token, final = events
    assert auto.args == {"query": "How does pointer arithmetic work in C?", "auto": True}
    assert (auto_end.trace["summary"], agent.args) == ("2 sources", {"query": "pointer to pointer"})
    prompt = model.calls[0].messages[0].content
    assert "Reference passages" in prompt and '"ref": 1, "title": "Beej"' in prompt
    assert '"ref": 2, "title": "Modernc"' in prompt and "Kr" not in prompt
    passages = json.loads(model.calls[1].messages[-1].content)["results"]
    assert [(p["title"], p["ref"]) for p in passages] == [
        ("Kr", 3), ("Modernc", 2), ("Beej", 1), ("Beej", 1)]
    assert token.text == final.content == "Adding 1 moves it one element on [1]; see also [3]."

    user_msg, reply = stored(db)
    assert (user_msg.role, reply.role, reply.id) == ("user", "assistant", final.message_id)
    assert [(c["name"], c["args"].get("auto")) for c in reply.tool_calls] == [
        ("search_books", True), ("search_books", None)]
    assert [c["title"] for c in reply.citations] == ["Beej", "Modernc", "Kr"]
    assert reply.citations == final.citations and reply.tool_calls == final.tool_calls
    assert db.get(ChatThread, thread.id).title == "How does pointer arithmetic work in C?"

    for message in ("stuck on pointer arithmetic, any hint?",
                    "Why does this pointer arithmetic fail?\n```c\np = p + 1;\n```"):
        quiet = finish(run_turn(db, student.id, thread.id, message,
                                model=ScriptedModel(script=["Try tracing it."]),
                                summary_model=ScriptedModel(),
                                tool_ctx_overrides={"embed": lambda text: unit(0)}))
        assert [type(e) for e in quiet] == [Token, Final]


def test_a_hint_is_the_reply_verbatim_and_the_model_is_not_asked_again(db, student):
    thread = new_thread(db, student)
    model = ScriptedModel(script=[
        tool_call("get_hint", "c1", level=1, language="c",
                  problem_text="Read two integers and print their sum."),
        "Just add them with a + b."])

    events = finish(run_turn(db, student.id, thread.id, "how do I start?", model=model,
                             summary_model=ScriptedModel(),
                             tool_ctx_overrides={"hint_runnable": FakeHintLLM(HINT)}))

    assert len(model.calls) == 1
    assert events[-1].content == stored(db)[-1].content == f"**Hint 1/4:** {HINT}"


def test_hint_requests_about_code_force_get_hint_and_other_questions_do_not(db, student):
    thread = new_thread(db, student)
    asks = ("I'm stuck, why does it fail?\n```c\nint main(void) { return 1; }\n```",
            "what is a pointer?", "give me a hint")
    models = [ScriptedModel(script=["ok"]) for _ in asks]
    for ask, model in zip(asks, models):
        finish(run_turn(db, student.id, thread.id, ask, model=model,
                        summary_model=ScriptedModel()))

    assert [m.calls[0].tool_choice for m in models] == ["get_hint", None, None]


PROGRAM = "```c\n#include <stdio.h>\nint main(void) {\n  return 0;\n}\n```"
PSEUDO = "1. Read n.\n2. Add each number to a running total.\n3. Print the total."


def test_chat_never_shows_a_complete_program(db, student):
    thread = new_thread(db, student)
    snippet = "```c\nint *a = malloc(n * sizeof *a);\nfree(a);\n```"
    turns = (["Use it like this:\n" + snippet],
             [PROGRAM, f"Steps:\n```text\n{PSEUDO}\n```"],
             [PROGRAM, "Still: " + PROGRAM])
    replies, models = [], []
    for script in turns:
        model = ScriptedModel(script=list(script))
        models.append(model)
        replies.append(finish(run_turn(db, student.id, thread.id, "full code please",
                                       model=model, summary_model=ScriptedModel()))[-1].content)

    assert replies[0].endswith(snippet) and len(models[0].calls) == 1
    assert replies[1] == f"Steps:\n```text\n{PSEUDO}\n```"
    assert models[1].calls[1].messages[-1].content == REWRITE
    assert "int main" not in replies[2] and CODE_HIDDEN in replies[2]
    assert stored(db)[-1].content == replies[2]


def test_citation_markers_without_sources_are_stripped_outside_code(db, student):
    thread = new_thread(db, student)
    model = ScriptedModel(script=[
        "A pointer stores an address [1][2]. Index with `a[1]` [3]:\n"
        "```c\n[1] = a[2];\n```\n[1] explains pointers in depth.\n- [2] Beej's guide"])

    events = finish(run_turn(db, student.id, thread.id, "what is a pointer?", model=model,
                             summary_model=ScriptedModel()))

    expected = "A pointer stores an address. Index with `a[1]`:\n```c\n[1] = a[2];\n```"
    assert events[-1].content == stored(db)[-1].content == expected
    assert events[-1].citations == []


def test_a_model_that_keeps_calling_tools_is_cut_off_at_five_and_still_answers(db, student):
    thread = new_thread(db, student)
    model = ScriptedModel(script=[tool_call("query_learning_data", f"c{i}", source="accuracy")
                                  for i in range(7)])

    events = finish(run_turn(db, student.id, thread.id, "what's my accuracy?", model=model,
                             summary_model=ScriptedModel()))

    assert [type(e) for e in events] == [ToolStart, ToolEnd] * 5 + [Token, Final]
    assert [(len(c.tools), c.tool_choice) for c in model.calls] == [(4, None)] * 5 + [(4, "none")]
    assert "used all your tool calls" in model.calls[-1].messages[0].content
    reply = stored(db)[-1]
    assert reply.content == events[-1].content == BUDGET_FALLBACK
    assert len(reply.tool_calls) == 5 and all(c["ok"] for c in reply.tool_calls)


def test_plain_thread_gets_no_tools_or_learner_context_but_keeps_moderation(db, student):
    thread = new_thread(db, student, mode="plain")
    model = ScriptedModel(script=["honestly, what a retard question"])

    events = finish(run_turn(db, student.id, thread.id, "what is a pointer?", "python",
                             model=model))

    assert [m.content for m in model.calls[0].messages] == [PLAIN_PROMPT, "what is a pointer?"]
    assert model.calls[0].tools == []
    assert [type(e) for e in events] == [Token, Final]
    assert events[0].text == events[1].content == SAFE_REPLY["slur"]
    reply = stored(db)[-1]
    assert (reply.moderation_flag, reply.tool_calls, reply.citations) == ("slur", None, None)


def test_abusive_message_gets_the_safe_reply_without_calling_the_model(db, student):
    thread = new_thread(db, student)
    model = ScriptedModel(script=["never used"])

    events = finish(run_turn(db, student.id, thread.id, "fuck you pet", model=model))

    assert model.calls == []
    assert [(type(e), e.content, e.moderation_flag) for e in events] == [
        (Final, SAFE_REPLY["abuse"], "abuse")]
    assert [(m.role, m.moderation_flag) for m in stored(db)] == [
        ("user", "abuse"), ("assistant", "abuse")]
    assert db.get(ChatThread, thread.id).title is None


def test_busy_and_failed_turns_are_saved_for_reload_but_kept_from_the_model(db, student):
    thread = new_thread(db, student)

    busy = finish(run_turn(db, student.id, thread.id, "what is recursion?",
                           model=ScriptedModel(script=[LLMUnavailable("gateway exhausted")]),
                           summary_model=ScriptedModel()))
    failed = finish(run_turn(db, student.id, thread.id, "and loops?",
                             model=ScriptedModel(script=[RuntimeError("provider fell over")]),
                             summary_model=ScriptedModel()))
    model = ScriptedModel(script=["Recursion is a function calling itself."])
    finish(run_turn(db, student.id, thread.id, "hello?", model=model,
                    summary_model=ScriptedModel()))

    assert [(type(e), e.content, e.moderation_flag) for e in busy] == [
        (Final, BUSY_REPLY, "busy")]
    assert [(type(e), e.message) for e in failed] == [(Error, FAILED)]
    assert [(m.role, m.content, m.moderation_flag) for m in stored(db)][:4] == [
        ("user", "what is recursion?", None), ("assistant", BUSY_REPLY, "busy"),
        ("user", "and loops?", None), ("assistant", FAILED, "error")]
    assert [m.content for m in model.calls[0].messages[1:]] == [
        "what is recursion?", "and loops?", "hello?"]


def test_code_help_thread_title_is_problem_name_and_question():
    content = ("Problem: Largest of N (problem_id 42)\n\nRead N numbers.\n\n"
               "Example input:\n3\n1 2 3\n\nMy question: why does it fail?")
    assert _title(content) == "Largest of N · why does it fail?"


def test_try_again_replaces_the_failed_exchange_instead_of_duplicating_it(db, student):
    thread = new_thread(db, student)
    finish(run_turn(db, student.id, thread.id, "what is recursion?",
                    model=ScriptedModel(script=[LLMUnavailable("gateway exhausted")]),
                    summary_model=ScriptedModel()))
    finish(run_turn(db, student.id, thread.id, "what is recursion? ",
                    model=ScriptedModel(script=["A function calling itself."]),
                    summary_model=ScriptedModel()))

    assert [(m.role, m.content, m.moderation_flag) for m in stored(db)] == [
        ("user", "what is recursion? ", None), ("assistant", "A function calling itself.", None)]


def test_turn_finishes_without_a_listener_and_rolls_old_messages_into_the_summary(db, student):
    thread = new_thread(db, student)
    for i in range(14):
        db.add(ChatMessage(thread_id=thread.id, user_id=student.id, role="user", content=f"q{i}"))
        db.add(ChatMessage(thread_id=thread.id, user_id=student.id, role="assistant",
                           content=f"a{i}"))
    db.commit()
    gate = threading.Event()
    summariser = ScriptedModel(script=["Asked q0 to q9 about loops."])
    model = ScriptedModel(script=[tool_call("query_learning_data", "c1", source="mastery"),
                                  lambda: gate.wait(10) and "Here is where you stand."])

    turn = run_turn(db, student.id, thread.id, "q14", model=model, summary_model=summariser)
    assert isinstance(next(turn), ToolStart)
    with pytest.raises(TurnInProgress):
        run_turn(db, student.id, thread.id, "hello?", model=ScriptedModel())
    gate.set()
    assert turn.wait(timeout=30)

    assert [m.content for m in stored(db)][-3:] == ["a13", "q14", "Here is where you stand."]
    assert len(model.calls[0].messages) == 1 + 29
    sent = summariser.calls[0].messages[0].content
    assert "Student: q0" in sent and "PET: a9" in sent and "q10" not in sent
    db.expire_all()
    folded = db.get(ChatThread, thread.id)
    assert (folded.summary, folded.summary_upto) == ("Asked q0 to q9 about loops.", 20)

    follow_up = ScriptedModel(script=["Sure."])
    finish(run_turn(db, student.id, thread.id, "q15", model=follow_up,
                    summary_model=ScriptedModel()))
    system, first, *_, last = follow_up.calls[0].messages
    assert "Earlier in this conversation: Asked q0 to q9 about loops." in system.content
    assert (first.content, last.content) == ("q10", "q15")
    assert len(follow_up.calls[0].messages) == 1 + 5 * 2 + 1
