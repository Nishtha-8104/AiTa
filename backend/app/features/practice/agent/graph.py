from functools import lru_cache
from typing import Any, Optional

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict

from app.core.topics import TOPIC_LABELS
from app.features.practice.logic.assessment import policy
from app.features.practice.logic.assessment.policy import NextItem, NothingToServe, Plan


class AssessmentState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    db: Any
    user_id: int
    plan: Optional[Plan] = None
    candidates: list[str] = []
    rotated_from: Optional[str] = None
    result: Optional[NextItem] = None


def load_profile(state: AssessmentState) -> AssessmentState:
    state.plan = policy.load_profile(state.db, state.user_id)
    return state


def choose_topic(state: AssessmentState) -> AssessmentState:
    ranked = policy.ranked_topics(state.plan)
    stuck = policy.stuck_topic(state.db, state.user_id)
    if stuck in ranked and len(ranked) > 1:
        ranked = [t for t in ranked if t != stuck] + [stuck]
        state.rotated_from = stuck
    state.candidates = ranked
    return state


def pick_item(state: AssessmentState) -> AssessmentState:
    """Walk the ranked topics until one has something to serve; for each, type and
    difficulty follow from its mastery."""
    for topic in state.candidates:
        plan = state.plan
        plan.topic = topic
        plan.item_type = policy.choose_type(state.db, plan, topic)
        plan.difficulty = policy.choose_difficulty(plan.topics[topic].mastery)
        plan.notes = []
        if state.rotated_from and topic != state.rotated_from:
            plan.notes.append(f"you missed {TOPIC_LABELS[state.rotated_from]} "
                              f"{policy.STUCK_AFTER} times in a row, so one item from "
                              "another topic first")
        state.result = policy.pick_item(state.db, plan)
        if state.result is not None:
            return state
    raise NothingToServe("Every item in the bank has been completed.")


@lru_cache(maxsize=1)
def build_assessment_graph():
    graph = StateGraph(AssessmentState)
    graph.add_node("load_profile", load_profile)
    graph.add_node("choose_topic", choose_topic)
    graph.add_node("pick_item", pick_item)
    graph.add_edge(START, "load_profile")
    graph.add_edge("load_profile", "choose_topic")
    graph.add_edge("choose_topic", "pick_item")
    graph.add_edge("pick_item", END)
    return graph.compile()


def next_item(db, user_id: int) -> NextItem:
    result = build_assessment_graph().invoke(AssessmentState(db=db, user_id=user_id))
    final = result if isinstance(result, AssessmentState) else AssessmentState(**result)
    return final.result
