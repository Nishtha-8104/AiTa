"""
Content Player Agent
=====================
The heart of aiTA — an adaptive AI tutor powered by Groq's ultra-fast inference.

Architecture:
  ┌─────────────────────────────────────────────────────────┐
  │                  Content Player Agent                   │
  │                                                         │
  │  ① Mode Router     — detects/routes to correct mode    │
  │  ② Context Builder — assembles user profile + history  │
  │  ③ System Prompter — builds mode-specific system prompt│
  │  ④ Groq Inference  — llama-3.3-70b-versatile (streaming)│
  │  ⑤ Response Parser — extracts concepts, signals, hints │
  │  ⑥ Profile Updater — feeds signals back to User Profile │
  └─────────────────────────────────────────────────────────┘

Five Specialised Modes:
  • QA          — Concept explanation with Socratic follow-ups
  • CODE_HELP   — Debug, explain, fix code (no direct solutions)
  • BRAINSTORM  — Explore approaches, weigh trade-offs
  • QUIZ        — Adaptive questions to test understanding
  • WALKTHROUGH — Step-by-step guided concept walkthroughs

Key Design Principles (from the aiTA paper):
  - Never give direct solutions — guide through hints and questions
  - Adapt language complexity to user's skill level
  - Detect confusion and surface it as a learning signal
  - Feed mastery/weakness signals back to User Profiling Agent
  - Keep explanations grounded in India's curriculum context
"""

import json
import time
import re
import httpx
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any, Generator

from sqlalchemy.orm import Session

from app.models.user import User, LearningProfile
from app.models.content_player import (
    ContentPlayerSession, ContentPlayerMessage,
    CodeSnapshot, SessionMode, MessageRole
)
from app.core.config import settings


# ─── Groq model config ────────────────────────────────────────────────────────
GROQ_MODEL        = "llama-3.3-70b-versatile"
GROQ_API_URL      ="https://api.groq.com/openai/v1/chat/completions"
MAX_HISTORY_TURNS = 12    # last N turns to keep in context window
MAX_TOKENS        = 1500


# ════════════════════════════════════════════════════════════════════════════════
#  SYSTEM PROMPTS — one per mode
# ════════════════════════════════════════════════════════════════════════════════

def _build_system_prompt(mode: SessionMode, user_ctx: Dict) -> str:
    skill   = user_ctx.get("skill_level", "beginner")
    langs   = ", ".join(user_ctx.get("preferred_languages", [])) or "general programming"
    weak    = ", ".join(user_ctx.get("weak_areas", [])) or "none identified yet"
    goals   = ", ".join(user_ctx.get("learning_goals", [])) or "general programming skills"
    name    = user_ctx.get("username", "student")

    base = f"""You are the Content Player Agent inside aiTA — an intelligent AI teaching assistant for programming education in India.

Student Context:
- Name: {name}
- Skill Level: {skill}
- Preferred Languages: {langs}
- Learning Goals: {goals}
- Known Weak Areas: {weak}

Core Rules (NEVER violate):
1. NEVER give complete solutions to exercises — give hints, guide thinking
2. Adapt vocabulary and complexity to the student's skill level ({skill})
3. Use concrete examples in Python/Java/C++ (the student's preferred languages)
4. Be encouraging, warm, and patient — many Indian students face confidence issues
5. When you detect confusion, slow down and try a different explanation approach
6. Always end responses with a follow-up question or next step to keep engagement
7. Keep responses focused and not too long — students lose attention

At the END of every response, append this JSON block (hidden from display):
%%AGENT_META%%{{"concepts": ["list", "of", "concepts", "covered"], "confusion": false, "mastery": ["topics", "student", "understood"], "weak": ["topics", "student", "struggled_with"], "suggestions": ["follow-up question 1", "follow-up question 2", "follow-up question 3"]}}%%END_META%%
"""

    mode_prompts = {
        SessionMode.QA: """
Mode: Q&A / Concept Explanation
Your role: Answer questions clearly. Use the Socratic method where appropriate.
- Start with a simple analogy, then go deeper
- Break complex concepts into digestible steps
- Relate to real-world or exam scenarios
- Check understanding with a gentle question at the end
""",
        SessionMode.CODE_HELP: """
Mode: Code Help & Debugging
Your role: Help students understand and fix their code WITHOUT giving the solution.
- Read the code and error carefully
- Identify the root cause
- Ask "What do you think this line does?" type questions
- Give a targeted hint that points toward the fix
- Explain WHY the error happens conceptually
- For syntax errors: explain the rule being violated
- For logic errors: ask the student to trace execution step by step
- NEVER rewrite the whole function for them
""",
        SessionMode.BRAINSTORM: """
Mode: Brainstorming & Approach Design
Your role: Help students think through problems and design solutions.
- Ask about constraints, edge cases, and requirements
- Present 2-3 different approaches with trade-offs
- Use pseudo-code or diagrams described in text
- Encourage the student to evaluate trade-offs themselves
- Connect to patterns they may already know
""",
        SessionMode.QUIZ: """
Mode: Adaptive Quiz
Your role: Test the student's understanding through targeted questions.
- Start with a question at their skill level
- If correct: increase difficulty, praise briefly, move on
- If incorrect: give a hint, allow a retry, then explain
- Mix question types: MCQ, fill-in-the-blank, code output prediction, debugging
- Track what they get right/wrong to focus on weak areas
- Be encouraging after wrong answers — frame as a learning moment
Format questions clearly with "**Question:**" prefix.
""",
        SessionMode.WALKTHROUGH: """
Mode: Step-by-Step Walkthrough
Your role: Guide students through a concept from scratch, step by step.
- Break the concept into clear numbered steps
- Explain each step with an example
- Pause and ask a micro-question after each major step
- Use progressive complexity: simple → normal → edge case
- Summarise at the end with a "Key Takeaways" section
- Suggest what to learn next
""",
    }

    return base + mode_prompts.get(mode, mode_prompts[SessionMode.QA])


# ════════════════════════════════════════════════════════════════════════════════
#  MAIN AGENT CLASS
# ════════════════════════════════════════════════════════════════════════════════

class ContentPlayerAgent:

    def __init__(self, db: Session):
        self.db           = db
        self.groq_api_key = settings.GROQ_API_KEY
        self.model        = GROQ_MODEL
        print(settings.GROQ_API_KEY)

    # ─────────────────────────────────────────────────────────────────────────
    #  PUBLIC: Create a new session
    # ─────────────────────────────────────────────────────────────────────────


    def create_session(self, user_id: int, mode: SessionMode,
                       language: Optional[str], topic: Optional[str]) -> ContentPlayerSession:
        session = ContentPlayerSession(
            user_id  = user_id,
            mode     = mode,
            language = language,
            topic    = topic,
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    # ─────────────────────────────────────────────────────────────────────────
    #  PUBLIC: Send a message and get agent response
    # ─────────────────────────────────────────────────────────────────────────

    def chat(
        self,
        session_id:    int,
        user_id:       int,
        message:       str,
        code_snippet:  Optional[str] = None,
        code_language: Optional[str] = None,
        error_message: Optional[str] = None,
        mode_override: Optional[SessionMode] = None,
    ) -> Dict[str, Any]:

        start_ms = int(time.time() * 1000)

        # ── Load session & validate ownership ────────────────────────────────
        session: ContentPlayerSession = self.db.query(ContentPlayerSession).filter(
            ContentPlayerSession.id      == session_id,
            ContentPlayerSession.user_id == user_id,
            ContentPlayerSession.is_active == True,
        ).first()

        if not session:
            raise ValueError("Session not found or not active.")

        active_mode = mode_override or session.mode

        # ── Build user context ────────────────────────────────────────────────
        user_ctx = self._get_user_context(user_id)

        # ── Build the full user message text (with code if present) ──────────
        full_user_message = self._format_user_message(
            message, code_snippet, code_language, error_message
        )

        # ── Save user message to DB ───────────────────────────────────────────
        user_msg = ContentPlayerMessage(
            session_id    = session_id,
            user_id       = user_id,
            role          = MessageRole.USER,
            content       = message,
            has_code      = bool(code_snippet),
            code_snippet  = code_snippet,
            code_language = code_language or session.language,
            error_message = error_message,
        )
        self.db.add(user_msg)
        self.db.flush()

        # ── Retrieve conversation history ─────────────────────────────────────
        history = self._build_message_history(session_id, user_id)

        # ── Build Groq messages payload ───────────────────────────────────────
        system_prompt = _build_system_prompt(active_mode, user_ctx)
        groq_messages = [{"role": "system", "content": system_prompt}]
        groq_messages.extend(history)
        groq_messages.append({"role": "user", "content": full_user_message})

        # ── Call Groq API ─────────────────────────────────────────────────────
        raw_response, tokens_used = self._call_groq(groq_messages)
        latency_ms = int(time.time() * 1000) - start_ms

        # ── Parse agent metadata from response ───────────────────────────────
        clean_response, meta = self._parse_agent_meta(raw_response)

        # ── Save assistant message ────────────────────────────────────────────
        assistant_msg = ContentPlayerMessage(
            session_id  = session_id,
            user_id     = user_id,
            role        = MessageRole.ASSISTANT,
            content     = clean_response,
            tokens_used = tokens_used,
            latency_ms  = latency_ms,
            model_used  = self.model,
        )
        self.db.add(assistant_msg)

        # ── Update session metadata ───────────────────────────────────────────
        session.total_messages    += 2
        session.total_tokens_used += tokens_used
        session.last_message_at    = datetime.now(timezone.utc)

        # Auto-generate session title from first user message
        if session.total_messages <= 2 and not session.title:
            session.title = self._generate_title(message)

        # Update concepts, mastery, weak signals from meta
        if meta.get("concepts"):
            existing = set(session.concepts_covered or [])
            session.concepts_covered = list(existing | set(meta["concepts"]))

        if meta.get("confusion"):
            session.confusion_detected = True

        if meta.get("mastery"):
            existing = set(session.mastery_signals or [])
            session.mastery_signals = list(existing | set(meta["mastery"]))

        if meta.get("weak"):
            existing = set(session.weak_signals or [])
            session.weak_signals = list(existing | set(meta["weak"]))

        # Save code snapshot if code was submitted
        if code_snippet:
            snap = CodeSnapshot(
                session_id     = session_id,
                user_id        = user_id,
                language       = code_language or session.language or "unknown",
                code           = code_snippet,
                error          = error_message,
                agent_feedback = clean_response[:500],
            )
            self.db.add(snap)

        self.db.commit()
        self.db.refresh(assistant_msg)

        return {
            "message_id"           : assistant_msg.id,
            "session_id"           : session_id,
            "response"             : clean_response,
            "tokens_used"          : tokens_used,
            "latency_ms"           : latency_ms,
            "session_title"        : session.title,
            "detected_concepts"    : meta.get("concepts", []),
            "follow_up_suggestions": meta.get("suggestions", []),
            "confusion_detected"   : meta.get("confusion", False),
        }

    # ─────────────────────────────────────────────────────────────────────────
    #  PRIVATE: Helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _get_user_context(self, user_id: int) -> Dict:
        user    = self.db.query(User).filter(User.id == user_id).first()
        profile = self.db.query(LearningProfile).filter(
            LearningProfile.user_id == user_id
        ).first()
        return {
            "username"            : user.username if user else "student",
            "skill_level"         : user.skill_level.value if user and user.skill_level else "beginner",
            "preferred_languages" : user.preferred_languages if user else [],
            "learning_goals"      : user.learning_goals if user else [],
            "weak_areas"          : profile.weak_areas if profile else [],
            "strong_areas"        : profile.strong_areas if profile else [],
            "topic_scores"        : profile.topic_scores if profile else {},
        }

    def _format_user_message(
        self,
        message:       str,
        code_snippet:  Optional[str],
        code_language: Optional[str],
        error_message: Optional[str],
    ) -> str:
        parts = [message]
        if code_snippet:
            lang = code_language or "python"
            parts.append(f"\n\n```{lang}\n{code_snippet}\n```")
        if error_message:
            parts.append(f"\n\n**Error / Output:**\n```\n{error_message}\n```")
        return "".join(parts)

    def _build_message_history(self, session_id: int, user_id: int) -> List[Dict]:
        """Fetch last N turns, format for Groq messages array."""
        messages = (
            self.db.query(ContentPlayerMessage)
            .filter(
                ContentPlayerMessage.session_id == session_id,
                ContentPlayerMessage.role.in_([MessageRole.USER, MessageRole.ASSISTANT]),
            )
            .order_by(ContentPlayerMessage.created_at.desc())
            .limit(MAX_HISTORY_TURNS * 2)
            .all()
        )
        messages = list(reversed(messages))

        history = []
        for msg in messages:
            content = msg.content
            if msg.has_code and msg.code_snippet:
                lang = msg.code_language or "python"
                content += f"\n\n```{lang}\n{msg.code_snippet}\n```"
            if msg.error_message:
                content += f"\n\n**Error:**\n```\n{msg.error_message}\n```"
            history.append({
                "role"   : msg.role.value,
                "content": content,
            })
        return history

    def _call_groq(self, messages: List[Dict]) -> tuple[str, int]:
        """Call Groq API and return (response_text, tokens_used)."""
        try:
            response = httpx.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type" : "application/json",
                },
                json={
                    "model"      : self.model,
                    "max_tokens" : MAX_TOKENS,
                    "temperature": 0.7,
                    "messages"   : messages,
                },
                timeout=45.0,
            )
            response.raise_for_status()
            data        = response.json()
            text        = data["choices"][0]["message"]["content"]
            tokens_used = data.get("usage", {}).get("total_tokens", 0)
            return text, tokens_used

        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"Groq API error {e.response.status_code}: {e.response.text}")
        except httpx.TimeoutException:
            raise RuntimeError("Groq API timed out. Please try again.")
        except Exception as e:
            raise RuntimeError(f"Unexpected error calling Groq: {e}")

    def _parse_agent_meta(self, raw: str) -> tuple[str, Dict]:
        """
        Extract the %%AGENT_META%%{...}%%END_META%% block from response.
        Returns (clean_text, meta_dict).
        """
        meta = {"concepts": [], "confusion": False, "mastery": [], "weak": [], "suggestions": []}
        pattern = r"%%AGENT_META%%(.*?)%%END_META%%"
        match = re.search(pattern, raw, re.DOTALL)

        if match:
            try:
                meta = json.loads(match.group(1).strip())
            except json.JSONDecodeError:
                pass
            # Strip the metadata block from the displayed response
            clean = re.sub(pattern, "", raw, flags=re.DOTALL).strip()
        else:
            clean = raw.strip()

        return clean, meta

    def _generate_title(self, first_message: str) -> str:
        """Generate a short title from the first user message."""
        words = first_message.strip().split()
        title = " ".join(words[:8])
        if len(words) > 8:
            title += "..."
        return title[:100]

    # ─────────────────────────────────────────────────────────────────────────
    #  PUBLIC: Session history & management
    # ─────────────────────────────────────────────────────────────────────────

    def get_sessions(self, user_id: int, limit: int = 20) -> List[ContentPlayerSession]:
        return (
            self.db.query(ContentPlayerSession)
            .filter(
                ContentPlayerSession.user_id    == user_id,
                ContentPlayerSession.is_archived == False,
            )
            .order_by(ContentPlayerSession.last_message_at.desc().nullsfirst(),
                      ContentPlayerSession.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_session_detail(self, session_id: int, user_id: int) -> ContentPlayerSession:
        session = (
            self.db.query(ContentPlayerSession)
            .filter(
                ContentPlayerSession.id      == session_id,
                ContentPlayerSession.user_id == user_id,
            )
            .first()
        )
        if not session:
            raise ValueError("Session not found.")
        return session

    def archive_session(self, session_id: int, user_id: int):
        session = self.db.query(ContentPlayerSession).filter(
            ContentPlayerSession.id      == session_id,
            ContentPlayerSession.user_id == user_id,
        ).first()
        if session:
            session.is_archived = True
            self.db.commit()

    def rate_message(self, message_id: int, user_id: int, was_helpful: bool):
        msg = self.db.query(ContentPlayerMessage).filter(
            ContentPlayerMessage.id      == message_id,
            ContentPlayerMessage.user_id == user_id,
            ContentPlayerMessage.role    == MessageRole.ASSISTANT,
        ).first()
        if msg:
            msg.was_helpful = was_helpful
            self.db.commit()