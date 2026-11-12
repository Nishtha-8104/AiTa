"""Real chat turns, in-process, for the eval scripts: a dedicated eval account per script,
a fresh thread per item, and each turn's events folded into one TurnResult."""

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.features.accounts.models import User
from app.features.accounts.service import AuthService
from app.features.chat.models import ChatThread
from app.features.chat.service import BUSY_FLAG, FAILED_FLAG, Error, Final, ToolStart, run_turn
from scripts._local_db import require_local_db

TURN_WAIT_S = 600
CLIP = 4000


@dataclass
class TurnResult:
    content: str = ""
    tools: list[str] = field(default_factory=list)
    tool_calls: list[dict] = field(default_factory=list)
    citations: list[dict] = field(default_factory=list)
    flag: str | None = None
    error: str | None = None

    @property
    def failed(self) -> bool:
        """Busy or broken turns are not results; the item is left for the next run."""
        return self.error is not None or self.flag in (BUSY_FLAG, FAILED_FLAG)


def clip(text: str | None, limit: int = CLIP) -> str | None:
    return text if text is None or len(text) <= limit else text[: limit - 1] + "…"


def eval_user(db: Session, email: str) -> User:
    require_local_db(db.get_bind().url)
    user =db.query(User).filter(User.email == email).first()
    if user is not None:
        return user
    username = email.split("@")[0].replace("-", "_").replace(".", "_")[:50]
    return AuthService.create_user(db, email, username, "Chat eval")


def new_thread(db: Session, user_id: int, mode: str = "pet") -> int:
    thread = ChatThread(user_id=user_id, mode=mode)
    db.add(thread)
    db.commit()
    return thread.id


def ask(db: Session, user_id: int, thread_id: int, text: str,
        language: str | None = None) -> TurnResult:
    turn = run_turn(db, user_id, thread_id, text, language)
    result = TurnResult()
    for event in turn:
        if isinstance(event, ToolStart):
            result.tools.append(event.name)
        elif isinstance(event, Final):
            result.content = event.content
            result.tool_calls = event.tool_calls
            result.citations = event.citations
            result.flag = event.moderation_flag
        elif isinstance(event, Error):
            result.error = event.message
    turn.wait(TURN_WAIT_S)
    return result
