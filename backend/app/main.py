
import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.llm_choice import LLMChoiceMiddleware
from app.features.grading import models as code_eval_models  # noqa: F401
from app.features.problems import models as problem_models  # noqa: F401
from app.features.accounts import router_auth, router_users, router_profile
from app.features.chat import router as chat
from app.features.feedback import router as feedback
from app.features.gamification import router as gamification
from app.features.model_settings import router as model_settings
from app.features.grading import router as code_eval
from app.features.onboarding import router as onboarding
from app.features.practice import router_assessment, router_sessions, router_topic_practice
from app.features.problems import router as problems
from app.features.onboarding.logic import pending
from app.features.chat.logic.rag import embedder


@asynccontextmanager
async def lifespan(app: FastAPI):
    # No create_all here. It adds missing tables but never missing columns, so a
    # database behind a migration starts up looking healthy and fails later on the
    # first write. Alembic owns the schema: run `alembic upgrade head`.
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} is running.")
    if not settings.SKIP_EMBED_WARMUP:
        embedder.warm_up_in_background()
    stop = asyncio.Event()
    sweep = None
    if not settings.SKIP_ONBOARDING_SWEEP:
        sweep = asyncio.create_task(pending.run_sweep_loop(stop))
    yield
    stop.set()
    if sweep is not None:
        await sweep
    print("👋 Shutting down PET backend.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## PET — Programming Education Tool backend

Practice, graded code, hints, feedback and a learner model per topic and language.

### Access
PET runs on your own computer for one student. `POST /auth/session` returns a Bearer
token; paste it into **Authorize**.
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

register_exception_handlers(app)

app.add_middleware(LLMChoiceMiddleware)
# Credentials so the model-choice cookie travels; that rules out a "*" origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router_auth.router, prefix="/api/v1")
app.include_router(router_users.router, prefix="/api/v1")
app.include_router(problems.router, prefix="/api/v1")
app.include_router(code_eval.router,prefix="/api/v1")
app.include_router(feedback.router, prefix="/api/v1")
app.include_router(router_profile.router, prefix="/api/v1")
app.include_router(router_assessment.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(gamification.router, prefix="/api/v1")
app.include_router(onboarding.router, prefix="/api/v1")
app.include_router(router_sessions.router, prefix="/api/v1")
app.include_router(router_topic_practice.router, prefix="/api/v1")
app.include_router(model_settings.router, prefix="/api/v1")


@app.get("/", tags=["Health"])
def root():
    return {"app": settings.APP_NAME, "version": settings.APP_VERSION, "status": "running", "docs": "/docs"}


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy", "version": settings.APP_VERSION}