from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings
import secrets

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a plain-text password."""
    password = password.encode("utf-8")[:72]
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password."""
    plain_password = plain_password.encode("utf-8")[:72]
    return pwd_context.verify(plain_password, hashed_password)


def generate_otp() -> str:
    """Generate a cryptographically secure 6-digit OTP."""
    return str(secrets.randbelow(900000) + 100000)   # always 6 digits: 100000–999999


def hash_otp(otp: str) -> str:
    """Bcrypt-hash the OTP. Raw OTP is never stored."""
    return pwd_context.hash(otp.encode("utf-8"))


def verify_otp(plain_otp: str, hashed_otp: str) -> bool:
    """Verify a plain OTP against its bcrypt hash."""
    return pwd_context.verify(plain_otp.encode("utf-8"), hashed_otp)


def create_otp_token(user_id: int) -> str:
    """
    Short-lived JWT (10 min) issued after password check passes.
    Carries only user_id + type='otp_pending' — NOT a full access token.
    Frontend uses this to call /auth/verify-otp.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=10)
    return jwt.encode(
        {"sub": str(user_id), "type": "otp_pending", "exp": expire},
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def decode_otp_token(token: str) -> Optional[int]:
    """Decode otp_pending token → returns user_id or None."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") != "otp_pending":
            return None
        return int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        return None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token. Returns payload or None."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None