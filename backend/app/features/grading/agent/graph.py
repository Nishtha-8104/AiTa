"""The Evaluation Agent's LangGraph: route -> analyse -> ensure tests -> run -> explain (when
useful) -> score -> L1 hint. evaluate_submission runs it, persists the report and hands a
verified result to Profiling."""

import time
from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.features.grading.agent.nodes.analyse import analyse
from app.features.grading.agent.nodes.emit_event import emit_event
from app.features.grading.agent.nodes.ensure_tests import ensure_tests
from app.features.grading.agent.nodes.execute_student import execute_student
from app.features.grading.agent.nodes.explain import explain
from app.features.grading.agent.nodes.hint_l1 import hint_l1, log_l1
from app.features.grading.agent.nodes.persist import persist
from app.features.grading.agent.nodes.route_mode import route_mode
from app.features.grading.agent.nodes.score import score
from app.features.grading.agent.schemas import EvalReport
from app.features.grading.agent.state import EvalState
from app.features.hints.service import HintSource


def _after_execute(state: EvalState) -> str:
    clean_pass = (state.verification_status == "verified" and state.tests_total
                  and state.tests_passed == state.tests_total)
    if state.halted or (not clean_pass and not state.explain_failures):
        return "score"
    return "explain"


@lru_cache(maxsize=1)
def build_eval_graph():
    graph = StateGraph(EvalState)
    graph.add_node("route_mode", route_mode)
    graph.add_node("analyse", analyse)
    graph.add_node("ensure_tests", ensure_tests)
    graph.add_node("execute_student", execute_student)
    graph.add_node("explain", explain)
    graph.add_node("score", score)

    graph.add_edge(START, "route_mode")
    graph.add_edge("route_mode", "analyse")
    graph.add_edge("analyse", "ensure_tests")
    graph.add_edge("ensure_tests", "execute_student")
    graph.add_conditional_edges(
        "execute_student", _after_execute, {"explain": "explain", "score": "score"}
    )
    graph.add_node("hint_l1", hint_l1)
    graph.add_edge("explain", "score")
    graph.add_edge("score", "hint_l1")
    graph.add_edge("hint_l1", END)
    return graph.compile()


def evaluate_submission(db, submission_id: int, user_id: int, *, provider=None,
                        generator=None, explain_runnable=None, emit: bool = True,
                        hint_source: HintSource = "practice",
                        explain_failures: bool = True) -> EvalReport:
    started_ms = int(time.time() * 1000)
    state = EvalState(
        db=db, submission_id=submission_id, user_id=user_id, provider=provider,
        generator=generator, explain_runnable=explain_runnable,
        explain_failures=explain_failures,
    )
    result = build_eval_graph().invoke(state)
    final = result if isinstance(result, EvalState) else EvalState(**result)
    persist(final, started_ms=started_ms)
    if emit:
        emit_event(final)
    log_l1(final, source=hint_source)
    return final.report
