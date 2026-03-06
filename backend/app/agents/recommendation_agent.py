"""
Content Recommendation Agent
=============================
Architecture (Agentic Loop):
  Step 1 — Profile Extraction     : Pull user profile, learning history, weak areas
  Step 2 — Candidate Generation   : Collaborative Filtering (CF) + Content-Based Filtering (CBF)
  Step 3 — RL Exploration Bonus   : Add novelty boost so agent doesn't repeat same items
  Step 4 — LLM Reasoning (Groq)  : Agent reads candidates + profile → ranks + explains each pick
  Step 5 — Persist & Return       : Save recommendations + agent thought log to DB

The agent calls the Groq API (llama-3.3-70b-versatile) to act as a
"recommendation reasoning engine" — it receives the user context and candidate
list, then outputs ranked picks with natural-language justifications.
Groq is used for its extremely fast inference (low-latency agentic loops).
"""

import json
import uuid
import time
import math
import httpx
from datetime import datetime, timezone
from typing import List, Dict, Tuple, Any
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.user import User, LearningProfile
from app.models.recommendation import (
    Content, UserContentInteraction, Recommendation,
    AgentRunLog, InteractionType
)
from app.core.config import settings


# ─── Scoring weights ──────────────────────────────────────────────────────────
CF_WEIGHT   = 0.45
CBF_WEIGHT  = 0.40
RL_WEIGHT   = 0.15
TOP_N       = 10   # final recs to return
CANDIDATE_K = 30   # how many candidates to pass to LLM


class ContentRecommendationAgent:
    """
    Agentic AI system that recommends personalised learning content.
    Uses Collaborative Filtering + Content-Based Filtering + LLM reasoning.
    """

    def __init__(self, db: Session):
        self.db = db
        self.groq_api_key = settings.GROQ_API_KEY
        self.model = "llama-3.3-70b-versatile"   # fast + smart — ideal for agentic loops

    # ════════════════════════════════════════════════════════════════════════
    #  PUBLIC ENTRY POINT
    # ════════════════════════════════════════════════════════════════════════

    def run(self, user_id: int) -> Dict[str, Any]:
        """
        Main agentic loop. Returns dict with recommendations + thought steps.
        """
        batch_id  = str(uuid.uuid4())
        start_ms  = int(time.time() * 1000)
        step_log  = []

        # Create run log entry
        run_log = AgentRunLog(
            user_id=user_id,
            batch_id=batch_id,
            status="running",
            step_log=[],
        )
        self.db.add(run_log)
        self.db.commit()

        try:
            # ── Step 1: Extract user context ─────────────────────────────
            step_log.append("🔍 Step 1: Extracting user profile and learning history...")
            user_ctx = self._extract_user_context(user_id)
            step_log.append(
                f"   ✅ User: {user_ctx['username']} | Skill: {user_ctx['skill_level']} "
                f"| Languages: {', '.join(user_ctx['preferred_languages']) or 'none'} "
                f"| Seen: {user_ctx['seen_content_ids'].__len__()} items"
            )

            # ── Step 2a: Collaborative Filtering ─────────────────────────
            step_log.append("🤝 Step 2a: Running Collaborative Filtering (user-user similarity)...")
            cf_scores = self._collaborative_filtering(user_id, user_ctx)
            step_log.append(f"   ✅ CF found {len(cf_scores)} candidate items from similar users.")
            run_log.cf_candidates = len(cf_scores)

            # ── Step 2b: Content-Based Filtering ─────────────────────────
            step_log.append("📚 Step 2b: Running Content-Based Filtering (profile → topics)...")
            cbf_scores = self._content_based_filtering(user_ctx)
            step_log.append(f"   ✅ CBF found {len(cbf_scores)} topic-matched items.")
            run_log.cbf_candidates = len(cbf_scores)

            # ── Step 3: Merge + RL exploration bonus ─────────────────────
            step_log.append("⚙️  Step 3: Merging scores + applying RL exploration bonus...")
            merged = self._merge_and_rank(cf_scores, cbf_scores, user_ctx)
            candidates = merged[:CANDIDATE_K]
            step_log.append(
                f"   ✅ Top {len(candidates)} candidates selected for LLM reasoning."
            )

            # ── Step 4: LLM Reasoning (Claude Agent) ─────────────────────
            step_log.append("🤖 Step 4: Sending candidates to Claude agent for reasoning...")
            llm_result = self._llm_reasoning(user_ctx, candidates)
            ranked_ids   = llm_result["ranked_ids"]
            explanations = llm_result["explanations"]
            tokens_used  = llm_result["tokens_used"]
            step_log.append(
                f"   ✅ Claude ranked {len(ranked_ids)} items, used {tokens_used} tokens."
            )
            step_log.append("🧠 Step 4b: Claude's reasoning: " + llm_result.get("summary", ""))

            # ── Step 5: Persist recommendations ──────────────────────────
            step_log.append("💾 Step 5: Persisting recommendations to database...")
            # Delete previous non-clicked recs for this user
            self.db.query(Recommendation).filter(
                Recommendation.user_id == user_id,
                Recommendation.is_clicked == False,
                Recommendation.is_dismissed == False,
            ).delete()

            saved_recs = []
            for rank, cid in enumerate(ranked_ids[:TOP_N], start=1):
                candidate = next((c for c in candidates if c["content_id"] == cid), None)
                if not candidate:
                    continue
                rec = Recommendation(
                    user_id        = user_id,
                    content_id     = cid,
                    score          = candidate["blended_score"],
                    cf_score       = candidate["cf_score"],
                    cbf_score      = candidate["cbf_score"],
                    rl_bonus       = candidate["rl_bonus"],
                    agent_reasoning= explanations.get(str(cid), ""),
                    rank           = rank,
                    batch_id       = batch_id,
                )
                self.db.add(rec)
                saved_recs.append(rec)

            # Update run log
            duration = int(time.time() * 1000) - start_ms
            run_log.status          = "done"
            run_log.step_log        = step_log
            run_log.final_count     = len(saved_recs)
            run_log.llm_tokens_used = tokens_used
            run_log.duration_ms     = duration
            self.db.commit()

            step_log.append(f"✅ Done! Generated {len(saved_recs)} recommendations in {duration}ms.")

            return {
                "batch_id"          : batch_id,
                "user_id"           : user_id,
                "total"             : len(saved_recs),
                "agent_thought_steps": step_log,
                "generated_at"      : datetime.now(timezone.utc),
            }

        except Exception as exc:
            run_log.status        = "failed"
            run_log.error_message = str(exc)
            run_log.step_log      = step_log + [f"❌ Error: {exc}"]
            self.db.commit()
            raise

    # ════════════════════════════════════════════════════════════════════════
    #  STEP 1 — USER CONTEXT
    # ════════════════════════════════════════════════════════════════════════

    def _extract_user_context(self, user_id: int) -> Dict:
        user: User = self.db.query(User).filter(User.id == user_id).first()
        profile: LearningProfile = self.db.query(LearningProfile).filter(
            LearningProfile.user_id == user_id
        ).first()

        seen = self.db.query(UserContentInteraction.content_id).filter(
            UserContentInteraction.user_id == user_id
        ).all()
        seen_ids = {row[0] for row in seen}

        liked = self.db.query(UserContentInteraction).filter(
            UserContentInteraction.user_id == user_id,
            UserContentInteraction.rating >= 4.0,
        ).all()

        return {
            "user_id"            : user_id,
            "username"           : user.username,
            "skill_level"        : user.skill_level.value if user.skill_level else "beginner",
            "preferred_languages": user.preferred_languages or [],
            "learning_goals"     : user.learning_goals or [],
            "interests"          : user.interests or [],
            "weak_areas"         : profile.weak_areas if profile else [],
            "strong_areas"       : profile.strong_areas if profile else [],
            "topic_scores"       : profile.topic_scores if profile else {},
            "error_patterns"     : profile.error_patterns if profile else [],
            "seen_content_ids"   : seen_ids,
            "liked_content_ids"  : {i.content_id for i in liked},
            "accuracy_rate"      : profile.accuracy_rate if profile else 0.0,
        }

    # ════════════════════════════════════════════════════════════════════════
    #  STEP 2a — COLLABORATIVE FILTERING (user-user cosine similarity)
    # ════════════════════════════════════════════════════════════════════════

    def _collaborative_filtering(self, user_id: int, user_ctx: Dict) -> Dict[int, float]:
        """
        User-User CF:
        1. Build interaction vectors for all users
        2. Find K most similar users (cosine similarity)
        3. Recommend content those users liked that this user hasn't seen
        """
        # Fetch all interactions (limit to keep it fast)
        all_interactions = self.db.query(UserContentInteraction).filter(
            UserContentInteraction.implicit_score > 0
        ).all()

        if not all_interactions:
            return {}

        # Build user→content score matrix
        user_vectors: Dict[int, Dict[int, float]] = defaultdict(dict)
        for inter in all_interactions:
            score = inter.implicit_score if inter.implicit_score else 0.0
            if inter.rating:
                score = max(score, inter.rating / 5.0)
            user_vectors[inter.user_id][inter.content_id] = score

        if user_id not in user_vectors:
            return {}

        target_vec = user_vectors[user_id]

        # Cosine similarity with every other user
        def cosine_sim(a: Dict, b: Dict) -> float:
            common = set(a) & set(b)
            if not common:
                return 0.0
            dot    = sum(a[k] * b[k] for k in common)
            norm_a = math.sqrt(sum(v**2 for v in a.values()))
            norm_b = math.sqrt(sum(v**2 for v in b.values()))
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return dot / (norm_a * norm_b)

        similarities: List[Tuple[int, float]] = []
        for uid, vec in user_vectors.items():
            if uid == user_id:
                continue
            sim = cosine_sim(target_vec, vec)
            if sim > 0.05:
                similarities.append((uid, sim))

        similarities.sort(key=lambda x: x[1], reverse=True)
        top_neighbors = similarities[:20]   # top-20 neighbors

        # Weighted sum of neighbor scores for unseen content
        cf_scores: Dict[int, float] = defaultdict(float)
        sim_sum:   Dict[int, float] = defaultdict(float)

        for neighbor_id, sim in top_neighbors:
            for cid, score in user_vectors[neighbor_id].items():
                if cid not in user_ctx["seen_content_ids"]:
                    cf_scores[cid] += sim * score
                    sim_sum[cid]   += sim

        # Normalize
        return {
            cid: (cf_scores[cid] / sim_sum[cid]) if sim_sum[cid] > 0 else 0.0
            for cid in cf_scores
        }

    # ════════════════════════════════════════════════════════════════════════
    #  STEP 2b — CONTENT-BASED FILTERING (profile → topic match)
    # ════════════════════════════════════════════════════════════════════════

    def _content_based_filtering(self, user_ctx: Dict) -> Dict[int, float]:
        """
        Score every unseen content item by how well it matches the user profile:
        - Skill level alignment
        - Topic overlap with weak areas (priority) + interests
        - Language preference match
        - Learning goal alignment
        """
        contents: List[Content] = self.db.query(Content).filter(
            Content.is_active == True,
            ~Content.id.in_(user_ctx["seen_content_ids"] or {0}),
        ).all()

        skill_map = {"beginner": 0, "intermediate": 1, "advanced": 2}
        user_skill = skill_map.get(user_ctx["skill_level"], 0)

        cbf_scores: Dict[int, float] = {}

        for c in contents:
            score = 0.0
            content_skill = skill_map.get(c.difficulty.value, 0)

            # ── Skill level fit (penalise large mismatch) ──────────────
            skill_diff = abs(user_skill - content_skill)
            if skill_diff == 0:
                score += 0.30
            elif skill_diff == 1:
                score += 0.15
            else:
                score += 0.0   # too hard or too easy

            # ── Weak area overlap (highest priority!) ──────────────────
            weak_overlap = set(c.topics) & set(user_ctx["weak_areas"])
            score += min(len(weak_overlap) * 0.15, 0.30)

            # ── Interest overlap ───────────────────────────────────────
            interest_overlap = set(c.topics) & set(user_ctx["interests"])
            score += min(len(interest_overlap) * 0.08, 0.16)

            # ── Programming language match ─────────────────────────────
            if c.language and c.language in user_ctx["preferred_languages"]:
                score += 0.12

            # ── Learning goal match (skills_gained) ───────────────────
            goal_overlap = set(c.skills_gained) & set(user_ctx["learning_goals"])
            score += min(len(goal_overlap) * 0.06, 0.12)

            cbf_scores[c.id] = min(score, 1.0)

        return cbf_scores

    # ════════════════════════════════════════════════════════════════════════
    #  STEP 3 — MERGE + RL EXPLORATION BONUS
    # ════════════════════════════════════════════════════════════════════════

    def _merge_and_rank(
        self,
        cf_scores:  Dict[int, float],
        cbf_scores: Dict[int, float],
        user_ctx:   Dict,
    ) -> List[Dict]:
        """
        Blend CF + CBF scores.
        RL bonus: items from under-explored content types get a novelty boost
        so the agent diversifies (exploitation vs exploration trade-off).
        """
        all_ids = set(cf_scores) | set(cbf_scores)

        # Count content types the user has seen (for RL exploration)
        seen_types: Dict[str, int] = defaultdict(int)
        if user_ctx["seen_content_ids"]:
            rows = self.db.query(Content.id, Content.content_type).filter(
                Content.id.in_(user_ctx["seen_content_ids"])
            ).all()
            for _, ct in rows:
                seen_types[ct.value] += 1

        # Fetch content type for candidates
        cid_list = list(all_ids)
        type_rows = self.db.query(Content.id, Content.content_type).filter(
            Content.id.in_(cid_list)
        ).all()
        cid_to_type = {row[0]: row[1].value for row in type_rows}

        max_seen = max(seen_types.values(), default=1) or 1

        candidates = []
        for cid in all_ids:
            cf  = cf_scores.get(cid, 0.0)
            cbf = cbf_scores.get(cid, 0.0)
            ctype = cid_to_type.get(cid, "article")

            # RL exploration: boost less-seen types
            seen_count = seen_types.get(ctype, 0)
            rl_bonus   = RL_WEIGHT * (1.0 - seen_count / max_seen)

            blended = CF_WEIGHT * cf + CBF_WEIGHT * cbf + rl_bonus

            candidates.append({
                "content_id"    : cid,
                "cf_score"      : round(cf, 4),
                "cbf_score"     : round(cbf, 4),
                "rl_bonus"      : round(rl_bonus, 4),
                "blended_score" : round(min(blended, 1.0), 4),
                "content_type"  : ctype,
            })

        candidates.sort(key=lambda x: x["blended_score"], reverse=True)
        return candidates

    # ════════════════════════════════════════════════════════════════════════
    #  STEP 4 — LLM REASONING (Groq Agent)
    # ════════════════════════════════════════════════════════════════════════

    def _llm_reasoning(self, user_ctx: Dict, candidates: List[Dict]) -> Dict:
        """
        Send user profile + candidates to Groq (llama-3.3-70b-versatile).
        The model acts as a 'Learning Path Advisor' agent that:
        1. Re-ranks candidates using pedagogical reasoning
        2. Writes a short explanation for each pick
        3. Returns structured JSON
        Groq's ultra-low latency makes it perfect for real-time agentic loops.
        """
        # Fetch content details for candidates
        cids = [c["content_id"] for c in candidates]
        contents: List[Content] = self.db.query(Content).filter(Content.id.in_(cids)).all()
        content_map = {c.id: c for c in contents}

        # Build candidate summaries for prompt
        candidate_summaries = []
        for c in candidates:
            cobj = content_map.get(c["content_id"])
            if not cobj:
                continue
            candidate_summaries.append({
                "id"           : c["content_id"],
                "title"        : cobj.title,
                "type"         : cobj.content_type.value,
                "difficulty"   : cobj.difficulty.value,
                "language"     : cobj.language or "general",
                "topics"       : cobj.topics,
                "skills_gained": cobj.skills_gained,
                "duration_mins": cobj.duration_mins,
                "blended_score": c["blended_score"],
                "cf_score"     : c["cf_score"],
                "cbf_score"    : c["cbf_score"],
            })

        system_prompt = """You are the Content Recommendation Agent inside aiTA, an AI Teaching Assistant for programming education in India.
Your job is to act as an intelligent Learning Path Advisor.

Given a student's profile and a list of pre-scored content candidates, you must:
1. Re-rank the candidates using pedagogical reasoning (what makes sense to learn NEXT?)
2. Select the best TOP_N items
3. Write a short, encouraging explanation (2-3 sentences) for WHY each item is recommended

You MUST respond with ONLY a valid JSON object in this exact format:
{
  "summary": "one sentence summarizing your overall reasoning strategy",
  "ranked": [
    {
      "id": <content_id_int>,
      "explanation": "2-3 sentence explanation for why this content is recommended for this specific student"
    }
  ]
}

Rules:
- Prioritize filling WEAK AREAS first
- Then pursue LEARNING GOALS  
- Balance difficulty (don't recommend advanced if student is beginner)
- Diversify content types (mix videos, exercises, articles)
- Make explanations personal and specific to the student's profile
- Return exactly TOP_N items or fewer if candidates are limited
""".replace("TOP_N", str(TOP_N))

        user_prompt = f"""Student Profile:
- Username: {user_ctx['username']}
- Skill Level: {user_ctx['skill_level']}
- Programming Languages: {', '.join(user_ctx['preferred_languages']) or 'not specified'}
- Learning Goals: {', '.join(user_ctx['learning_goals']) or 'not specified'}
- Interests: {', '.join(user_ctx['interests']) or 'not specified'}
- Weak Areas (PRIORITY): {', '.join(user_ctx['weak_areas']) or 'none identified yet'}
- Strong Areas: {', '.join(user_ctx['strong_areas']) or 'none identified yet'}
- Accuracy Rate: {user_ctx['accuracy_rate']*100:.0f}%

Pre-scored Candidates (from collaborative filtering + content-based filtering):
{json.dumps(candidate_summaries, indent=2)}

Please re-rank these {len(candidate_summaries)} candidates and select the best {TOP_N} for this student.
Return ONLY valid JSON, no markdown, no extra text."""

        try:
            response = httpx.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.groq_api_key}",
                    "Content-Type" : "application/json",
                },
                json={
                    "model"      : self.model,
                    "max_tokens" : 2000,
                    "temperature": 0.3,   # lower = more deterministic JSON output
                    "messages"   : [
                        {"role": "system", "content": system_prompt},
                        {"role": "user",   "content": user_prompt},
                    ],
                },
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()

            raw_text    = data["choices"][0]["message"]["content"]
            tokens_used = data.get("usage", {}).get("total_tokens", 0)

            # Strip markdown code fences if Groq wraps JSON in them
            clean = raw_text.strip()
            if clean.startswith("```"):
                clean = clean.split("```")[1]
                if clean.startswith("json"):
                    clean = clean[4:]
            parsed = json.loads(clean.strip())

            ranked_ids   = [item["id"] for item in parsed.get("ranked", [])]
            explanations = {
                str(item["id"]): item["explanation"]
                for item in parsed.get("ranked", [])
            }
            summary = parsed.get("summary", "")

            return {
                "ranked_ids"  : ranked_ids,
                "explanations": explanations,
                "summary"     : summary,
                "tokens_used" : tokens_used,
            }

        except (httpx.HTTPError, json.JSONDecodeError, KeyError) as exc:
            # Graceful fallback: use blended score ranking without LLM
            fallback_ids = [c["content_id"] for c in candidates[:TOP_N]]
            return {
                "ranked_ids"  : fallback_ids,
                "explanations": {str(cid): "Recommended based on your learning profile and similar learners." for cid in fallback_ids},
                "summary"     : f"(LLM unavailable, using score-based ranking: {exc})",
                "tokens_used" : 0,
            }