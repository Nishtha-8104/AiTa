from pydantic_settings import BaseSettings
from typing import List
from dotenv import load_dotenv
import os

# Load .env from backend/ directory (one level up from app/)
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str 

    # JWT
    SECRET_KEY: str 
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # App
    APP_NAME: str = "aiTA - AI Teaching Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # ── Groq API Key for LLM agent reasoning ─────────────────────────────
    GROQ_API_KEY: str=""
    YOUTUBE_API_KEY: str=""

    # ── Email (SMTP) for OTP delivery ─────────────────────────────────────
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_NAME: str = "aiTA"
    
    # ── Gmail API (OAuth2 - works on Render via HTTPS) ────────────────────
    GMAIL_CLIENT_ID: str = ""
    GMAIL_CLIENT_SECRET: str = ""
    GMAIL_REFRESH_TOKEN: str = ""
    GMAIL_FROM_EMAIL: str = ""
    @property
    def allowed_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    class Config:
        env_file = os.path.join(os.path.dirname(__file__), '..', '..', '.env')
        extra = "ignore"
    

settings = Settings()