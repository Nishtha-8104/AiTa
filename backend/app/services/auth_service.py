import uuid
import smtplib
import logging
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User, LearningProfile, UserSession, OTPRecord
from app.schemas.user import RegisterRequest, LoginRequest, TokenResponse, OTPChallengeResponse
from app.core.security import (
    hash_password, verify_password,
    generate_otp, hash_otp, verify_otp,
    create_otp_token, decode_otp_token,
    create_access_token, create_refresh_token, decode_token,
)
from app.core.config import settings

logger = logging.getLogger(__name__)

OTP_EXPIRY_MINUTES = 10

# Try to import Gmail API
try:
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    from google.auth.transport.requests import Request
    GMAIL_API_AVAILABLE = True
except ImportError:
    GMAIL_API_AVAILABLE = False
    logger.warning("Gmail API libraries not installed. Using SMTP fallback.")


def _mask_email(email: str) -> str:
    """s***@gmail.com — shows first char + domain only."""
    local, domain = email.split("@", 1)
    return f"{local[0]}***@{domain}"


def _get_gmail_service():
    """Get authenticated Gmail API service using OAuth2 refresh token."""
    if not GMAIL_API_AVAILABLE:
        return None
    
    if not settings.GMAIL_CLIENT_ID or not settings.GMAIL_CLIENT_SECRET or not settings.GMAIL_REFRESH_TOKEN:
        return None
    
    try:
        # Create credentials from refresh token
        creds = Credentials(
            token=None,
            refresh_token=settings.GMAIL_REFRESH_TOKEN,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GMAIL_CLIENT_ID,
            client_secret=settings.GMAIL_CLIENT_SECRET,
            scopes=["https://www.googleapis.com/auth/gmail.send"]
        )
        
        # Refresh the access token
        creds.refresh(Request())
        
        # Build Gmail service
        service = build('gmail', 'v1', credentials=creds)
        return service
    except Exception as e:
        logger.error(f"Failed to initialize Gmail API: {e}")
        return None


def _send_email_via_gmail_api(to_email: str, subject: str, body: str) -> bool:
    """Send email using Gmail API (works on Render - uses HTTPS)."""
    try:
        service = _get_gmail_service()
        if not service:
            return False
        
        # Create message
        message = MIMEText(body)
        message["To"] = to_email
        message["From"] = settings.GMAIL_FROM_EMAIL
        message["Subject"] = subject
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        # Send via Gmail API
        service.users().messages().send(
            userId="me",
            body={"raw": raw_message}
        ).execute()
        
        logger.info(f"Email sent via Gmail API to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Gmail API send failed: {e}")
        return False


def _send_otp_email(to_email: str, otp: str, username: str) -> None:
    """
    Send OTP via Gmail API (preferred) or SMTP fallback.
    Falls back to console log if neither is configured.
    """
    subject = "Your aiTA Login OTP"
    body = f"""Hi {username},

Your one-time password (OTP) for aiTA login is:

    {otp}

This OTP expires in {OTP_EXPIRY_MINUTES} minutes.
If you did not request this, please ignore this email.

— aiTA Team
"""

    # Try Gmail API first (works on Render)
    if GMAIL_API_AVAILABLE and settings.GMAIL_REFRESH_TOKEN:
        if _send_email_via_gmail_api(to_email, subject, body):
            return
    
    # Fallback to SMTP (may not work on Render)
    if settings.SMTP_USER and settings.SMTP_PASSWORD:
        msg = MIMEMultipart()
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_USER}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                server.ehlo()
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_USER, to_email, msg.as_string())
            logger.info(f"OTP sent via SMTP to {to_email}")
            return
        except Exception as exc:
            logger.error(f"SMTP send failed for {to_email}: {exc}")
    
    # Final fallback to console
    print(f"[DEV] OTP for {to_email}: {otp}") 
    logger.warning(f"[DEV] OTP for {to_email}: {otp}")


def _send_otp_email_reset(to_email: str, otp: str, username: str) -> None:
    """Send password-reset OTP email via Gmail API or SMTP."""
    subject = "Reset your aiTA password"
    body = f"""Hi {username},

You requested a password reset for your aiTA account.
Your one-time password (OTP) is:

    {otp}

This OTP expires in {OTP_EXPIRY_MINUTES} minutes.
If you did not request this, you can safely ignore this email.

— aiTA Team
"""

    # Try Gmail API first
    if GMAIL_API_AVAILABLE and settings.GMAIL_REFRESH_TOKEN:
        if _send_email_via_gmail_api(to_email, subject, body):
            return
    
    # Fallback to SMTP
    if settings.SMTP_USER and settings.SMTP_PASSWORD:
        msg = MIMEMultipart()
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_USER}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                server.ehlo()
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.SMTP_USER, to_email, msg.as_string())
            logger.info(f"Reset OTP sent via SMTP to {to_email}")
            return
        except Exception as exc:
            logger.error(f"SMTP reset send failed for {to_email}: {exc}")
    
    # Final fallback
    logger.warning(f"[DEV] Password reset OTP for {to_email}: {otp}")


class AuthService:

    @staticmethod
    def register(db: Session, data: RegisterRequest) -> User:
        """Register a new user and create their learning profile."""
        if db.query(User).filter(User.email == data.email).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email already exists."
            )
        if db.query(User).filter(User.username == data.username).first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This username is already taken. Please choose another."
            )

        user = User(
            email=data.email,
            username=data.username,
            hashed_password=hash_password(data.password),
            full_name=data.full_name,
            role=data.role,
            preferred_languages=[],
            learning_goals=[],
            interests=[],
            badges=[],
        )
        db.add(user)
        db.flush()

        profile = LearningProfile(
            user_id=user.id,
            topic_scores={},
            error_patterns=[],
            strong_areas=[],
            weak_areas=[],
            recommended_next=[],
            preferred_content_types=[],
        )
        db.add(profile)
        db.commit()
        db.refresh(user)
        return user

    # ── STEP 1: Verify password → issue OTP ──────────────────────────────────

    @staticmethod
    def login_step1(
        db: Session, data: LoginRequest,
    ) -> OTPChallengeResponse:
        """
        Step 1 of 2FA login:
        - Verify email + password
        - Generate 6-digit OTP, bcrypt-hash it, store in otp_records
        - Send raw OTP to user's email
        - Return otp_token (short-lived JWT) — NOT access tokens yet
        """
        user = db.query(User).filter(User.email == data.email).first()

        # Constant-time: always check password even if user not found
        if not user or not verify_password(data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account has been deactivated. Please contact support."
            )

        # Delete any existing unused OTPs for this user
        db.query(OTPRecord).filter(
            OTPRecord.user_id == user.id,
            OTPRecord.is_used == False,
        ).delete()

        # Generate + hash OTP — raw OTP never touches the DB
        raw_otp    = generate_otp()
        otp_record = OTPRecord(
            user_id    = user.id,
            hashed_otp = hash_otp(raw_otp),
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES),
        )
        db.add(otp_record)
        db.commit()

        # Send raw OTP via email (or console in dev)
        _send_otp_email(user.email, raw_otp, user.username)

        return OTPChallengeResponse(
            otp_token  = create_otp_token(user.id),
            email_hint = _mask_email(user.email),
        )

    # ── STEP 2: Verify OTP → issue real JWT tokens ────────────────────────────

    @staticmethod
    def login_step2(
        db: Session, otp_token: str, otp: str,
        ip_address: str = None, user_agent: str = None,
    ) -> TokenResponse:
        """
        Step 2 of 2FA login:
        - Decode otp_token to get user_id
        - Find the latest unused, unexpired OTPRecord for that user
        - Verify raw OTP against bcrypt hash
        - Mark OTP as used
        - Issue real access + refresh tokens
        """
        user_id = decode_otp_token(otp_token)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="OTP session expired or invalid. Please log in again.",
            )

        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")

        now = datetime.now(timezone.utc)
        record = (
            db.query(OTPRecord)
            .filter(
                OTPRecord.user_id == user_id,
                OTPRecord.is_used == False,
                OTPRecord.expires_at > now,
            )
            .order_by(OTPRecord.created_at.desc())
            .first()
        )

        if not record or not verify_otp(otp, record.hashed_otp):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired OTP.",
            )

        # Consume the OTP — can never be reused
        record.is_used = True

        # Issue real tokens
        jti        = str(uuid.uuid4())
        token_data = {"sub": str(user.id), "username": user.username, "role": user.role, "jti": jti}

        access_token  = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)

        session = UserSession(
            user_id    = user.id,
            token_jti  = jti,
            ip_address = ip_address,
            user_agent = user_agent,
        )
        db.add(session)

        user.total_sessions += 1
        user.last_active_at  = now
        db.commit()

        return TokenResponse(
            access_token  = access_token,
            refresh_token = refresh_token,
            token_type    = "bearer",
            expires_in    = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    # ── Forgot Password: send OTP ─────────────────────────────────────────────

    @staticmethod
    def forgot_password(db: Session, email: str) -> OTPChallengeResponse:
        """
        Sends a password-reset OTP to the given email.
        Always returns success — never reveals whether the email exists.
        """
        user = db.query(User).filter(User.email == email).first()

        if user and user.is_active:
            # Delete any existing unused OTPs
            db.query(OTPRecord).filter(
                OTPRecord.user_id == user.id,
                OTPRecord.is_used == False,
            ).delete()

            raw_otp = generate_otp()
            db.add(OTPRecord(
                user_id    = user.id,
                hashed_otp = hash_otp(raw_otp),
                expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES),
            ))
            db.commit()

            _send_otp_email_reset(user.email, raw_otp, user.username)
            otp_token  = create_otp_token(user.id)
            email_hint = _mask_email(user.email)
        else:
            # Return a dummy response — don't leak whether email exists
            otp_token  = "invalid"
            email_hint = _mask_email(email) if "@" in email else "***"

        return OTPChallengeResponse(
            otp_token  = otp_token,
            message    = "If this email is registered, an OTP has been sent.",
            email_hint = email_hint,
        )

    # ── Forgot Password: verify OTP + set new password ────────────────────────

    @staticmethod
    def reset_password(db: Session, otp_token: str, otp: str, new_password: str) -> None:
        """
        Verifies the reset OTP and sets the new password.
        """
        user_id = decode_otp_token(otp_token)
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Reset session expired or invalid. Please request a new OTP.",
            )

        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        now    = datetime.now(timezone.utc)
        record = (
            db.query(OTPRecord)
            .filter(
                OTPRecord.user_id  == user_id,
                OTPRecord.is_used  == False,
                OTPRecord.expires_at > now,
            )
            .order_by(OTPRecord.created_at.desc())
            .first()
        )

        if not record or not verify_otp(otp, record.hashed_otp):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired OTP.",
            )

        record.is_used       = True
        user.hashed_password = hash_password(new_password)
        db.commit()

    # ── Token refresh ─────────────────────────────────────────────────────────

    @staticmethod
    def refresh_tokens(db: Session, refresh_token: str) -> TokenResponse:
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token."
            )

        user_id = int(payload.get("sub"))
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        jti        = str(uuid.uuid4())
        token_data = {"sub": str(user.id), "username": user.username, "role": user.role, "jti": jti}
        return TokenResponse(
            access_token  = create_access_token(token_data),
            refresh_token = create_refresh_token(token_data),
            token_type    = "bearer",
            expires_in    = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    # ── Logout ────────────────────────────────────────────────────────────────

    @staticmethod
    def logout(db: Session, user_id: int, jti: str):
        session = db.query(UserSession).filter(
            UserSession.user_id   == user_id,
            UserSession.token_jti == jti,
        ).first()
        if session:
            session.is_active = False
            session.ended_at  = datetime.now(timezone.utc)
            db.commit()
