"""Chat agent tools over sqlite, with a fake executor, explainer, hint LLM and embedder."""

import json

from app.core.exceptions import ExecutorUnavailable, LLMUnavailable
from app.features.accounts.models import User
from app.features.chat.agent.tools import (
    UNVERIFIED_REPLY,
    LastAttempt,
    ToolContext,
    _keep_lines,
    _usable,
    build_tools,
)
from app.features.chat.models import EMBED_DIM, BookChunk
from app.features.grading.logic.execution.base import ExecStatus
from app.features.grading.models import CodeSubmission
from app.features.hints.models import HintEvent
from app.features.hints.service import next_level
from app.features.learner_model.models import LearningEvent
from app.features.problems.models import Problem, ProblemSource
from tests.conftest import FakeExecutionProvider, failing
from tests.features.grading.test_graph import (
    SUM_STATEMENT,
    FakeExplainRunnable,
    gen_then_student,
    generated_tests,
    merged,
    ok,
)
from tests.features.hints import test_hints as base
from tests.features.hints.test_hints import FakeHintLLM

user = base.user
problem = base.problem

C_MAX = "#include <stdio.h>\nint main(void) { int a; scanf(\"%d\", &a); printf(\"%d\\n\", a); }"


def tools_for(session, user, **kwargs) -> tuple[ToolContext, dict]:
    ctx = ToolContext(db=session, user_id=user.id, language="c",
                      eval_kwargs={"explain_runnable": FakeExplainRunnable()}, **kwargs)
    return ctx, {tool.name: tool for tool in build_tools(ctx)}


def call(tools, name, **args) -> dict:
    return json.loads(tools[name].invoke(args).split("\n\n", 1)[0])


def test_evaluate_code_needs_a_problem_then_falls_back_to_the_last_bank_attempt(
        session, user, problem):
    ctx, tools = tools_for(session, user)
    assert call(tools, "evaluate_code", code=C_MAX, language="c") == {
        "error": "need_problem", "message": "Ask the student for the problem statement."}
    assert session.query(CodeSubmission).count() == 0

    ctx.last_attempt = LastAttempt(problem.id, "Largest", "Wrong answer", 0, 2)
    ctx.provider = FakeExecutionProvider(merged("3\n0\n"))
    result = call(tools, "evaluate_code", code=C_MAX, language="C")
    assert ctx.fixed_reply == (
        "**Wrong answer on test 2** · 1/2 tests passed\n\nInput:\n```\n-4 -9\n```\n\n"
        "Expected:\n```\n-4\n```\n\nYour output:\n```\n0\n```\n\n"
        "Want a hint? Ask and I'll start with a gentle one.")

    assert (result["problem_id"], result["passed"], result["total"]) == (problem.id, 1, 2)
    assert result["verdict"] == "Wrong answer on test 2"
    assert result["first_failing"]["expected"] == "-4"
    assert result["first_failing"]["actual"] == "0"
    assert "feedback" not in result and "issues" not in result
    assert ctx.eval_kwargs["explain_runnable"].prompts == []
    assert session.query(CodeSubmission).one().from_bank is True
    assert session.query(LearningEvent).count() == 0
    assert [(t.ok, t.summary) for t in ctx.traces] == [
        (False, "need problem"), (True, "1/2 tests passed")]


def test_pasted_problem_becomes_a_student_problem_without_mastery_evidence(session, user):
    ctx, tools = tools_for(session, user)
    ctx.provider = gen_then_student([ok("1\n"), ok("2\n"), ok("3\n")], merged("1\n2\n3\n"))
    ctx.eval_kwargs["generator"] = lambda **k: generated_tests()

    result = call(tools, "evaluate_code", code="print(1)", language="python",
                  problem_id=4242, problem_text=SUM_STATEMENT)

    pasted = session.query(Problem).one()
    assert (pasted.source, pasted.created_by_user_id) == (ProblemSource.STUDENT, user.id)
    assert (result["problem_id"], result["passed"], result["total"]) == (pasted.id, 3, 3)
    assert result["first_failing"] is None
    assert session.query(CodeSubmission).one().from_bank is False
    assert session.query(LearningEvent).count() == 0


def test_unverified_run_gets_the_fixed_not_checked_reply_without_an_explanation(session, user):
    ctx, tools = tools_for(session, user)
    ctx.provider = FakeExecutionProvider([ok("1\n")])

    def no_tests(**kwargs):
        raise LLMUnavailable("provider down")

    ctx.eval_kwargs["generator"] = no_tests
    result = call(tools, "evaluate_code", code="print(1)", language="python",
                  problem_text=SUM_STATEMENT)

    assert result["unverified_reason"] == "test_generation_failed"
    assert ctx.fixed_reply == UNVERIFIED_REPLY
    assert ctx.eval_kwargs["explain_runnable"].prompts == []


def test_get_hint_paths(session, user, problem):
    llm = FakeHintLLM("Which value should the running maximum start from?")
    ctx, tools = tools_for(session, user, hint_runnable=llm)

    approach = call(tools, "get_hint", level=3, language="c++", problem_id=problem.id)
    assert approach == {"level": 3, "hint": llm.replies[0], "problem_id": problem.id}
    assert ctx.fixed_reply == f"**Hint 3/4:** {llm.replies[0]}"
    assert "APPROACH LEVEL 3" in llm.prompts[-1]

    ctx.provider = FakeExecutionProvider(merged("3\n0\n"))
    call(tools, "evaluate_code", code=C_MAX, language="c", problem_id=problem.id)
    ladder = call(tools, "get_hint", level=2, language="c", problem_id=problem.id,
                  code=C_MAX + "\n")
    assert (ladder["level"], ladder["hint"]) == (2, llm.replies[0])
    assert "HINT LEVEL 2" in llm.prompts[-1]
    assert session.query(CodeSubmission).count() == 1

    ctx.provider = FakeExecutionProvider([failing(ExecStatus.COMPILE_ERROR,
                                                  compile_output="error: expected ';'")])
    call(tools, "evaluate_code", code="int main( {", language="c", problem_id=problem.id)
    broken = call(tools, "get_hint", level=2, language="c", problem_id=problem.id,
                  code="int main( {")
    assert broken["compiled"] is False and "expected ';'" in broken["compile_output"]
    assert "hint" not in broken

    ctx.provider = FakeExecutionProvider(merged("3\n-4\n"))
    passed = call(tools, "get_hint", level=4, language="c", problem_id=problem.id,
                  code=C_MAX + "// fixed")
    assert passed["passed"] is True and "hint" not in passed

    events = session.query(HintEvent).order_by(HintEvent.id).all()
    assert [(e.source, e.level, e.evaluation_id is None) for e in events] == [
        ("chat", 3, True), ("chat", 1, False), ("chat", 2, False)]
    assert next_level(session, user.id, problem.id) == 1
    assert [t.summary for t in ctx.traces] == [
        "hint L3", "1/2 tests passed", "hint L2", "compile error", "compile error",
        "all tests pass"]


def test_hint_lines_survive_markdown_but_code_fences_stay_untouched():
    text = "Your code fails on this input:\n3\n1 2 3\nTrace it.\n```c\nsum += x;\n```"
    assert _keep_lines(text) == ("Your code fails on this input:  \n3  \n1 2 3  \nTrace it.  \n"
                                 "```c\nsum += x;\n```")


def test_failures_become_error_json_and_failed_traces(session, user, monkeypatch):
    other = User(email="o@example.com", username="other")
    session.add(other)
    session.flush()
    private = Problem(source=ProblemSource.STUDENT, statement="theirs", statement_hash="o" * 64,
                      created_by_user_id=other.id)
    shared = Problem(source=ProblemSource.GENERATED, statement="generated", statement_hash="g" * 64,
                     created_by_user_id=other.id)
    session.add_all([private, shared])
    session.commit()
    ctx, tools = tools_for(session, user)
    assert _usable(ctx, shared.id) and not _usable(ctx, private.id)

    def down(*args, **kwargs):
        raise ExecutorUnavailable("connect /var/run/docker.sock refused")

    monkeypatch.setattr("app.features.chat.agent.tools.learning_data.query", down)
    crashed = call(tools, "query_learning_data", source="accuracy")
    unknown_source = call(tools, "query_learning_data", source="grades")
    bad_language = call(tools, "evaluate_code", code=C_MAX, language="java", problem_id=1)
    not_theirs = call(tools, "evaluate_code", code=C_MAX, language="c", problem_id=private.id)
    bad_level = call(tools, "get_hint", level=7, language="c")

    assert crashed["error"] == "tool_failed" and "docker" not in crashed["message"]
    assert unknown_source["error"] == bad_level["error"] == "invalid_arguments"
    assert bad_language["error"] == "invalid_language"
    assert not_theirs["error"] == "unknown_problem"
    assert not any(t.ok for t in ctx.traces) and len(ctx.traces) == 5
    assert ctx.traces[1].args == {"source": "grades"}
    assert session.query(CodeSubmission).count() == 0


def test_search_books_returns_trimmed_passages_and_citation_traces(session, user):
    def chunk(source_id, position, vec_head, lang="c"):
        session.add(BookChunk(
            source_id=source_id, source_title=source_id.title(), license="CC BY 4.0",
            url=f"https://x/{source_id}", chapter="Pointers", section="Arithmetic",
            lang_tag=lang, position=position, text="p" * 2000,
            embedding=[1.0, vec_head] + [0.0] * (EMBED_DIM - 2),
        ))

    chunk("beej", 0, 0.1)
    chunk("beej", 7, 0.2)
    chunk("modernc", 0, 0.3)
    chunk("py4e", 0, 0.0, lang="python")
    session.commit()
    ctx, tools = tools_for(session, user,
                           embed=lambda text: [1.0, 0.0] + [0.0] * (EMBED_DIM - 2))

    result = call(tools, "search_books", query="pointer arithmetic")

    assert not session.in_transaction()
    assert [r["title"] for r in result["results"]] == ["Beej", "Beej", "Modernc"]
    assert all(len(r["text"]) <= 700 for r in result["results"])
    trace = ctx.traces[0]
    assert (trace.ok, trace.summary) == (True, "2 sources")
    assert trace.citations == [
        {"title": "Beej", "chapter": "Pointers", "section": "Arithmetic", "url": "https://x/beej"},
        {"title": "Modernc", "chapter": "Pointers", "section": "Arithmetic",
         "url": "https://x/modernc"},
    ]
