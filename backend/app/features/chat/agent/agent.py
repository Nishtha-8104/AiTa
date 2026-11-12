"""The chat agent graph for a thread's mode: pet (tools, learner context, memory
guard) or plain (the study baseline: one-line prompt, no tools, no context)."""

from collections.abc import Sequence

from langchain.agents import create_agent
from langchain.agents.middleware import (
    AgentMiddleware,
    SummarizationMiddleware,
    ToolCallLimitMiddleware,
)
from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool

from app.core.llm_gateway import gateway_chat_model
from app.features.chat.agent.context import ChatContext
from app.features.chat.agent.middleware import (
    TOOL_CALL_LIMIT,
    AnswerWithinBudget,
    ChatState,
    NoFullPrograms,
    moderation_in,
    moderation_out,
)
from app.features.chat.agent.prompts import system_prompt

# Cross-turn memory is the thread's rolling summary (service.py). This only compacts a
# single turn whose pasted code and tool results outgrow the fallback model's context.
TURN_TOKEN_LIMIT = 24_000
KEEP_MESSAGES = 10


def build_agent(mode: str, ctx: ChatContext | None, tools: Sequence[BaseTool],
                model: BaseChatModel, summary_model: BaseChatModel | None = None, *,
                middleware: Sequence[AgentMiddleware] = ()):
    if mode == "plain":
        return create_agent(model, [], system_prompt=system_prompt("plain", None),
                            state_schema=ChatState,
                            middleware=[moderation_in, *middleware, moderation_out])
    return create_agent(
        model, list(tools), system_prompt=system_prompt(mode, ctx), state_schema=ChatState,
        middleware=[
            moderation_in,
            SummarizationMiddleware(model=summary_model or gateway_chat_model("chat_summary"),
                                    trigger=("tokens", TURN_TOKEN_LIMIT),
                                    keep=("messages", KEEP_MESSAGES)),
            ToolCallLimitMiddleware(run_limit=TOOL_CALL_LIMIT),
            AnswerWithinBudget(TOOL_CALL_LIMIT),
            NoFullPrograms(),
            *middleware,
            moderation_out,
        ],
    )
