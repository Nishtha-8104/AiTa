# """
# Content Player Agent
# =====================
# The heart of aiTA — an adaptive AI tutor powered by Groq's ultra-fast inference.

# Architecture:
#   ┌─────────────────────────────────────────────────────────┐
#   │                  Content Player Agent                   │
#   │                                                         │
#   │  ① Mode Router     — detects/routes to correct mode    │
#   │  ② Context Builder — assembles user profile + history  │
#   │  ③ System Prompter — builds mode-specific system prompt│
#   │  ④ Groq Inference  — llama-3.3-70b-versatile (streaming)│
#   │  ⑤ Response Parser — extracts concepts, signals, hints │
#   │  ⑥ Profile Updater — feeds signals back to User Profile │
#   └─────────────────────────────────────────────────────────┘

# Five Specialised Modes:
#   • QA          — Concept explanation with Socratic follow-ups
#   • CODE_HELP   — Debug, explain, fix code (no direct solutions)
#   • BRAINSTORM  — Explore approaches, weigh trade-offs
#   • QUIZ        — Adaptive questions to test understanding
#   • WALKTHROUGH — Step-by-step guided concept walkthroughs

# Key Design Principles (from the aiTA paper):
#   - Never give direct solutions — guide through hints and questions
#   - Adapt language complexity to user's skill level
#   - Detect confusion and surface it as a learning signal
#   - Feed mastery/weakness signals back to User Profiling Agent
#   - Keep explanations grounded in India's curriculum context
# """

# import json
# import time
# import re
# import httpx
# from datetime import datetime, timezone
# from typing import List, Dict, Optional, Any, Generator

# from sqlalchemy.orm import Session

# from app.models.user import User, LearningProfile
# from app.models.content_player import (
#     ContentPlayerSession, ContentPlayerMessage,
#     CodeSnapshot, SessionMode, MessageRole
# )
# from app.core.config import settings


# # ─── Groq model config ────────────────────────────────────────────────────────
# GROQ_MODEL        = "llama-3.3-70b-versatile"
# GROQ_API_URL      ="https://api.groq.com/openai/v1/chat/completions"
# MAX_HISTORY_TURNS = 12    # last N turns to keep in context window
# MAX_TOKENS        = 1500




# def _build_system_prompt(mode: SessionMode, user_ctx: Dict) -> str:
#     skill   = user_ctx.get("skill_level", "beginner")
#     langs   = ", ".join(user_ctx.get("preferred_languages", [])) or "general programming"
#     weak    = ", ".join(user_ctx.get("weak_areas", [])) or "none identified yet"
#     goals   = ", ".join(user_ctx.get("learning_goals", [])) or "general programming skills"
#     name    = user_ctx.get("username", "student")

#     base = f"""You are the Content Player Agent inside aiTA — an intelligent AI teaching assistant for programming education in India.

# Student Context:
# - Name: {name}
# - Skill Level: {skill}
# - Preferred Languages: {langs}
# - Learning Goals: {goals}
# - Known Weak Areas: {weak}

# Core Rules (NEVER violate):
# 1. NEVER give complete solutions to exercises — give hints, guide thinking
# 2. Adapt vocabulary and complexity to the student's skill level ({skill})
# 3. Use concrete examples in Python/Java/C++ (the student's preferred languages)
# 4. Be encouraging, warm, and patient — many Indian students face confidence issues
# 5. When you detect confusion, slow down and try a different explanation approach
# 6. Always end responses with a follow-up question or next step to keep engagement
# 7. Keep responses focused and not too long — students lose attention

# At the END of every response, append this JSON block (hidden from display):
# %%AGENT_META%%{{"concepts": ["list", "of", "concepts", "covered"], "confusion": false, "mastery": ["topics", "student", "understood"], "weak": ["topics", "student", "struggled_with"], "suggestions": ["follow-up question 1", "follow-up question 2", "follow-up question 3"]}}%%END_META%%
# """

#     mode_prompts = {
#         SessionMode.QA: """
# Mode: Q&A / Concept Explanation
# Your role: Answer questions clearly. Use the Socratic method where appropriate.
# - Start with a simple analogy, then go deeper
# - Break complex concepts into digestible steps
# - Relate to real-world or exam scenarios
# - Check understanding with a gentle question at the end
# """,
#         SessionMode.CODE_HELP: """
# Mode: Code Help & Debugging
# Your role: Help students understand and fix their code WITHOUT giving the solution.
# - Read the code and error carefully
# - Identify the root cause
# - Ask "What do you think this line does?" type questions
# - Give a targeted hint that points toward the fix
# - Explain WHY the error happens conceptually
# - For syntax errors: explain the rule being violated
# - For logic errors: ask the student to trace execution step by step
# - NEVER rewrite the whole function for them
# """,
#         SessionMode.BRAINSTORM: """
# Mode: Brainstorming & Approach Design
# Your role: Help students think through problems and design solutions.
# - Ask about constraints, edge cases, and requirements
# - Present 2-3 different approaches with trade-offs
# - Use pseudo-code or diagrams described in text
# - Encourage the student to evaluate trade-offs themselves
# - Connect to patterns they may already know
# """,
#         SessionMode.QUIZ: """
# Mode: Adaptive Quiz
# Your role: Test the student's understanding through targeted questions.
# - Start with a question at their skill level
# - If correct: increase difficulty, praise briefly, move on
# - If incorrect: give a hint, allow a retry, then explain
# - Mix question types: MCQ, fill-in-the-blank, code output prediction, debugging
# - Track what they get right/wrong to focus on weak areas
# - Be encouraging after wrong answers — frame as a learning moment
# Format questions clearly with "**Question:**" prefix.
# """,
#         SessionMode.WALKTHROUGH: """
# Mode: Step-by-Step Walkthrough
# Your role: Guide students through a concept from scratch, step by step.
# - Break the concept into clear numbered steps
# - Explain each step with an example
# - Pause and ask a micro-question after each major step
# - Use progressive complexity: simple → normal → edge case
# - Summarise at the end with a "Key Takeaways" section
# - Suggest what to learn next
# """,
#     }

#     return base + mode_prompts.get(mode, mode_prompts[SessionMode.QA])


# # ════════════════════════════════════════════════════════════════════════════════
# #  MAIN AGENT CLASS
# # ════════════════════════════════════════════════════════════════════════════════

# class ContentPlayerAgent:

#     def __init__(self, db: Session):
#         self.db           = db
#         self.groq_api_key = settings.GROQ_API_KEY
#         self.model        = GROQ_MODEL
#         print(settings.GROQ_API_KEY)

#     # ─────────────────────────────────────────────────────────────────────────
#     #  PUBLIC: Create a new session
#     # ─────────────────────────────────────────────────────────────────────────


#     def create_session(self, user_id: int, mode: SessionMode,
#                        language: Optional[str], topic: Optional[str]) -> ContentPlayerSession:
#         session = ContentPlayerSession(
#             user_id  = user_id,
#             mode     = mode,
#             language = language,
#             topic    = topic,
#         )
#         self.db.add(session)
#         self.db.commit()
#         self.db.refresh(session)
#         return session

#     # ─────────────────────────────────────────────────────────────────────────
#     #  PUBLIC: Send a message and get agent response
#     # ─────────────────────────────────────────────────────────────────────────

#     def chat(
#         self,
#         session_id:    int,
#         user_id:       int,
#         message:       str,
#         code_snippet:  Optional[str] = None,
#         code_language: Optional[str] = None,
#         error_message: Optional[str] = None,
#         mode_override: Optional[SessionMode] = None,
#     ) -> Dict[str, Any]:

#         start_ms = int(time.time() * 1000)

#         # ── Load session & validate ownership ────────────────────────────────
#         session: ContentPlayerSession = self.db.query(ContentPlayerSession).filter(
#             ContentPlayerSession.id      == session_id,
#             ContentPlayerSession.user_id == user_id,
#             ContentPlayerSession.is_active == True,
#         ).first()

#         if not session:
#             raise ValueError("Session not found or not active.")

#         active_mode = mode_override or session.mode

#         # ── Build user context ────────────────────────────────────────────────
#         user_ctx = self._get_user_context(user_id)

#         # ── Build the full user message text (with code if present) ──────────
#         full_user_message = self._format_user_message(
#             message, code_snippet, code_language, error_message
#         )

#         # ── Save user message to DB ───────────────────────────────────────────
#         user_msg = ContentPlayerMessage(
#             session_id    = session_id,
#             user_id       = user_id,
#             role          = MessageRole.USER,
#             content       = message,
#             has_code      = bool(code_snippet),
#             code_snippet  = code_snippet,
#             code_language = code_language or session.language,
#             error_message = error_message,
#         )
#         self.db.add(user_msg)
#         self.db.flush()

#         # ── Retrieve conversation history ─────────────────────────────────────
#         history = self._build_message_history(session_id, user_id)

#         # ── Build Groq messages payload ───────────────────────────────────────
#         system_prompt = _build_system_prompt(active_mode, user_ctx)
#         groq_messages = [{"role": "system", "content": system_prompt}]
#         groq_messages.extend(history)
#         groq_messages.append({"role": "user", "content": full_user_message})

#         # ── Call Groq API ─────────────────────────────────────────────────────
#         raw_response, tokens_used = self._call_groq(groq_messages)
#         latency_ms = int(time.time() * 1000) - start_ms

#         # ── Parse agent metadata from response ───────────────────────────────
#         clean_response, meta = self._parse_agent_meta(raw_response)

#         # ── Save assistant message ────────────────────────────────────────────
#         assistant_msg = ContentPlayerMessage(
#             session_id  = session_id,
#             user_id     = user_id,
#             role        = MessageRole.ASSISTANT,
#             content     = clean_response,
#             tokens_used = tokens_used,
#             latency_ms  = latency_ms,
#             model_used  = self.model,
#         )
#         self.db.add(assistant_msg)

#         # ── Update session metadata ───────────────────────────────────────────
#         session.total_messages    += 2
#         session.total_tokens_used += tokens_used
#         session.last_message_at    = datetime.now(timezone.utc)

#         # Auto-generate session title from first user message
#         if session.total_messages <= 2 and not session.title:
#             session.title = self._generate_title(message)

#         # Update concepts, mastery, weak signals from meta
#         if meta.get("concepts"):
#             existing = set(session.concepts_covered or [])
#             session.concepts_covered = list(existing | set(meta["concepts"]))

#         if meta.get("confusion"):
#             session.confusion_detected = True

#         if meta.get("mastery"):
#             existing = set(session.mastery_signals or [])
#             session.mastery_signals = list(existing | set(meta["mastery"]))

#         if meta.get("weak"):
#             existing = set(session.weak_signals or [])
#             session.weak_signals = list(existing | set(meta["weak"]))

#         # Save code snapshot if code was submitted
#         if code_snippet:
#             snap = CodeSnapshot(
#                 session_id     = session_id,
#                 user_id        = user_id,
#                 language       = code_language or session.language or "unknown",
#                 code           = code_snippet,
#                 error          = error_message,
#                 agent_feedback = clean_response[:500],
#             )
#             self.db.add(snap)

#         self.db.commit()
#         self.db.refresh(assistant_msg)

#         return {
#             "message_id"           : assistant_msg.id,
#             "session_id"           : session_id,
#             "response"             : clean_response,
#             "tokens_used"          : tokens_used,
#             "latency_ms"           : latency_ms,
#             "session_title"        : session.title,
#             "detected_concepts"    : meta.get("concepts", []),
#             "follow_up_suggestions": meta.get("suggestions", []),
#             "confusion_detected"   : meta.get("confusion", False),
#         }

#     # ─────────────────────────────────────────────────────────────────────────
#     #  PRIVATE: Helpers
#     # ─────────────────────────────────────────────────────────────────────────

#     def _get_user_context(self, user_id: int) -> Dict:
#         user    = self.db.query(User).filter(User.id == user_id).first()
#         profile = self.db.query(LearningProfile).filter(
#             LearningProfile.user_id == user_id
#         ).first()
#         return {
#             "username"            : user.username if user else "student",
#             "skill_level"         : user.skill_level.value if user and user.skill_level else "beginner",
#             "preferred_languages" : user.preferred_languages if user else [],
#             "learning_goals"      : user.learning_goals if user else [],
#             "weak_areas"          : profile.weak_areas if profile else [],
#             "strong_areas"        : profile.strong_areas if profile else [],
#             "topic_scores"        : profile.topic_scores if profile else {},
#         }

#     def _format_user_message(
#         self,
#         message:       str,
#         code_snippet:  Optional[str],
#         code_language: Optional[str],
#         error_message: Optional[str],
#     ) -> str:
#         parts = [message]
#         if code_snippet:
#             lang = code_language or "python"
#             parts.append(f"\n\n```{lang}\n{code_snippet}\n```")
#         if error_message:
#             parts.append(f"\n\n**Error / Output:**\n```\n{error_message}\n```")
#         return "".join(parts)

#     def _build_message_history(self, session_id: int, user_id: int) -> List[Dict]:
#         """Fetch last N turns, format for Groq messages array."""
#         messages = (
#             self.db.query(ContentPlayerMessage)
#             .filter(
#                 ContentPlayerMessage.session_id == session_id,
#                 ContentPlayerMessage.role.in_([MessageRole.USER, MessageRole.ASSISTANT]),
#             )
#             .order_by(ContentPlayerMessage.created_at.desc())
#             .limit(MAX_HISTORY_TURNS * 2)
#             .all()
#         )
#         messages = list(reversed(messages))

#         history = []
#         for msg in messages:
#             content = msg.content
#             if msg.has_code and msg.code_snippet:
#                 lang = msg.code_language or "python"
#                 content += f"\n\n```{lang}\n{msg.code_snippet}\n```"
#             if msg.error_message:
#                 content += f"\n\n**Error:**\n```\n{msg.error_message}\n```"
#             history.append({
#                 "role"   : msg.role.value,
#                 "content": content,
#             })
#         return history

#     def _call_groq(self, messages: List[Dict]) -> tuple[str, int]:
#         """Call Groq API and return (response_text, tokens_used)."""
#         try:
#             response = httpx.post(
#                 GROQ_API_URL,
#                 headers={
#                     "Authorization": f"Bearer {self.groq_api_key}",
#                     "Content-Type" : "application/json",
#                 },
#                 json={
#                     "model"      : self.model,
#                     "max_tokens" : MAX_TOKENS,
#                     "temperature": 0.7,
#                     "messages"   : messages,
#                 },
#                 timeout=45.0,
#             )
#             response.raise_for_status()
#             data        = response.json()
#             text        = data["choices"][0]["message"]["content"]
#             tokens_used = data.get("usage", {}).get("total_tokens", 0)
#             return text, tokens_used

#         except httpx.HTTPStatusError as e:
#             raise RuntimeError(f"Groq API error {e.response.status_code}: {e.response.text}")
#         except httpx.TimeoutException:
#             raise RuntimeError("Groq API timed out. Please try again.")
#         except Exception as e:
#             raise RuntimeError(f"Unexpected error calling Groq: {e}")

#     def _parse_agent_meta(self, raw: str) -> tuple[str, Dict]:
#         """
#         Extract the %%AGENT_META%%{...}%%END_META%% block from response.
#         Returns (clean_text, meta_dict).
#         """
#         meta = {"concepts": [], "confusion": False, "mastery": [], "weak": [], "suggestions": []}
#         pattern = r"%%AGENT_META%%(.*?)%%END_META%%"
#         match = re.search(pattern, raw, re.DOTALL)

#         if match:
#             try:
#                 meta = json.loads(match.group(1).strip())
#             except json.JSONDecodeError:
#                 pass
#             # Strip the metadata block from the displayed response
#             clean = re.sub(pattern, "", raw, flags=re.DOTALL).strip()
#         else:
#             clean = raw.strip()

#         return clean, meta

#     def _generate_title(self, first_message: str) -> str:
#         """Generate a short title from the first user message."""
#         words = first_message.strip().split()
#         title = " ".join(words[:8])
#         if len(words) > 8:
#             title += "..."
#         return title[:100]

#     # ─────────────────────────────────────────────────────────────────────────
#     #  PUBLIC: Session history & management
#     # ─────────────────────────────────────────────────────────────────────────

#     def get_sessions(self, user_id: int, limit: int = 20) -> List[ContentPlayerSession]:
#         return (
#             self.db.query(ContentPlayerSession)
#             .filter(
#                 ContentPlayerSession.user_id    == user_id,
#                 ContentPlayerSession.is_archived == False,
#             )
#             .order_by(ContentPlayerSession.last_message_at.desc().nullsfirst(),
#                       ContentPlayerSession.created_at.desc())
#             .limit(limit)
#             .all()
#         )

#     def get_session_detail(self, session_id: int, user_id: int) -> ContentPlayerSession:
#         session = (
#             self.db.query(ContentPlayerSession)
#             .filter(
#                 ContentPlayerSession.id      == session_id,
#                 ContentPlayerSession.user_id == user_id,
#             )
#             .first()
#         )
#         if not session:
#             raise ValueError("Session not found.")
#         return session

#     def archive_session(self, session_id: int, user_id: int):
#         session = self.db.query(ContentPlayerSession).filter(
#             ContentPlayerSession.id      == session_id,
#             ContentPlayerSession.user_id == user_id,
#         ).first()
#         if session:
#             session.is_archived = True
#             self.db.commit()

#     def rate_message(self, message_id: int, user_id: int, was_helpful: bool):
#         msg = self.db.query(ContentPlayerMessage).filter(
#             ContentPlayerMessage.id      == message_id,
#             ContentPlayerMessage.user_id == user_id,
#             ContentPlayerMessage.role    == MessageRole.ASSISTANT,
#         ).first()
#         if msg:
#             msg.was_helpful = was_helpful
#             self.db.commit()



"""
agents/content_player_agent.py — UPDATED with:
  1. Topic memory from user profile (interested_topics used in all modes)
  2. LeetCode-style problems in walkthrough mode
  3. Adaptive difficulty based on user comfort signals
  4. Topic sync — if user discusses a new topic, update session + profile everywhere
  5. All 5 modes discuss the SAME topic throughout

Copy to: backend/app/agents/content_player_agent.py
"""

import os
import re
import json
import asyncio
import httpx
from typing import Optional
from app.core.config import settings

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.3-70b-versatile"

# ─── Difficulty levels ────────────────────────────────────────────────────────
DIFFICULTY_LEVELS = ["easy", "medium", "hard", "expert"]


def _get_difficulty_index(level: str) -> int:
    try:
        return DIFFICULTY_LEVELS.index(level.lower())
    except ValueError:
        return 1  # default medium


def _adjust_difficulty(current_level: str, comfort_signal: str) -> str:
    """
    Adjust difficulty based on user comfort.
    comfort_signal: 'too_easy' | 'comfortable' | 'struggling' | 'too_hard'
    """
    idx = _get_difficulty_index(current_level)
    if comfort_signal in ("too_easy",):
        idx = min(idx + 1, len(DIFFICULTY_LEVELS) - 1)
    elif comfort_signal in ("struggling", "too_hard"):
        idx = max(idx - 1, 0)
    return DIFFICULTY_LEVELS[idx]


# ─── LeetCode-style problem generator ────────────────────────────────────────

LEETCODE_PROMPTS = {
    "easy": """Generate a LeetCode EASY level problem about {topic}.
Format exactly like this:
---
**Problem:** [Title]
**Difficulty:** Easy
**Description:** [2-3 sentence clear problem statement]
**Example:**
```
Input: [example input]
Output: [expected output]
Explanation: [brief explanation]
```
**Constraints:**
- [constraint 1]
- [constraint 2]
**Hint:** [one gentle hint]
---
""",
    "medium": """Generate a LeetCode MEDIUM level problem about {topic}.
Format exactly like this:
---
**Problem:** [Title]
**Difficulty:** Medium  
**Description:** [3-4 sentence problem statement with edge cases]
**Example 1:**
```
Input: [example]
Output: [output]
Explanation: [explanation]
```
**Example 2:**
```
Input: [edge case]
Output: [output]
```
**Constraints:**
- [constraint 1]
- [constraint 2]
- [constraint 3]
**Follow-up:** [harder variant to think about]
---
""",
    "hard": """Generate a LeetCode HARD level problem about {topic}.
Format exactly like this:
---
**Problem:** [Title]
**Difficulty:** Hard
**Description:** [Complex problem statement requiring multiple concepts]
**Example:**
```
Input: [complex input]
Output: [output]
Explanation: [detailed explanation]
```
**Constraints:**
- [tight constraint 1]
- [tight constraint 2]
- [time/space complexity requirement]
**Key Insight:** [what makes this hard — the aha moment]
---
""",
    "expert": """Generate a LeetCode contest-level EXPERT problem about {topic}.
Combine multiple advanced concepts. Format as:
---
**Problem:** [Title]
**Difficulty:** Expert
**Description:** [Multi-part complex problem]
**Example:**
```
Input: [complex multi-part input]
Output: [output]
```
**Constraints:**
- Extremely tight time constraint
- Memory optimization required
**Approach Hint:** [vague direction without spoiling]
---
"""
}

# ─── Mode system prompts ──────────────────────────────────────────────────────

def _get_system_prompt(
    mode: str,
    topic: str,
    language: str,
    skill_level: str,
    interested_topics: list,
    difficulty: str = "medium",
) -> str:
    topics_context = f"\nUser's interested topics from profile: {', '.join(interested_topics)}" if interested_topics else ""
    base = f"""You are aiTA, an expert programming tutor specialising in {topic} for {skill_level} learners using {language}.
The ENTIRE conversation stays focused on: **{topic}**. Do not switch topics unless explicitly asked.{topics_context}

Current difficulty level: {difficulty.upper()}
Adapt your explanations, examples, and problems to this difficulty.

CRITICAL RULES:
1. Every example, analogy, and problem MUST relate to {topic}
2. If the user asks about a different topic, acknowledge it but gently redirect: "Great question! Let's finish our {topic} journey first, then we can explore [other topic]."
3. Detect user comfort from their messages:
   - Confused/wrong answers → difficulty drops one level, add more scaffolding
   - Correct + asking for more → difficulty rises one level
4. Always end with ONE question or challenge related to {topic}

After your response, append this hidden metadata (exact format):
%%AGENT_META%%{{"concepts":["{topic}"],"confusion":false,"mastery":[],"weak":[],"suggestions":[],"difficulty":"{difficulty}","topic":"{topic}","comfort_signal":"comfortable"}}%%END_META%%
Update the JSON values based on the actual conversation content.
"""

    mode_prompts = {
        "walkthrough": f"""{base}
MODE: STEP-BY-STEP WALKTHROUGH with LeetCode Practice

Structure each response as:
1. **Concept** — Clear explanation of the {topic} concept at {difficulty} level
2. **Example** — Working {language} code example
3. **Breakdown** — Line-by-line explanation
4.**LeetCode Practice** — After explaining, present a {difficulty}-level problem about {topic}
5. **Check-in** — "Does this make sense? Try solving the problem above."

For the LeetCode problem, use this exact format:
---
 **Practice Problem ({difficulty.title()})**
[Problem statement clearly related to {topic}]

```
Input: [example]
Output: [expected]
```
**Your task:** Write a {language} solution. When done, I'll evaluate and help you improve.
---
""",

        "qa": f"""{base}
MODE: SOCRATIC Q&A

Answer questions about {topic} using the Socratic method:
- Never give the answer directly — guide through questions
- Build on what they already know about {topic}
- Use analogies specific to {topic}
- At the end: "What do you think would happen if [related {topic} scenario]?"
""",

        "quiz": f"""{base}
MODE: ADAPTIVE QUIZ on {topic}

Generate quiz questions about {topic} at {difficulty} difficulty:
- Mix question types: MCQ, code output prediction, bug finding, fill-in-blank
- After each answer: explain WHY it's right or wrong in context of {topic}
- If user struggles 2+ times: "Let me make this easier — " and drop one difficulty level
- If user aces 3 in a row: "Excellent! Let's level up — " and increase difficulty
- Always frame questions around {topic} scenarios
""",

        "code_help": f"""{base}
MODE: CODE ASSISTANCE for {topic}

Help debug and improve code related to {topic}:
- Explain errors in context of {topic} concepts
- Show the corrected code with inline comments
- Explain what went wrong and WHY (relating to {topic})  
- Suggest a follow-up exercise to reinforce the {topic} concept
- Difficulty of suggestions: {difficulty}
""",

        "brainstorm": f"""{base}
MODE: APPROACH BRAINSTORMING for {topic}

Present 2-3 different algorithmic approaches to {topic} problems:
- Each approach: name, brief explanation, time/space complexity, when to use it
- Compare trade-offs honestly
- For {difficulty} level: {'focus on basic approaches' if difficulty == 'easy' else 'include advanced optimisations'}
- End with: "Which approach resonates with you? Let's implement it together."
"""
    }

    return mode_prompts.get(mode, mode_prompts["qa"])


# ─── Topic detection ──────────────────────────────────────────────────────────

TOPIC_KEYWORDS = {
    "arrays": ["array", "list", "subarray", "sliding window", "two pointer"],
    "linked_lists": ["linked list", "node", "pointer", "head", "tail", "next"],
    "trees": ["tree", "bst", "binary", "traversal", "root", "leaf", "graph", "dfs", "bfs"],
    "dynamic_programming": ["dp", "dynamic programming", "memoization", "tabulation", "subproblem"],
    "sorting": ["sort", "merge sort", "quick sort", "bubble", "insertion", "binary search"],
    "recursion": ["recursion", "recursive", "base case", "call stack", "fibonacci"],
    "hashing": ["hash", "dictionary", "map", "set", "collision", "hashmap"],
    "stacks_queues": ["stack", "queue", "deque", "lifo", "fifo", "push", "pop"],
    "backtracking": ["backtrack", "permutation", "combination", "n-queens", "sudoku"],
    "bit_manipulation": ["bit", "bitwise", "xor", "and", "or", "shift", "mask"],
    "greedy": ["greedy", "optimal", "local optimum", "activity selection"],
    "math": ["prime", "gcd", "lcm", "modulo", "factorial", "fibonacci"],
}


def _detect_topic_from_message(message: str) -> Optional[str]:
    """Detect if user message is strongly about a different topic."""
    msg_lower = message.lower()
    topic_scores = {}
    for topic, keywords in TOPIC_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in msg_lower)
        if score >= 2:  # Need at least 2 keyword matches to avoid false positives
            topic_scores[topic] = score
    if topic_scores:
        return max(topic_scores, key=topic_scores.get)
    return None


# ─── Comfort signal detector ──────────────────────────────────────────────────

def _detect_comfort_signal(message: str) -> str:
    """Detect how comfortable the user is from their message."""
    msg_lower = message.lower()
    
    struggling_signals = [
        "don't understand", "confused", "lost", "what?", "huh", "i don't get",
        "this is hard", "too difficult", "not making sense", "can you explain again",
        "still confused", "not sure", "help me", "stuck"
    ]
    easy_signals = [
        "too easy", "already know", "boring", "trivial", "simple", "obviously",
        "that's basic", "i know this", "harder please", "next level", "more challenging"
    ]
    
    if any(s in msg_lower for s in struggling_signals):
        return "struggling"
    if any(s in msg_lower for s in easy_signals):
        return "too_easy"
    return "comfortable"


def _extract_accuracy_from_message(message: str) -> Optional[float]:
    """
    Extract accuracy percentage from a message like:
    'accuracy: 85%', 'score: 90', 'passed 9/10 test cases', etc.
    Returns float 0-100 or None if not found.
    """
    msg_lower = message.lower()

    # Pattern: "accuracy: 85%" or "score: 90%"
    m = re.search(r'(?:accuracy|score)[:\s]+(\d+(?:\.\d+)?)\s*%?', msg_lower)
    if m:
        return float(m.group(1))

    # Pattern: "passed 9/10" or "9 out of 10"
    m = re.search(r'(\d+)\s*(?:/|out of)\s*(\d+)', msg_lower)
    if m:
        passed, total = int(m.group(1)), int(m.group(2))
        if total > 0:
            return (passed / total) * 100

    # Pattern: "85%" standalone
    m = re.search(r'\b(\d{2,3})\s*%', msg_lower)
    if m:
        val = float(m.group(1))
        if 0 <= val <= 100:
            return val

    return None


def _question_key(topic: str, difficulty: str) -> str:
    """Generate a stable key for a question to track solved state."""
    return f"{topic.lower().replace(' ', '_')}_{difficulty}"


# ─── Main agent ──────────────────────────────────────────────────────────────

async def run_content_player(
    mode: str,
    topic: str,
    language: str,
    message: str,
    conversation_history: list,
    user_profile: dict,
    difficulty: str = "medium",
    solved_questions: list = None,
    consecutive_easy_solves: int = 0,
    code_snippet: str = None,
) -> dict:
    """
    Main content player agent.
    
    Returns dict with response, metadata, new_difficulty, topic_changed,
    question_solved, difficulty_increased.
    """
    solved_questions = solved_questions or []

    # Extract user context
    interested_topics = user_profile.get("interested_topics", [])
    skill_level = user_profile.get("skill_level", "beginner")
    
    # ── Accuracy / solved detection ───────────────────────────────────────────
    # Check if user submitted code with accuracy > 70%
    accuracy = _extract_accuracy_from_message(message)
    has_code_submission = bool(code_snippet) or bool(re.search(
        r'def |class |#include|public static|function |=>|{|}', message
    ))

    question_solved = False
    difficulty_increased = False
    new_consecutive = consecutive_easy_solves

    q_key = _question_key(topic, difficulty)

    if has_code_submission and accuracy is not None and accuracy >= 70:
        # Mark this question as solved
        if q_key not in solved_questions:
            solved_questions = solved_questions + [q_key]
        question_solved = True
        new_consecutive += 1

        # Auto-increase difficulty after 3 consecutive easy solves
        if new_consecutive >= 3:
            idx = _get_difficulty_index(difficulty)
            if idx < len(DIFFICULTY_LEVELS) - 1:
                difficulty = DIFFICULTY_LEVELS[idx + 1]
                difficulty_increased = True
                new_consecutive = 0  # reset streak after bump
    elif has_code_submission and (accuracy is None or accuracy < 70):
        # Wrong/incomplete submission — reset streak
        new_consecutive = 0

    # ── Comfort signal ────────────────────────────────────────────────────────
    comfort_signal = _detect_comfort_signal(message)
    
    # Adjust difficulty based on comfort (only if not already bumped by solve streak)
    if not difficulty_increased:
        new_difficulty = _adjust_difficulty(difficulty, comfort_signal)
    else:
        new_difficulty = difficulty

    # ── Topic detection ───────────────────────────────────────────────────────
    detected_topic = _detect_topic_from_message(message)
    topic_changed = False
    effective_topic = topic
    
    if detected_topic and detected_topic != topic and len(message) > 50:
        topic_changed = True
        effective_topic = detected_topic
    
    # ── Build system prompt ───────────────────────────────────────────────────
    # Tell the agent which questions are already solved so it doesn't repeat them
    solved_context = ""
    if solved_questions:
        solved_context = f"\nAlready solved by this student (DO NOT repeat these): {', '.join(solved_questions)}"

    system_prompt = _get_system_prompt(
        mode=mode,
        topic=effective_topic,
        language=language,
        skill_level=skill_level,
        interested_topics=interested_topics,
        difficulty=new_difficulty,
    ) + solved_context

    # Inject LeetCode problem on first walkthrough message
    inject_leetcode = (
        mode == "walkthrough" and
        len(conversation_history) <= 1 and
        "problem" not in message.lower()
    )
    if inject_leetcode:
        system_prompt += f"\n\nIMPORTANT: This is the first walkthrough message. After explaining the concept, MUST include a {new_difficulty} LeetCode-style problem about {effective_topic}."

    # If question was just solved, tell agent to congratulate and give next problem
    if question_solved:
        solved_msg = (
            f"\n\nThe student just solved the {difficulty} problem correctly (accuracy: {accuracy:.0f}%)! "
            f"{'Difficulty has been increased to ' + new_difficulty + '.' if difficulty_increased else ''} "
            f"Congratulate them warmly, then present a NEW {new_difficulty}-level problem about {effective_topic}. "
            f"Do NOT repeat any problem from: {', '.join(solved_questions)}"
        )
        system_prompt += solved_msg

    # ── Build messages ────────────────────────────────────────────────────────
    messages = [{"role": "system", "content": system_prompt}]
    for msg in conversation_history[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    enhanced_message = message
    if comfort_signal != "comfortable":
        enhanced_message = f"[User comfort signal: {comfort_signal}]\n{message}"
    if code_snippet:
        enhanced_message += f"\n\n```{language}\n{code_snippet}\n```"
    messages.append({"role": "user", "content": enhanced_message})
    
    # ── Call Groq ─────────────────────────────────────────────────────────────
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": MODEL,
                "messages": messages,
                "max_tokens": 2048,
                "temperature": 0.7,
            },
        )
        response.raise_for_status()
        data = response.json()
    
    raw_response = data["choices"][0]["message"]["content"]
    tokens_used = data.get("usage", {}).get("total_tokens", 0)
    
    # Extract hidden metadata
    meta = {}
    meta_match = re.search(r"%%AGENT_META%%(.*?)%%END_META%%", raw_response, re.DOTALL)
    if meta_match:
        try:
            meta = json.loads(meta_match.group(1))
        except json.JSONDecodeError:
            pass
        raw_response = raw_response.replace(meta_match.group(0), "").strip()
    
    final_meta = {
        "concepts":           meta.get("concepts", [effective_topic]),
        "confusion":          comfort_signal == "struggling",
        "mastery":            meta.get("mastery", []),
        "weak":               meta.get("weak", []),
        "suggestions":        meta.get("suggestions", []),
        "difficulty":         new_difficulty,
        "topic":              effective_topic,
        "comfort_signal":     comfort_signal,
        "difficulty_changed": new_difficulty != difficulty or difficulty_increased,
        "topic_changed":      topic_changed,
        "tokens_used":        tokens_used,
        "mode":               mode,
    }
    
    return {
        "response":               raw_response,
        "metadata":               final_meta,
        "new_difficulty":         new_difficulty,
        "topic_changed":          topic_changed,
        "new_topic":              effective_topic if topic_changed else None,
        "question_solved":        question_solved,
        "difficulty_increased":   difficulty_increased,
        "solved_questions":       solved_questions,
        "consecutive_easy_solves": new_consecutive,
    }


# ─── LeetCode Problem Generator ───────────────────────────────────────────────

async def generate_leetcode_problem(
    topic: str,
    difficulty: str = "medium",
    language: str = "python",
    exclude_titles: list = None,
) -> dict:
    """
    Generate a complete LeetCode-style problem with starter code, solution, and explanation.
    Retries up to 3 times on 429 rate-limit with exponential backoff.
    Falls back to a local template if Groq is unavailable.
    exclude_titles: list of problem titles already shown — agent must not repeat them.
    """
    exclude_titles = exclude_titles or []
    exclusion_note = ""
    if exclude_titles:
        exclusion_note = f"\n\nIMPORTANT: Do NOT generate any of these problems (already shown): {', '.join(exclude_titles)}. Generate a DIFFERENT problem."

    prompt = f"""Generate a complete LeetCode-style coding problem about "{topic}" at {difficulty} difficulty for {language}.{exclusion_note}

Return ONLY valid JSON in this exact format (no markdown, no extra text):
{{
  "title": "Problem title (e.g. Two Sum, Valid Parentheses)",
  "difficulty": "{difficulty}",
  "description": "Clear 3-4 sentence problem statement",
  "examples": [
    {{"input": "example input", "output": "expected output", "explanation": "brief explanation"}},
    {{"input": "edge case input", "output": "edge case output", "explanation": "why this edge case matters"}}
  ],
  "constraints": [
    "1 <= n <= 10^5",
    "constraint 2"
  ],
  "hints": [
    "Think about what data structure helps here",
    "Consider the time complexity requirement"
  ],
  "starter_code": "def solution():\\n    # Write your solution here\\n    pass",
  "solution_code": "def solution():\\n    # Complete working solution with comments\\n    pass",
  "explanation": "Step-by-step explanation of the optimal approach, time and space complexity"
}}

Make the starter_code a proper {language} function signature with parameters.
Make the solution_code a complete working solution with inline comments explaining each step.
The explanation should cover: approach, why it works, time complexity O(?), space complexity O(?)."""

    max_retries = 3
    backoff = 2  # seconds, doubles each retry

    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    GROQ_API_URL,
                    headers={
                        "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": MODEL,
                        "messages": [{"role": "user", "content": prompt}],
                        "max_tokens": 2000,
                        "temperature": 0.4,
                    },
                )

                if response.status_code == 429:
                    # Rate limited — wait and retry
                    retry_after = int(response.headers.get("retry-after", backoff))
                    wait = max(retry_after, backoff)
                    await asyncio.sleep(wait)
                    backoff *= 2
                    continue

                response.raise_for_status()
                data = response.json()
                break  # success

        except httpx.TimeoutException:
            if attempt < max_retries - 1:
                await asyncio.sleep(backoff)
                backoff *= 2
                continue
            # All retries exhausted — fall through to local fallback
            data = None
            break
        except httpx.HTTPStatusError:
            data = None
            break
    else:
        data = None

    # ── Parse response or use local fallback ──────────────────────────────────
    if data:
        raw = data["choices"][0]["message"]["content"].strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()
        try:
            result = json.loads(raw)
            # If LLM returned a title we've already seen, reject and use fallback
            if result.get("title") in exclude_titles:
                return _local_problem_fallback(topic, difficulty, language, exclude_titles)
            return result
        except json.JSONDecodeError:
            pass  # fall through to local fallback

    return _local_problem_fallback(topic, difficulty, language, exclude_titles)


def _local_problem_fallback(topic: str, difficulty: str, language: str, exclude_titles: list = None) -> dict:
    """
    Returns a pre-built problem template when Groq is rate-limited or unavailable.
    Rotates through variants to avoid repeating the same problem.
    """
    exclude_titles = exclude_titles or []
    topic_lower = topic.lower()

    templates = {
        "arrays": {
            "easy":   [
                ("Two Sum", "Given an array of integers and a target, return indices of two numbers that add up to the target.", "nums = [2,7,11,15], target = 9", "[0,1]", "nums[0] + nums[7] = 9"),
                ("Best Time to Buy and Sell Stock", "Find the maximum profit from buying and selling a stock once.", "prices = [7,1,5,3,6,4]", "5", "Buy at 1, sell at 6"),
                ("Contains Duplicate", "Return true if any value appears at least twice in the array.", "nums = [1,2,3,1]", "true", "1 appears twice"),
            ],
            "medium": [
                ("Maximum Subarray", "Find the contiguous subarray with the largest sum.", "nums = [-2,1,-3,4,-1,2,1,-5,4]", "6", "Subarray [4,-1,2,1] has sum 6"),
                ("Product of Array Except Self", "Return array where each element is the product of all other elements.", "nums = [1,2,3,4]", "[24,12,8,6]", "No division allowed"),
                ("3Sum", "Find all unique triplets that sum to zero.", "nums = [-1,0,1,2,-1,-4]", "[[-1,-1,2],[-1,0,1]]", "Two-pointer after sorting"),
            ],
            "hard":   [
                ("Trapping Rain Water", "Given elevation map, compute how much water it can trap.", "height = [0,1,0,2,1,0,1,3,2,1,2,1]", "6", "Use two pointers or stack"),
                ("Sliding Window Maximum", "Return max of each sliding window of size k.", "nums = [1,3,-1,-3,5,3,6,7], k = 3", "[3,3,5,5,6,7]", "Use a deque"),
            ],
        },
        "linked_lists": {
            "easy":   [
                ("Reverse Linked List", "Reverse a singly linked list.", "head = [1,2,3,4,5]", "[5,4,3,2,1]", "Iterative or recursive"),
                ("Merge Two Sorted Lists", "Merge two sorted linked lists.", "l1 = [1,2,4], l2 = [1,3,4]", "[1,1,2,3,4,4]", "Compare heads iteratively"),
            ],
            "medium": [
                ("Add Two Numbers", "Add two numbers represented as linked lists.", "l1 = [2,4,3], l2 = [5,6,4]", "[7,0,8]", "342 + 465 = 807"),
                ("Remove Nth Node From End", "Remove the nth node from the end of the list.", "head = [1,2,3,4,5], n = 2", "[1,2,3,5]", "Two-pointer with gap n"),
            ],
            "hard":   [
                ("Merge K Sorted Lists", "Merge k sorted linked lists into one sorted list.", "lists = [[1,4,5],[1,3,4],[2,6]]", "[1,1,2,3,4,4,5,6]", "Use a min-heap"),
                ("Reverse Nodes in k-Group", "Reverse every k nodes of a linked list.", "head = [1,2,3,4,5], k = 2", "[2,1,4,3,5]", "Recursive or iterative"),
            ],
        },
        "trees": {
            "easy":   [
                ("Maximum Depth of Binary Tree", "Find the maximum depth of a binary tree.", "root = [3,9,20,null,null,15,7]", "3", "DFS or BFS"),
                ("Symmetric Tree", "Check if a binary tree is a mirror of itself.", "root = [1,2,2,3,4,4,3]", "true", "Recursive comparison"),
            ],
            "medium": [
                ("Binary Tree Level Order Traversal", "Return level order traversal of a binary tree.", "root = [3,9,20,null,null,15,7]", "[[3],[9,20],[15,7]]", "BFS with queue"),
                ("Validate Binary Search Tree", "Determine if a binary tree is a valid BST.", "root = [2,1,3]", "true", "Track min/max bounds"),
            ],
            "hard":   [
                ("Binary Tree Maximum Path Sum", "Find the maximum path sum in a binary tree.", "root = [-10,9,20,null,null,15,7]", "42", "Path 15 -> 20 -> 7"),
                ("Serialize and Deserialize Binary Tree", "Design an algorithm to serialize and deserialize a binary tree.", "root = [1,2,3,null,null,4,5]", '"1,2,3,null,null,4,5"', "BFS or DFS encoding"),
            ],
        },
        "dynamic_programming": {
            "easy":   [
                ("Climbing Stairs", "You can climb 1 or 2 steps. How many ways to reach step n?", "n = 5", "8", "Fibonacci-like pattern"),
                ("House Robber", "Rob houses without robbing adjacent ones. Maximize amount.", "nums = [2,7,9,3,1]", "12", "DP: max(rob, skip)"),
            ],
            "medium": [
                ("Coin Change", "Find minimum coins needed to make amount.", "coins = [1,5,11], amount = 15", "3", "Bottom-up DP"),
                ("Longest Increasing Subsequence", "Find the length of the longest strictly increasing subsequence.", "nums = [10,9,2,5,3,7,101,18]", "4", "DP or binary search"),
            ],
            "hard":   [
                ("Edit Distance", "Find minimum operations to convert word1 to word2.", 'word1 = "horse", word2 = "ros"', "3", "2D DP table"),
                ("Burst Balloons", "Maximize coins by bursting balloons optimally.", "nums = [3,1,5,8]", "167", "Interval DP"),
            ],
        },
        "sorting": {
            "easy":   [
                ("Merge Sorted Array", "Merge two sorted arrays in-place.", "nums1=[1,2,3,0,0,0], nums2=[2,5,6]", "[1,2,2,3,5,6]", "Merge from the end"),
                ("Sort Array by Parity", "Move even integers before odd integers.", "nums = [3,1,2,4]", "[2,4,3,1]", "Two-pointer swap"),
            ],
            "medium": [
                ("Sort Colors", "Sort array of 0s, 1s, 2s in-place (Dutch National Flag).", "nums = [2,0,2,1,1,0]", "[0,0,1,1,2,2]", "Three-pointer approach"),
                ("Kth Largest Element", "Find the kth largest element in an unsorted array.", "nums = [3,2,1,5,6,4], k = 2", "5", "QuickSelect or heap"),
            ],
            "hard":   [
                ("Largest Number", "Arrange numbers to form the largest number.", "nums = [3,30,34,5,9]", '"9534330"', "Custom comparator sort"),
                ("Count of Smaller Numbers After Self", "Count smaller elements to the right of each element.", "nums = [5,2,6,1]", "[2,1,1,0]", "Merge sort or BIT"),
            ],
        },
        "recursion": {
            "easy":   [
                ("Fibonacci Number", "Return the nth Fibonacci number.", "n = 10", "55", "F(n) = F(n-1) + F(n-2)"),
                ("Power of Two", "Determine if n is a power of two using recursion.", "n = 16", "true", "Divide by 2 recursively"),
            ],
            "medium": [
                ("Permutations", "Return all permutations of a distinct integer array.", "nums = [1,2,3]", "[[1,2,3],[1,3,2],...]", "Backtracking with swap"),
                ("Subsets", "Return all possible subsets of a distinct integer array.", "nums = [1,2,3]", "[[],[1],[2],[1,2],[3],[1,3],[2,3],[1,2,3]]", "Include/exclude recursion"),
            ],
            "hard":   [
                ("N-Queens", "Place n queens on n×n board so no two attack each other.", "n = 4", '[[".Q..","...Q","Q...","..Q."],...]', "Backtracking with column/diagonal checks"),
                ("Word Search II", "Find all words from a dictionary in a 2D board.", 'board = [["o","a","a","n"],...], words = ["oath","pea"]', '["oath"]', "Trie + DFS backtracking"),
            ],
        },
    }

    diff_key = difficulty if difficulty in ("easy", "medium", "hard") else "medium"

    # Find best matching template key
    matched = None
    for key in templates:
        if key in topic_lower or topic_lower in key:
            matched = key
            break

    if matched and diff_key in templates[matched]:
        variants = templates[matched][diff_key]
        # Pick first variant whose title isn't in exclude_titles
        chosen = next((v for v in variants if v[0] not in exclude_titles), variants[-1])
        title, desc, inp, out, expl = chosen
    else:
        title = f"{topic.title()} Challenge"
        desc  = f"Solve a {difficulty}-level problem involving {topic}. Given an input, produce the correct output following the constraints below."
        inp, out, expl = "See description", "See description", "Apply the core concept"

    lang_starters = {
        "python":     f"def solve(nums):\n    # Write your solution here\n    pass",
        "java":       f"public int solve(int[] nums) {{\n    // Write your solution here\n    return 0;\n}}",
        "javascript": f"function solve(nums) {{\n    // Write your solution here\n}}",
        "c++":        f"int solve(vector<int>& nums) {{\n    // Write your solution here\n    return 0;\n}}",
    }
    starter = lang_starters.get(language.lower(), lang_starters["python"])

    return {
        "title":        title,
        "difficulty":   difficulty,
        "description":  desc,
        "examples":     [{"input": inp, "output": out, "explanation": expl}],
        "constraints":  ["1 <= n <= 10^4", "Values fit in a 32-bit integer"],
        "hints":        ["Think about the brute force first, then optimise", "Consider time vs space trade-offs"],
        "starter_code": starter,
        "solution_code": starter.replace("pass", "# Solution hidden — try it yourself first!").replace("return 0;", "// Solution hidden — try it yourself first!"),
        "explanation":  f"This is a {difficulty} {topic} problem. Work through it step by step. If you're stuck, ask the tutor for a hint!",
    }
