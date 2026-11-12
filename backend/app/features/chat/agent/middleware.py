"""Agent middleware: moderation on the way in and out, a forced answer once the tool
budget is spent, no complete programs in replies, tool-built replies shown verbatim, hint
requests routed to get_hint, and tool start/end callbacks for the event stream."""

import json
import re
import threading
from collections.abc import Callable
from dataclasses import asdict
from typing import Any

from langchain.agents.middleware import (
    AgentMiddleware,
    AgentState,
    ModelResponse,
    after_model,
    before_model,
    hook_config,
)
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    RemoveMessage,
    SystemMessage,
    ToolMessage,
)
from typing_extensions import NotRequired

from app.features.chat.agent.tools import ToolContext, ToolTrace
from app.features.chat.logic import moderation

TOOL_CALL_LIMIT = 5
ARG_CHARS = 200
BUDGET_SPENT = ("You have used all your tool calls for this message. Answer now with what "
                "you have, and say briefly if something could not be checked.")
BUDGET_FALLBACK = ("I couldn't finish checking everything for this question. Could you ask "
                   "again, maybe a little more specifically?")


class ChatState(AgentState):
    moderation_flag: NotRequired[str | None]
    code_rewritten: NotRequired[bool]


@before_model(state_schema=ChatState, can_jump_to=["end"])
def moderation_in(state: ChatState, runtime) -> dict | None:
    messages = state["messages"]
    if not messages or not isinstance(messages[-1], HumanMessage):
        return None
    verdict = moderation.check(messages[-1].text)
    if not verdict.flagged:
        return None
    return {"messages": [AIMessage(content=moderation.SAFE_REPLY[verdict.category])],
            "moderation_flag": verdict.category, "jump_to": "end"}


@after_model(state_schema=ChatState)
def moderation_out(state: ChatState, runtime) -> dict | None:
    last = state["messages"][-1]
    if not isinstance(last, AIMessage) or last.tool_calls:
        return None
    verdict = moderation.check(last.text)
    if not verdict.flagged:
        return None
    return {"messages": [AIMessage(id=last.id, content=moderation.SAFE_REPLY[verdict.category],
                                   response_metadata=last.response_metadata,
                                   usage_metadata=last.usage_metadata)],
            "moderation_flag": verdict.category}


SNIPPET_LINES = 10
_FENCE = re.compile(r"```([^\n`]*)\n(.*?)(?:```|$)", re.DOTALL)
_PROGRAM = re.compile(r"\bmain\s*\(|\bif\s+__name__\s*==")
_PROSE_TAGS = {"text", "txt", "pseudocode", "plaintext", "output", "console"}
REWRITE = ("Your reply contains a complete program or a code block longer than 10 lines, "
           "which PET never shows. Rewrite it: give the main logic as numbered plain-English "
           "pseudocode in a ```text block, and keep any real code to one short snippet of at "
           "most 10 lines for a specific construct.")
CODE_HIDDEN = ("```text\nFull code is not shown in PET. Work from the steps above, or ask "
               "for a hint.\n```")


def _too_much_code(tag: str, body: str) -> bool:
    if _PROGRAM.search(body):
        return True
    if tag.strip().lower() in _PROSE_TAGS:
        return False
    return sum(1 for line in body.splitlines() if line.strip()) > SNIPPET_LINES


def _has_program(text: str) -> bool:
    return any(_too_much_code(tag, body) for tag, body in _FENCE.findall(text))


def _hide_programs(text: str) -> str:
    return _FENCE.sub(lambda m: CODE_HIDDEN if _too_much_code(*m.groups()) else m.group(0), text)


class NoFullPrograms(AgentMiddleware):
    """Chat never shows a complete program: pseudocode for the logic, snippets of at most
    SNIPPET_LINES for syntax. A reply that breaks this is rewritten once; if the rewrite
    still breaks it, the offending blocks are replaced."""

    state_schema = ChatState

    @hook_config(can_jump_to=["model"])
    def after_model(self, state: ChatState, runtime) -> dict | None:
        last = state["messages"][-1]
        if not isinstance(last, AIMessage) or last.tool_calls or not _has_program(last.text):
            return None
        if not state.get("code_rewritten"):
            return {"messages": [RemoveMessage(id=last.id), HumanMessage(content=REWRITE)],
                    "code_rewritten": True, "jump_to": "model"}
        return {"messages": [AIMessage(id=last.id, content=_hide_programs(last.text),
                                       response_metadata=last.response_metadata,
                                       usage_metadata=last.usage_metadata)]}


class AnswerWithinBudget(AgentMiddleware):
    """ToolCallLimitMiddleware only blocks calls past the limit and lets the model try
    again, which a stubborn model can repeat forever. Once the budget is spent the model
    is told not to call tools, and any call it makes anyway is dropped, so this reply
    ends the turn. Tools stay declared: the history holds tool calls, which some
    OpenAI-compatible servers reject without the tool definitions."""

    def __init__(self, limit: int = TOOL_CALL_LIMIT):
        super().__init__()
        self.limit = limit

    def _used(self, request) -> int:
        counts = request.state.get("run_tool_call_count")
        if counts:
            return counts.get("__all__", 0)
        return sum(isinstance(m, ToolMessage) for m in request.messages)

    def wrap_model_call(self, request, handler) -> ModelResponse:
        if self._used(request) < self.limit:
            return handler(request)
        prompt = f"{request.system_prompt}\n\n{BUDGET_SPENT}" if request.system_prompt else BUDGET_SPENT
        response = handler(request.override(tool_choice="none",
                                            system_message=SystemMessage(content=prompt)))
        return ModelResponse(result=[
            AIMessage(id=m.id, content=m.text.strip() or BUDGET_FALLBACK,
                      response_metadata=m.response_metadata, usage_metadata=m.usage_metadata)
            if isinstance(m, AIMessage) and m.tool_calls else m
            for m in response.result
        ], structured_response=response.structured_response)


def _clip_args(args: dict) -> dict:
    return {k: v if not isinstance(v, str) or len(v) <= ARG_CHARS else v[: ARG_CHARS - 1] + "…"
            for k, v in args.items()}


def trace_dict(trace: ToolTrace) -> dict:
    return {k: v for k, v in asdict(trace).items() if k != "citations"}


def citations_from(traces: list[ToolTrace]) -> list[dict]:
    """Every book source of the turn, in first-seen order; [n] in the reply is item n."""
    seen: list[dict] = []
    for trace in traces:
        for cite in trace.citations or ():
            if cite not in seen:
                seen.append(cite)
    return seen


def _with_refs(message: ToolMessage, citations: list[dict]) -> ToolMessage:
    try:
        payload = json.loads(message.content)
    except (TypeError, ValueError):
        return message
    refs = {(c["title"], c["chapter"], c["section"], c["url"]): n
            for n, c in enumerate(citations, 1)}
    payload["results"] = [
        {"ref": refs.get((r.get("title"), r.get("chapter"), r.get("section"), r.get("url"))), **r}
        for r in payload.get("results", [])
    ]
    return message.model_copy(update={"content": json.dumps(payload, ensure_ascii=False)})


class FixedReply(AgentMiddleware):
    """A failing evaluation or a hint ends the turn exactly as the tool built it: a model
    retelling either one adds the diagnosis or the fix back, past the hint guardrail."""

    state_schema = ChatState

    def __init__(self, ctx: ToolContext):
        super().__init__()
        self.ctx = ctx

    @hook_config(can_jump_to=["end"])
    def before_model(self, state: ChatState, runtime) -> dict | None:
        if self.ctx.fixed_reply is None or not isinstance(state["messages"][-1], ToolMessage):
            return None
        return {"messages": [AIMessage(content=self.ctx.fixed_reply)], "jump_to": "end"}


_HINT_ASK = re.compile(
    r"\b(?:hints?|clue|stuck|nudge)\b|\bwhat'?s wrong\b|\bkya galat\b|\batak\w*\b"
    r"|\bsamajh\s+nahi\b|\bwhy\b.*\b(?:wrong|fail\w*|not\s+work\w*)\b",
    re.IGNORECASE | re.DOTALL)


class ForceHint(AgentMiddleware):
    """Asked for a hint about a known problem, the first model call must call get_hint:
    left to choose, the model sometimes writes a hint of its own, fix included."""

    def __init__(self, ctx: ToolContext):
        super().__init__()
        self.ctx = ctx

    def wrap_model_call(self, request, handler) -> ModelResponse:
        last = request.messages[-1] if request.messages else None
        if (isinstance(last, HumanMessage) and _HINT_ASK.search(last.text)
                and (self.ctx.last_attempt is not None or "```" in last.text)):
            return handler(request.override(tool_choice="get_hint"))
        return handler(request)


class ToolEvents(AgentMiddleware):
    """Reports each tool call as it starts and ends, and numbers book passages with the
    same refs as the citations stored on the reply."""

    def __init__(self, ctx: ToolContext, on_start: Callable[[str, dict], Any],
                 on_end: Callable[[dict], Any]):
        super().__init__()
        self.ctx = ctx
        self.on_start = on_start
        self.on_end = on_end
        # Parallel calls of one step run on separate threads; one at a time keeps each
        # start/end pair together and ctx.traces[-1] pointing at the call just made.
        self._lock = threading.Lock()

    def wrap_tool_call(self, request, handler) -> ToolMessage:
        call = request.tool_call
        args = _clip_args(call.get("args") or {})
        with self._lock:
            self.on_start(call["name"], args)
            before = len(self.ctx.traces)
            if request.tool is None:
                result = ToolMessage(content=f"Unknown tool {call['name']!r}.",
                                     tool_call_id=call["id"], name=call["name"], status="error")
            else:
                result = handler(request)
            if len(self.ctx.traces) == before:
                self.ctx.traces.append(ToolTrace(name=call["name"], args=args,
                                                 summary="unknown tool", ok=False, ms=0))
            trace = self.ctx.traces[-1]
            if trace.citations and isinstance(result, ToolMessage):
                result = _with_refs(result, citations_from(self.ctx.traces))
            self.on_end(trace_dict(trace))
        return result
