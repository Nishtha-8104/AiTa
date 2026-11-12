"""Picks the configured execution provider; only the executor sidecar exists."""

from functools import lru_cache

from app.core.config import settings
from app.features.grading.logic.execution.base import ExecutionProvider
from app.features.grading.logic.execution.sidecar import SidecarProvider


@lru_cache(maxsize=1)
def get_provider() -> ExecutionProvider:
    name = settings.EXECUTION_PROVIDER
    if name == "sidecar":
        return SidecarProvider(settings.EXECUTOR_URL)
    raise ValueError(f"unknown EXECUTION_PROVIDER: {name}")
