# ============================================================
# CHANGES TO: backend/app/core/config.py
# ADD the ANTHROPIC_API_KEY field to the Settings class
# ============================================================

# Replace the entire Settings class body with this:

from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql://postgres:yourpassword@localhost:5432/aita_db"

    # JWT
    SECRET_KEY: str = "your-super-secret-key-change-this-in-production-min-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # App
    APP_NAME: str = "aiTA - AI Teaching Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # ── Groq API Key for LLM agent reasoning ─────────────────────────────
    GROQ_API_KEY: str = ""   # Set in .env → GROQ_API_KEY=gsk_...

    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()