
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import Base, engine
from app.api import auth, users, recommendations,content_player


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    print(f"✅ Database tables created/verified.")
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} is running.")
    yield
    print("👋 Shutting down aiTA backend.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
## aiTA — AI-Powered Teaching Assistant Backend

### Agents
- 👤 **User Profiling Agent** — Builds dynamic learner models
- 🤖 **Content Recommendation Agent** — CF + CBF + Claude LLM reasoning

### Authentication
Use `/auth/login` to get a Bearer token, then click **Authorize**.
    """,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(recommendations.router, prefix="/api/v1")   
app.include_router(content_player.router, prefix="/api/v1")


@app.get("/", tags=["Health"])
def root():
    return {"app": settings.APP_NAME, "version": settings.APP_VERSION, "status": "running", "docs": "/docs"}


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy", "version": settings.APP_VERSION}