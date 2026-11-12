import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.features  # noqa: F401  -- registers every table on Base.metadata
from app.core.database import Base
from app.features.grading.logic.execution.base import (
    ExecLimits, ExecResult, ExecStatus, ExecutionProvider,
)


@pytest.fixture(scope="session", autouse=True)
def no_live_llm_client():
    """No test anywhere may build a real client, whatever a key in the environment
    would otherwise allow: the free tier this project runs on is metered, and a
    stray call spends it silently.

    `app.core.llm._nvidia` is the single place `ChatOpenAI` is constructed, so
    patching it there covers `get_chat_model` and `get_codegen_model` both. The
    error must not be an `openai.OpenAIError`: `_nvidia` catches that one and
    degrades it to `LLMUnavailable`, which several tests expect — the guard would
    be swallowed into a passing test instead of a loud failure.
    """
    def explode(*args, **kwargs):
        raise AssertionError(
            "a test tried to construct a real LLM client: patch the model call "
            "instead of letting it reach the provider"
        )

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("app.core.llm.ChatOpenAI", explode)
        yield


@pytest.fixture(scope="session", autouse=True)
def hints_clear_the_fix_check():
    """The fix check is an LLM judge; hint tests that are not about it see every hint
    cleared. Its own tests call the real function, imported before this patch."""
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("app.features.hints.logic.guardrail.states_fix", lambda *a, **k: False)
        yield


@pytest.fixture(scope="session", autouse=True)
def no_embedder_model():
    """Startup warm-up is off, and loading the real sentence-transformers model fails
    loudly: tests pass their own `embed`."""
    def explode():
        raise AssertionError("a test tried to load the real embedding model: pass embed=")

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("app.core.config.settings.SKIP_EMBED_WARMUP", True)
        patch.setattr("app.features.chat.logic.rag.embedder._load_model", explode)
        yield


@pytest.fixture(scope="session", autouse=True)
def no_onboarding_sweep():
    """The theory sweep loop opens real database sessions; an app started in a test
    must not run it."""
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("app.core.config.settings.SKIP_ONBOARDING_SWEEP", True)
        yield


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with sessionmaker(bind=engine)() as db:
        yield db


class FakeExecutionProvider(ExecutionProvider):
    def __init__(self, results: list[ExecResult]):
        self.results = results
        self.calls: list[dict] = []

    def run_batch(self, language, source, stdins, limits):
        self.calls.append({"language": language, "source": source, "stdins": list(stdins)})
        return self.results[: len(stdins)]


def ok(stdout: str, time_ms: int = 5) -> ExecResult:
    return ExecResult(status=ExecStatus.OK, stdout=stdout, time_ms=time_ms)


def failing(status: ExecStatus, stderr: str = "",
            compile_output: str | None = None) -> ExecResult:
    return ExecResult(status=status, stderr=stderr, compile_output=compile_output)


@pytest.fixture
def limits():
    return ExecLimits()
