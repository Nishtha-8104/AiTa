"""
Feedback Agent  (Step 5 of the aiTA Pipeline)
==============================================
Per the proposal:
  "The Feedback Agent translates findings of code evaluation and content player
   agents and sends rich, meaningful feedback to assist the learner in grasping
   errors and augmenting skills. The entire process feeds back into the User
   Profiling Agent, which updates the user profile in real time."

Pipeline steps:
  ① Context Collector  — pulls Code Eval result AND/OR Content Player session
  ② Pattern Analyser   — finds recurring errors, misconceptions, weak concepts
  ③ Groq LLM Synthesis — narrative feedback personalised to student profile
  ④ Profile Updater    — writes weak_areas, error_patterns, topic_scores back
  ⑤ Persist            — saves FeedbackReport, returns to frontend
"""

import json, time, httpx
from datetime import datetime, timezone
from typing import Optional, Dict, List
from sqlalchemy.orm import Session

from app.models.user import User, LearningProfile
from app.models.feedback import FeedbackReport, FeedbackType, FeedbackTone
from app.models.code_eval import CodeEvaluation, CodeSubmission
from app.models.content_player import ContentPlayerSession
from app.core.config import settings

GROQ_URL   = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"


class FeedbackAgent:

    def __init__(self, db: Session):
        self.db  = db
        self.key = settings.GROQ_API_KEY

    # ─── PUBLIC ENTRY POINT ───────────────────────────────────────────────────

    def generate(self, user_id: int, evaluation_id: Optional[int],
                 cp_session_id: Optional[int], tone: FeedbackTone) -> FeedbackReport:

        start_ms = int(time.time() * 1000)
        steps    = []

        # ① Collect context
        steps.append(" Step 1: Collecting context from upstream agents...")
        user_ctx = self._get_user(user_id)
        eval_ctx = self._get_eval(evaluation_id)      if evaluation_id  else None
        cp_ctx   = self._get_cp_session(cp_session_id) if cp_session_id else None

        if not eval_ctx and not cp_ctx:
            raise ValueError("Provide at least one of evaluation_id or cp_session_id.")

        fb_type = (FeedbackType.COMBINED       if eval_ctx and cp_ctx else
                   FeedbackType.CODE_REVIEW    if eval_ctx else
                   FeedbackType.LEARNING_RECAP)
        steps.append(f" Type: {fb_type.value} | Tone: {tone.value}")

        # ② Analyse patterns
        steps.append("Step 2: Analysing error patterns and concept gaps...")
        patterns = self._analyse_patterns(eval_ctx, cp_ctx)
        steps.append(f"{len(patterns['errors'])} errors, "
                     f"{len(patterns['weak_concepts'])} weak concepts found")

        # ③ LLM synthesis
        steps.append(" Step 3: Groq LLM generating contextual feedback...")
        llm    = self._llm_synthesise(user_ctx, eval_ctx, cp_ctx, patterns, tone)
        tokens = llm.pop("tokens_used", 0)
        steps.append(f" Feedback synthesised ({tokens} tokens)")

        # ④ Update profile
        steps.append("👤 Step 4: Writing signals back to User Profile...")
        profile_updates = self._update_profile(user_id, patterns, llm)
        steps.append(f" Updated: {list(profile_updates.keys())}")

        # ⑤ Persist
        duration = int(time.time() * 1000) - start_ms
        steps.append(f"Done in {duration}ms")

        report = FeedbackReport(
            user_id        = user_id,
            evaluation_id  = evaluation_id,
            cp_session_id  = cp_session_id,
            feedback_type  = fb_type,
            tone           = tone,
            headline       = llm.get("headline", ""),
            summary        = llm.get("summary", ""),
            strengths      = llm.get("strengths", []),
            errors         = llm.get("errors", []),
            misconceptions = llm.get("misconceptions", []),
            action_items   = llm.get("action_items", []),
            concept_map    = llm.get("concept_map", {}),
            next_topics    = llm.get("next_topics", []),
            motivational   = llm.get("motivational", ""),
            profile_updates= profile_updates,
            agent_steps    = steps,
            tokens_used    = tokens,
            latency_ms     = duration,
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    # ─── CONTEXT COLLECTORS ───────────────────────────────────────────────────

    def _get_user(self, user_id: int) -> Dict:
        u = self.db.query(User).filter(User.id == user_id).first()
        p = self.db.query(LearningProfile).filter(LearningProfile.user_id == user_id).first()
        return {
            "username":       u.username if u else "student",
            "skill":          u.skill_level.value if u and u.skill_level else "beginner",
            "languages":      u.preferred_languages or [],
            "goals":          u.learning_goals or [],
            "weak_areas":     p.weak_areas or [] if p else [],
            "error_patterns": p.error_patterns or [] if p else [],
            "accuracy":       p.accuracy_rate or 0.0 if p else 0.0,
        }

    def _get_eval(self, eval_id: int) -> Optional[Dict]:
        ev  = self.db.query(CodeEvaluation).filter(CodeEvaluation.id == eval_id).first()
        if not ev: return None
        sub = self.db.query(CodeSubmission).filter(CodeSubmission.id == ev.submission_id).first()
        return {
            "language":        sub.language.value if sub else "unknown",
            "code":            (sub.code or "")[:1500] if sub else "",
            "overall":         ev.overall_score,
            "correctness":     ev.correctness_score,
            "quality":         ev.quality_score,
            "efficiency":      ev.efficiency_score,
            "security":        ev.security_score,
            "style":           ev.style_score,
            "docs":            ev.documentation_score,
            "issues":          ev.issues or [],
            "time_complexity": ev.time_complexity,
            "key_improvements":ev.key_improvements or [],
            "learning_points": ev.learning_points or [],
            "best_practices":  ev.best_practices_used or [],
            "anti_patterns":   ev.anti_patterns or [],
            "summary":         ev.summary or "",
        }

    def _get_cp_session(self, sid: int) -> Optional[Dict]:
        s = self.db.query(ContentPlayerSession).filter(ContentPlayerSession.id == sid).first()
        if not s: return None
        return {
            "topic":    s.topic or "",
            "mode":     s.mode if isinstance(s.mode, str) else s.mode.value if s.mode else "qa",
            "concepts": s.concepts_covered or [],
            "mastery":  s.mastery_signals or [],
            "weak":     s.weak_signals or [],
            "confusion":s.confusion_detected,
            "messages": s.total_messages,
        }

    # ─── PATTERN ANALYSER ─────────────────────────────────────────────────────

    def _analyse_patterns(self, eval_ctx, cp_ctx) -> Dict:
        errors, weak_concepts, strengths = [], [], []

        if eval_ctx:
            for issue in eval_ctx["issues"][:10]:
                if issue.get("severity") in ("error", "critical"):
                    errors.append(f"[{issue.get('category','?')}] {issue.get('message','')}")
            for dim, score in [("correctness", eval_ctx["correctness"]),
                                ("quality",     eval_ctx["quality"]),
                                ("efficiency",  eval_ctx["efficiency"]),
                                ("security",    eval_ctx["security"]),
                                ("documentation", eval_ctx["docs"])]:
                if score < 60:
                    weak_concepts.append(dim)
            strengths.extend(eval_ctx.get("best_practices", [])[:3])

        if cp_ctx:
            weak_concepts.extend(cp_ctx.get("weak", []))
            strengths.extend(cp_ctx.get("mastery", []))
            if cp_ctx.get("confusion"):
                errors.append(f"Confusion on topic: '{cp_ctx.get('topic','')}'")

        return {
            "errors":        list(dict.fromkeys(errors))[:8],
            "weak_concepts": list(dict.fromkeys(weak_concepts))[:6],
            "strengths":     list(dict.fromkeys(strengths))[:5],
        }

    # ─── GROQ LLM SYNTHESIS ───────────────────────────────────────────────────

    def _llm_synthesise(self, user_ctx, eval_ctx, cp_ctx, patterns, tone) -> Dict:
        tone_map = {
            FeedbackTone.ENCOURAGING:  "Be warm and encouraging — praise effort before mentioning problems.",
            FeedbackTone.CONSTRUCTIVE: "Be direct and specific — focus on actionable improvement over praise.",
            FeedbackTone.CHALLENGING:  "Be Socratic — ask why, push deeper understanding, challenge assumptions.",
        }

        system = f"""You are the Feedback Agent in aiTA — an AI teaching assistant for Indian programming students.
You synthesise findings from the Code Evaluation Agent and Content Player Agent into rich, personalised feedback.

Student: {user_ctx['username']} | Skill: {user_ctx['skill']}
Languages: {', '.join(user_ctx['languages']) or 'general'}
Known weak areas: {', '.join(user_ctx['weak_areas']) or 'none yet'}
Tone: {tone_map[tone]}

Rules:
- NEVER say "wrong" without explaining WHY it matters for learning
- Adapt language to {user_ctx['skill']} level — no jargon for beginners
- Action items must be specific and doable in one 30-minute session
- concept_map values are 0.0–1.0 estimates of current understanding
- motivational line must be personal to this student, not generic

Respond ONLY with valid JSON (no markdown fences):
{{
  "headline": "<one-line overall verdict, max 120 chars>",
  "summary": "<3-4 sentence narrative synthesis>",
  "strengths": ["<specific thing done well>", ...],
  "errors": ["<error + why it matters>", ...],
  "misconceptions": ["<conceptual misunderstanding>", ...],
  "action_items": ["<specific actionable task>", "<task 2>", "<task 3>"],
  "concept_map": {{"<concept>": <0.0-1.0>, ...}},
  "next_topics": ["<topic 1>", "<topic 2>", "<topic 3>"],
  "motivational": "<one personalised encouraging sentence>"
}}"""

        parts = []
        if eval_ctx:
            parts.append(
                f"CODE EVALUATION:\n"
                f"Score: {eval_ctx['overall']:.0f}/100 | Correct: {eval_ctx['correctness']:.0f} | "
                f"Quality: {eval_ctx['quality']:.0f} | Efficiency: {eval_ctx['efficiency']:.0f}\n"
                f"Issues: {json.dumps(patterns['errors'])}\n"
                f"Learning points: {json.dumps(eval_ctx['learning_points'][:5])}\n"
                f"Anti-patterns: {json.dumps(eval_ctx['anti_patterns'][:4])}\n"
                f"Agent summary: {eval_ctx['summary']}"
            )
        if cp_ctx:
            parts.append(
                f"CONTENT PLAYER SESSION:\n"
                f"Topic: {cp_ctx['topic']} | Mode: {cp_ctx['mode']}\n"
                f"Concepts covered: {json.dumps(cp_ctx['concepts'][:8])}\n"
                f"Mastery: {json.dumps(cp_ctx['mastery'][:5])}\n"
                f"Weaknesses: {json.dumps(cp_ctx['weak'][:5])}\n"
                f"Confusion detected: {cp_ctx['confusion']}"
            )
        parts.append(
            f"PATTERN ANALYSIS:\n"
            f"Error patterns: {json.dumps(patterns['errors'])}\n"
            f"Weak concepts: {json.dumps(patterns['weak_concepts'])}\n"
            f"Strengths: {json.dumps(patterns['strengths'])}"
        )

        try:
            r = httpx.post(
                GROQ_URL,
                headers={"Authorization": f"Bearer {self.key}", "Content-Type": "application/json"},
                json={
                    "model": GROQ_MODEL, "max_tokens": 1800, "temperature": 0.4,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user",   "content": "\n\n".join(parts)},
                    ],
                },
                timeout=60.0,
            )
            r.raise_for_status()
            data = r.json()
            raw  = data["choices"][0]["message"]["content"].strip()
            tok  = data.get("usage", {}).get("total_tokens", 0)
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"): raw = raw[4:]
            parsed = json.loads(raw.strip())
            parsed["tokens_used"] = tok
            return parsed
        except Exception:
            return {
                "headline":      "Feedback generated (static fallback)",
                "summary":       f"Patterns found: {', '.join(patterns['errors'][:2]) or 'none'}.",
                "strengths":     patterns["strengths"],
                "errors":        patterns["errors"],
                "misconceptions":[],
                "action_items":  [f"Review: {c}" for c in patterns["weak_concepts"][:3]],
                "concept_map":   {c: 0.3 for c in patterns["weak_concepts"]},
                "next_topics":   patterns["weak_concepts"][:3],
                "motivational":  "Every bug fixed is a lesson learned — keep going!",
                "tokens_used":   0,
            }

    # ─── PROFILE UPDATER ──────────────────────────────────────────────────────

    def _update_profile(self, user_id: int, patterns: Dict, llm: Dict) -> Dict:
        p = self.db.query(LearningProfile).filter(LearningProfile.user_id == user_id).first()
        if not p: return {}
        updates = {}

        new_weak = list(dict.fromkeys(
            (p.weak_areas or []) + patterns["weak_concepts"] + llm.get("next_topics", [])[:2]
        ))[:10]
        if set(new_weak) != set(p.weak_areas or []):
            p.weak_areas = new_weak; updates["weak_areas"] = new_weak

        new_err = list(dict.fromkeys(
            (p.error_patterns or []) + [e[:60] for e in patterns["errors"][:3]]
        ))[:15]
        if set(new_err) != set(p.error_patterns or []):
            p.error_patterns = new_err; updates["error_patterns"] = new_err

        cm = llm.get("concept_map", {})
        if cm:
            cur = dict(p.topic_scores or {})
            for topic, score in cm.items():
                cur[topic] = round((cur.get(topic, score) * 0.7 + score * 0.3), 3)
            p.topic_scores = cur; updates["topic_scores"] = cur

        if llm.get("next_topics"):
            p.recommended_next = llm["next_topics"][:5]; updates["recommended_next"] = p.recommended_next

        p.last_updated_by_agent = datetime.now(timezone.utc)
        self.db.commit()
        return updates

    # ─── QUERY HELPERS ────────────────────────────────────────────────────────

    def get_reports(self, user_id: int, limit: int = 20):
        return (self.db.query(FeedbackReport)
                .filter(FeedbackReport.user_id == user_id)
                .order_by(FeedbackReport.created_at.desc())
                .limit(limit).all())

    def get_report(self, report_id: int, user_id: int):
        r = self.db.query(FeedbackReport).filter(
            FeedbackReport.id == report_id, FeedbackReport.user_id == user_id).first()
        if not r: raise ValueError("Report not found.")
        return r

    def mark_read(self, report_id: int, user_id: int):
        r = self.db.query(FeedbackReport).filter(
            FeedbackReport.id == report_id, FeedbackReport.user_id == user_id).first()
        if r: r.is_read = True; self.db.commit()

    def unread_count(self, user_id: int) -> int:
        return self.db.query(FeedbackReport).filter(
            FeedbackReport.user_id == user_id, FeedbackReport.is_read == False).count()