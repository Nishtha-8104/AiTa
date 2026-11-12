import logging
from functools import lru_cache
from typing import Any, Optional

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ConfigDict

from app.features.gamification import service as gamification
from app.features.learner_model import service
from app.features.learner_model.models import LearningEvent
from app.features.learner_model.service import EventInput

logger = logging.getLogger(__name__)


class ProfilingState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    db: Any
    event_in: EventInput
    event: Optional[LearningEvent] = None


def record_event(state: ProfilingState) -> ProfilingState:
    state.event = service.record_event(state.db, state.event_in)
    return state


def update_mastery(state: ProfilingState) -> ProfilingState:
    service.update_mastery(state.db, state.event)
    return state


def gamify(state: ProfilingState) -> ProfilingState:
    """Awards ride in a savepoint: a failure here costs the awards, never the evidence."""
    try:
        with state.db.begin_nested():
            gamification.apply(state.db, state.event)
    except Exception:
        logger.exception("gamification failed for event %s", state.event.id)
    return state


def derive_profile(state: ProfilingState) -> ProfilingState:
    service.derive_profile(state.db, state.event_in.user_id)
    state.db.commit()
    return state


@lru_cache(maxsize=1)
def build_profiling_graph():
    graph = StateGraph(ProfilingState)
    graph.add_node("record_event", record_event)
    graph.add_node("update_mastery", update_mastery)
    graph.add_node("gamify", gamify)
    graph.add_node("derive_profile", derive_profile)
    graph.add_edge(START, "record_event")
    graph.add_edge("record_event", "update_mastery")
    graph.add_edge("update_mastery", "gamify")
    graph.add_edge("gamify", "derive_profile")
    graph.add_edge("derive_profile", END)
    return graph.compile()


def ingest(db, event_in: EventInput) -> LearningEvent:
    """The single entry point every grader calls with its evidence."""
    result = build_profiling_graph().invoke(ProfilingState(db=db, event_in=event_in))
    final = result if isinstance(result, ProfilingState) else ProfilingState(**result)
    return final.event
