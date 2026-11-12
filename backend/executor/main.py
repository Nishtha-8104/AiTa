import threading

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from executor.runner import BatchResult, RunLimits, run_batch

app = FastAPI(title="PET executor")
_slots = threading.Semaphore(4)


class Case(BaseModel):
    id: int
    stdin: str = ""


class RunRequest(BaseModel):
    language: str
    source: str
    cases: list[Case]
    limits: RunLimits = RunLimits()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/run-batch", response_model=BatchResult)
def run(request: RunRequest) -> BatchResult:
    if not _slots.acquire(timeout=30):
        raise HTTPException(status_code=503, detail="executor saturated")
    try:
        return run_batch(
            request.language,
            request.source,
            [case.model_dump() for case in request.cases],
            request.limits,
        )
    finally:
        _slots.release()
