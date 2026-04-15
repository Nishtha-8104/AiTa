"""
Content Recommendation Agent
==============================
Implements the full recommendation pipeline described in the aiTA paper:

  1. User Profile Extraction
     - Skill level, preferred languages, interested topics (from registration)
     - Learning history: lessons done, time spent per topic, error patterns
     - Problem-solving approach signals from code evaluations
     - Accuracy rate and improvement trajectory

  2. Content-Based Filtering (CBF)
     - Matches content to profile topics, languages, difficulty preference
     - Boosts content covering weak areas and error patterns
     - Penalises content on already-mastered strong areas

  3. Collaborative Filtering (CF)
     - Cosine similarity between user interaction vectors
     - Co-completion chains: users who finished X also finished Y
     - Weighted by recency and interaction quality

  4. Reinforcement Learning (RL) Exploration Bonus
     - Rewards under-explored content types and topics
     - Prevents the agent from always recommending the same format

  5. Learning Path Sequencing
     - Prerequisite-aware ordering (arrays → linked lists → trees)
     - Difficulty progression: foundation → target → stretch
     - Gap detection: topics with low accuracy get prioritised

  6. Groq LLM Re-ranking
     - Final re-rank with full profile context
     - Personalised explanations referencing actual user data
     - Fallback to score-based ranking if LLM unavailable
"""

import json
import uuid
import time
import math
import httpx
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from collections import defaultdict, Counter

from sqlalchemy.orm import Session

from app.models.user import User, LearningProfile
from app.models.recommendation import (
    Content, UserContentInteraction, Recommendation,
    AgentRunLog, DifficultyLevel,
)
from app.core.config import settings

# ─── Weights ──────────────────────────────────────────────────────────────────
CF_WEIGHT   = 0.35   # collaborative filtering
CBF_WEIGHT  = 0.45   # content-based filtering (profile-driven)
RL_WEIGHT   = 0.20   # exploration bonus
TOP_N       = 10
CANDIDATE_K = 40

YOUTUBE_API_URL  = "https://www.googleapis.com/youtube/v3"
GROQ_API_URL     = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL_PRIMARY  = "llama-3.3-70b-versatile"
GROQ_MODEL_FALLBACK = "llama3-8b-8192"

# ─── Learning path prerequisite chains ───────────────────────────────────────
# topic → [prerequisites that should come first]
PREREQUISITES: Dict[str, List[str]] = {
    "linked lists":        ["arrays"],
    "trees":               ["linked lists", "recursion"],
    "graphs":              ["trees", "recursion"],
    "dynamic programming": ["recursion", "arrays"],
    "backtracking":        ["recursion"],
    "binary search":       ["arrays", "sorting"],
    "sliding window":      ["arrays", "two pointers"],
    "two pointers":        ["arrays"],
    "hashing":             ["arrays"],
    "stacks queues":       ["arrays"],
    "greedy":              ["sorting", "arrays"],
    "bit manipulation":    ["math"],
    "design patterns":     ["oop"],
    "system design":       ["databases", "oop"],
    "machine learning":    ["math", "python"],
    "react":               ["javascript", "web development"],
    "django":              ["python", "databases"],
    "spring":              ["java", "oop"],
}

# topic → adjacent topics to suggest when this topic is exhausted
TOPIC_ADJACENCY: Dict[str, List[str]] = {
    "arrays":              ["linked lists", "sorting", "binary search", "two pointers"],
    "linked lists":        ["arrays", "stacks queues", "trees"],
    "trees":               ["graphs", "dynamic programming", "recursion"],
    "graphs":              ["trees", "dynamic programming", "backtracking"],
    "dynamic programming": ["recursion", "greedy", "trees"],
    "recursion":           ["dynamic programming", "backtracking", "trees"],
    "sorting":             ["arrays", "binary search", "greedy"],
    "binary search":       ["arrays", "sorting", "two pointers"],
    "hashing":             ["arrays", "strings", "two pointers"],
    "stacks queues":       ["arrays", "linked lists", "trees"],
    "backtracking":        ["recursion", "dynamic programming", "graphs"],
    "greedy":              ["dynamic programming", "sorting", "arrays"],
    "bit manipulation":    ["math", "arrays", "dynamic programming"],
    "math":                ["bit manipulation", "dynamic programming", "greedy"],
    "strings":             ["arrays", "hashing", "dynamic programming"],
    "two pointers":        ["arrays", "binary search", "sliding window"],
    "sliding window":      ["arrays", "two pointers", "strings"],
    "oop":                 ["design patterns", "recursion"],
    "design patterns":     ["oop", "system design"],
    "python":              ["algorithms", "data structures"],
    "javascript":          ["web development", "react"],
    "java":                ["oop", "spring"],
}

# topic → skills gained
TOPIC_SKILLS: Dict[str, List[str]] = {
    "arrays":              ["array manipulation", "problem solving", "DSA"],
    "linked lists":        ["pointer logic", "DSA", "memory management"],
    "trees":               ["tree traversal", "recursion", "DSA"],
    "graphs":              ["graph traversal", "BFS", "DFS", "shortest path"],
    "dynamic programming": ["memoization", "tabulation", "optimization"],
    "recursion":           ["recursive thinking", "base cases", "call stack"],
    "sorting":             ["comparison sorts", "divide and conquer", "DSA"],
    "hashing":             ["hash maps", "collision handling", "O(1) lookup"],
    "stacks queues":       ["LIFO/FIFO", "monotonic stack", "BFS"],
    "backtracking":        ["state space search", "pruning", "combinatorics"],
    "bit manipulation":    ["bitwise ops", "XOR tricks", "space optimization"],
    "greedy":              ["greedy choice", "interval scheduling", "optimization"],
    "math":                ["number theory", "modular arithmetic", "combinatorics"],
    "strings":             ["string matching", "sliding window", "pattern search"],
    "two pointers":        ["two pointer technique", "in-place algorithms"],
    "sliding window":      ["window management", "subarray problems"],
    "oop":                 ["classes", "inheritance", "polymorphism", "encapsulation"],
    "design patterns":     ["SOLID principles", "software architecture", "reusability"],
    "databases":           ["SQL", "normalization", "indexing", "query optimization"],
    "web development":     ["HTML", "CSS", "JavaScript", "REST APIs"],
    "machine learning":    ["supervised learning", "model training", "scikit-learn"],
    "system design":       ["scalability", "microservices", "caching", "load balancing"],
}

_DIFF_MAP = {
    "easy": "beginner", "beginner": "beginner",
    "medium": "intermediate", "intermediate": "intermediate",
    "hard": "advanced", "advanced": "advanced",
}
_TYPE_ROTATION = ["video", "tutorial", "article", "exercise", "project"]


# ══════════════════════════════════════════════════════════════════════════════
#  YOUTUBE SEARCH TOOL
# ══════════════════════════════════════════════════════════════════════════════

class YouTubeSearchTool:
    def __init__(self, api_key: str):
        self.api_key = api_key

    def search(self, query: str, max_results: int = 3) -> List[Dict]:
        if not self.api_key:
            return []
        try:
            r = httpx.get(
                f"{YOUTUBE_API_URL}/search",
                params={"part": "snippet", "q": query + " tutorial",
                        "type": "video", "maxResults": max_results,
                        "relevanceLanguage": "en", "videoDuration": "medium",
                        "key": self.api_key},
                timeout=6.0,
            )
            r.raise_for_status()
            items = r.json().get("items", [])
            if not items:
                return []

            ids = [i["id"]["videoId"] for i in items]
            sr = httpx.get(
                f"{YOUTUBE_API_URL}/videos",
                params={"part": "statistics,contentDetails,snippet",
                        "id": ",".join(ids), "key": self.api_key},
                timeout=6.0,
            )
            sr.raise_for_status()
            stat_map = {v["id"]: v for v in sr.json().get("items", [])}

            videos = []
            for item in items:
                vid = item["id"]["videoId"]
                s   = stat_map.get(vid, {})
                st  = s.get("statistics", {})
                sn  = s.get("snippet", item.get("snippet", {}))
                views = int(st.get("viewCount", 0))
                likes = int(st.get("likeCount", 0))
                dur   = self._parse_duration(s.get("contentDetails", {}).get("duration", "PT0M"))
                q     = round(min(views/1_000_000,1)*0.5 + min(likes/50_000,1)*0.3 + 0.2, 4)
                videos.append({
                    "id": vid, "title": sn.get("title", ""),
                    "url": f"https://www.youtube.com/watch?v={vid}",
                    "thumbnail": sn.get("thumbnails", {}).get("medium", {}).get("url"),
                    "channel": sn.get("channelTitle", ""),
                    "views": views, "likes": likes,
                    "duration_mins": dur, "quality_score": q,
                })
            videos.sort(key=lambda v: v["quality_score"], reverse=True)
            return videos
        except Exception:
            return []

    def _parse_duration(self, iso: str) -> float:
        import re
        h = re.search(r'(\d+)H', iso)
        m = re.search(r'(\d+)M', iso)
        s = re.search(r'(\d+)S', iso)
        return round(
            (int(h.group(1)) * 60 if h else 0) +
            (int(m.group(1)) if m else 0) +
            (int(s.group(1)) / 60 if s else 0), 1
        )


# ══════════════════════════════════════════════════════════════════════════════
#  PROFILE-DRIVEN CONTENT GENERATOR
#  Creates Content rows from user's profile topics + languages.
#  Two-phase: fast insert first, YouTube backfill second.
# ══════════════════════════════════════════════════════════════════════════════

def _generate_content_for_profile(db: Session, yt: YouTubeSearchTool, user_ctx: Dict) -> int:
    topics    = user_ctx["interested_topics"] or []
    languages = user_ctx["preferred_languages"] or ["python"]
    skill     = user_ctx["skill_level"]
    diff_pref = user_ctx["difficulty_pref"]

    target_diff = _DIFF_MAP.get(diff_pref, _DIFF_MAP.get(skill, "intermediate"))
    diff_ladder = {
        "beginner":     ["beginner", "intermediate"],
        "intermediate": ["beginner", "intermediate", "advanced"],
        "advanced":     ["intermediate", "advanced"],
    }
    difficulties = diff_ladder.get(target_diff, ["intermediate"])

    # Load existing content in-memory to avoid JSON LIKE queries
    existing_rows = db.query(
        Content.title, Content.language, Content.difficulty, Content.topics
    ).filter(Content.is_active == True).all()

    combo_counts: Counter = Counter()
    existing_titles: set  = set()
    for row in existing_rows:
        existing_titles.add(row.title)
        row_lang = (row.language or "").lower()
        row_diff = (row.difficulty.value if hasattr(row.difficulty, "value") else str(row.difficulty)).lower()
        for t in (row.topics or []):
            combo_counts[(t.lower(), row_lang, row_diff)] += 1

    created   = 0
    new_items = []

    # Phase 1: insert rows immediately (no YouTube — keeps it fast)
    for topic_raw in topics:
        topic         = topic_raw.lower().replace("_", " ")
        skills_gained = TOPIC_SKILLS.get(topic_raw.lower(), [topic, "problem solving"])

        for lang in languages[:3]:
            lang_lower = lang.lower()
            for difficulty in difficulties:
                if combo_counts.get((topic, lang_lower, difficulty.lower()), 0) >= 2:
                    continue
                title = f"{topic.title()} — {lang.title()} ({difficulty.title()})"[:500]
                if title in existing_titles:
                    continue
                content_type = _TYPE_ROTATION[created % len(_TYPE_ROTATION)]
                c = Content(
                    title=title,
                    description=f"Learn {topic} in {lang} at {difficulty} level.",
                    content_type=content_type, difficulty=difficulty,
                    language=lang.title(), topics=[topic],
                    skills_gained=skills_gained, source="YouTube",
                    avg_rating=4.5, duration_mins=30,
                    url=None, thumbnail_url=None, author=None, is_active=True,
                )
                db.add(c)
                new_items.append((c, topic, lang, difficulty))
                existing_titles.add(title)
                combo_counts[(topic, lang_lower, difficulty.lower())] += 1
                created += 1

    if created > 0:
        db.commit()

    # Phase 2: backfill YouTube URLs (best-effort, non-blocking)
    if yt.api_key and new_items:
        updated = 0
        for content_obj, topic, lang, difficulty in new_items:
            try:
                videos = yt.search(f"{topic} {lang} {difficulty} tutorial", max_results=2)
                if videos:
                    best = videos[0]
                    content_obj.url           = best["url"]
                    content_obj.thumbnail_url = best["thumbnail"]
                    content_obj.author        = best["channel"]
                    if best["title"]:
                        content_obj.title = best["title"][:500]
                    if best["duration_mins"]:
                        content_obj.duration_mins = best["duration_mins"]
                    updated += 1
            except Exception:
                pass
        if updated > 0:
            db.commit()

    return created


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN AGENT
# ══════════════════════════════════════════════════════════════════════════════

class ContentRecommendationAgent:

    def __init__(self, db: Session):
        self.db           = db
        self.groq_api_key = settings.GROQ_API_KEY
        self.yt           = YouTubeSearchTool(getattr(settings, "YOUTUBE_API_KEY", ""))

    # ── PUBLIC ENTRY POINT ────────────────────────────────────────────────────

    def run(self, user_id: int) -> Dict[str, Any]:
        batch_id = str(uuid.uuid4())
        start_ms = int(time.time() * 1000)
        step_log: List[str] = []

        run_log = AgentRunLog(user_id=user_id, batch_id=batch_id, status="running", step_log=[])
        self.db.add(run_log)
        self.db.commit()

        try:
            # ── Step 1: Extract full user profile ────────────────────────
            step_log.append("🔍 Step 1: Reading your learning profile, history & error patterns...")
            user_ctx = self._extract_user_context(user_id)

            if not user_ctx["interested_topics"]:
                # Last resort: derive topics from learning_goals and interests
                fallback_topics = (user_ctx.get("learning_goals") or []) + (user_ctx.get("interests") or [])
                if fallback_topics:
                    user_ctx["interested_topics"] = fallback_topics
                    step_log.append(f"   ℹ️  No explicit topics set — using goals/interests as topics: {fallback_topics[:4]}")
                else:
                    step_log.append("⚠️  Profile has no topics, interests, or goals — add them in your profile for better recommendations.")
                    # Continue anyway with general content rather than bailing out

            step_log.append(
                f"   ✅ {user_ctx['username']} | {user_ctx['skill_level']} | "
                f"Topics: {user_ctx['interested_topics']} | "
                f"Languages: {user_ctx['preferred_languages']} | "
                f"Weak areas: {user_ctx['weak_areas'] or 'none yet'} | "
                f"Error patterns: {user_ctx['error_patterns'][:2] or 'none yet'} | "
                f"Accuracy: {user_ctx['accuracy_rate']:.0%} | "
                f"Excluded (done/dismissed): {len(user_ctx['excluded_ids'])}"
            )

            # ── Step 2: Generate profile-driven content catalog ───────────
            step_log.append("🎯 Step 2: Generating content for your topics & languages...")
            new_items = _generate_content_for_profile(self.db, self.yt, user_ctx)
            total = self.db.query(Content).filter(Content.is_active == True).count()
            step_log.append(f"   ✅ {new_items} new items created. Catalog: {total} total.")

            # ── Step 3: Detect knowledge gaps & learning path ─────────────
            step_log.append("🗺️  Step 3: Analysing knowledge gaps and learning path...")
            gap_topics, next_topics = self._analyse_learning_path(user_ctx)
            step_log.append(
                f"   ✅ Gaps detected: {gap_topics or 'none'} | "
                f"Suggested next: {next_topics or 'continuing current topics'}"
            )

            # ── Step 4a: Collaborative Filtering ─────────────────────────
            step_log.append("🤝 Step 4a: Collaborative Filtering — finding similar learners...")
            cf_scores = self._collaborative_filtering(user_id, user_ctx)
            step_log.append(
                f"   ✅ CF found {len(cf_scores)} candidates from similar learner paths."
            )
            run_log.cf_candidates = len(cf_scores)

            # ── Step 4b: Content-Based Filtering ─────────────────────────
            step_log.append("📚 Step 4b: Content-Based Filtering — matching your profile...")
            cbf_scores = self._content_based_filtering(user_ctx, gap_topics)
            step_log.append(
                f"   ✅ CBF scored {len(cbf_scores)} items "
                f"(prioritising: {(gap_topics + user_ctx['interested_topics'])[:3]})."
            )
            run_log.cbf_candidates = len(cbf_scores)

            # ── Step 4c: Related-topic expansion if needed ────────────────
            raw_count = len(set(cf_scores) | set(cbf_scores))
            expansion_scores: Dict[int, float] = {}
            if raw_count < TOP_N:
                step_log.append(f"🔗 Step 4c: Only {raw_count} fresh items — expanding to adjacent topics...")
                expansion_scores = self._expand_related_topics(user_ctx, next_topics)
                step_log.append(f"   ✅ Expansion added {len(expansion_scores)} adjacent-topic items.")
            else:
                step_log.append(f"   ℹ️  {raw_count} fresh candidates — no expansion needed.")

            # ── Step 5: Merge + RL exploration bonus ─────────────────────
            step_log.append("⚙️  Step 5: Merging CF + CBF + RL exploration bonus...")
            merged     = self._merge_and_rank(cf_scores, cbf_scores, user_ctx, expansion_scores)
            candidates = merged[:CANDIDATE_K]
            step_log.append(
                f"   ✅ {len(candidates)} diverse candidates after RL diversity enforcement."
            )

            # ── Step 6: Groq LLM re-ranking ───────────────────────────────
            step_log.append("🤖 Step 6: Groq AI re-ranking with full profile context...")
            llm_result   = self._llm_reasoning(user_ctx, candidates, gap_topics, next_topics)
            ranked_ids   = llm_result["ranked_ids"]
            explanations = llm_result["explanations"]
            descriptions = llm_result.get("descriptions", {})
            difficulties = llm_result.get("difficulties", {})
            tokens_used  = llm_result["tokens_used"]
            step_log.append(
                f"   ✅ Groq ranked {len(ranked_ids)} items "
                f"({tokens_used} tokens, model: {llm_result.get('model_used','fallback')})."
            )
            step_log.append("🧠 Strategy: " + llm_result.get("summary", ""))

            # ── Step 7: Persist ───────────────────────────────────────────
            step_log.append("💾 Step 7: Saving your personalised recommendations...")
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
                # Pack LLM-generated fields into agent_reasoning as JSON
                reasoning_payload = json.dumps({
                    "description":  descriptions.get(str(cid), ""),
                    "difficulty":   difficulties.get(str(cid), ""),
                    "why_relevant": explanations.get(str(cid), ""),
                })
                self.db.add(Recommendation(
                    user_id=user_id, content_id=cid,
                    score=candidate["blended_score"],
                    cf_score=candidate["cf_score"],
                    cbf_score=candidate["cbf_score"],
                    rl_bonus=candidate["rl_bonus"],
                    agent_reasoning=reasoning_payload,
                    rank=rank, batch_id=batch_id,
                ))
                saved_recs.append(cid)

            duration = int(time.time() * 1000) - start_ms
            run_log.status = "done"; run_log.step_log = step_log
            run_log.final_count = len(saved_recs)
            run_log.llm_tokens_used = tokens_used
            run_log.duration_ms = duration
            self.db.commit()
            step_log.append(f"✅ Done! {len(saved_recs)} personalised recommendations in {duration}ms.")

            return {
                "batch_id": batch_id, "user_id": user_id, "total": len(saved_recs),
                "agent_thought_steps": step_log, "generated_at": datetime.now(timezone.utc),
            }

        except Exception as exc:
            try: self.db.rollback()
            except Exception: pass
            try:
                run_log.status = "failed"
                run_log.error_message = str(exc)
                run_log.step_log = step_log + [f"❌ Error: {exc}"]
                self.db.commit()
            except Exception: pass
            raise

    # ── USER CONTEXT ──────────────────────────────────────────────────────────

    def _extract_user_context(self, user_id: int) -> Dict:
        user    = self.db.query(User).filter(User.id == user_id).first()
        profile = self.db.query(LearningProfile).filter(LearningProfile.user_id == user_id).first()

        interactions = self.db.query(UserContentInteraction).filter(
            UserContentInteraction.user_id == user_id
        ).all()

        seen_ids      = {i.content_id for i in interactions}
        completed_ids = {i.content_id for i in interactions if i.is_completed or i.completion_pct >= 80}
        liked_ids     = {i.content_id for i in interactions if (i.rating or 0) >= 4.0}
        disliked_ids  = {i.content_id for i in interactions if (i.rating or 0) <= 2.0}

        dismissed_ids = {r[0] for r in self.db.query(Recommendation.content_id).filter(
            Recommendation.user_id == user_id, Recommendation.is_dismissed == True
        ).all()}

        excluded_ids = completed_ids | dismissed_ids | disliked_ids

        # Time spent per topic — derived from interactions on content
        time_per_topic: Dict[str, float] = defaultdict(float)
        completed_content = self.db.query(Content).filter(
            Content.id.in_(completed_ids)
        ).all() if completed_ids else []
        for c in completed_content:
            for t in (c.topics or []):
                time_per_topic[t.lower()] += c.duration_mins or 0

        # Parse difficulty preference from learning_goals
        learning_goals = user.learning_goals or [] if user else []
        difficulty_pref = "medium"
        for g in learning_goals:
            if g.startswith("difficulty:"):
                difficulty_pref = g.split(":", 1)[1].strip()
                break

        return {
            "user_id":             user_id,
            "username":            user.username if user else "student",
            "skill_level":         user.skill_level.value if user and user.skill_level else "beginner",
            "difficulty_pref":     difficulty_pref,
            "preferred_languages": [l.lower() for l in (user.preferred_languages or [])] if user else [],
            "learning_goals":      [g for g in learning_goals if not g.startswith("difficulty:")],
            "interests":           user.interests or [] if user else [],
            "interested_topics":   (
                user.interested_topics or []
                if user else []
            ) or (user.interests or [] if user else []),
            "weak_areas":          profile.weak_areas if profile else [],
            "strong_areas":        profile.strong_areas if profile else [],
            "topic_scores":        profile.topic_scores if profile else {},
            "error_patterns":      profile.error_patterns if profile else [],
            "preferred_content_types": profile.preferred_content_types if profile else [],
            "accuracy_rate":       profile.accuracy_rate if profile else 0.0,
            "improvement_rate":    profile.improvement_rate if profile else 0.0,
            "time_per_topic":      dict(time_per_topic),
            "seen_content_ids":    seen_ids,
            "completed_ids":       completed_ids,
            "dismissed_ids":       dismissed_ids,
            "excluded_ids":        excluded_ids,
            "liked_ids":           liked_ids,
            "disliked_ids":        disliked_ids,
        }

    # ── LEARNING PATH ANALYSIS ────────────────────────────────────────────────

    def _analyse_learning_path(self, user_ctx: Dict):
        """
        Detects knowledge gaps and determines what to learn next.

        Gap detection:
          - Topics with topic_score < 0.5 (low accuracy)
          - Topics in error_patterns (recurring mistakes)
          - Topics in weak_areas (agent-flagged)

        Next topics:
          - Prerequisites of interested topics not yet started
          - Adjacent topics after completing current ones
        """
        topic_scores  = user_ctx["topic_scores"]
        weak_areas    = {t.lower() for t in user_ctx["weak_areas"]}
        error_topics  = {e.lower() for e in user_ctx["error_patterns"]}
        interested    = [t.lower().replace("_", " ") for t in user_ctx["interested_topics"]]
        time_per_topic = user_ctx["time_per_topic"]

        # Gap topics: low score OR in weak_areas OR in error_patterns
        gap_topics: List[str] = []
        for topic in interested:
            score = topic_scores.get(topic, None)
            if topic in weak_areas or topic in error_topics:
                gap_topics.append(topic)
            elif score is not None and score < 0.5:
                gap_topics.append(topic)

        # Next topics: prerequisites not yet covered + adjacency suggestions
        next_topics: List[str] = []
        for topic in interested:
            prereqs = PREREQUISITES.get(topic, [])
            for p in prereqs:
                if p not in interested and p not in next_topics:
                    # Only suggest if user hasn't spent time on it
                    if time_per_topic.get(p, 0) < 30:
                        next_topics.append(p)

        # If no gaps and no next, suggest adjacency
        if not next_topics:
            for topic in interested:
                for adj in TOPIC_ADJACENCY.get(topic, []):
                    if adj not in interested and adj not in next_topics:
                        next_topics.append(adj)
                        if len(next_topics) >= 3:
                            break

        return gap_topics[:5], next_topics[:5]

    # ── COLLABORATIVE FILTERING ───────────────────────────────────────────────

    def _collaborative_filtering(self, user_id: int, user_ctx: Dict) -> Dict[int, float]:
        """
        Two-part CF:
        1. Cosine similarity between user interaction vectors (standard CF)
        2. Co-completion chains: users who completed X also completed Y
           → recommend Y to users who completed X (like JS → React)
        """
        all_interactions = self.db.query(UserContentInteraction).filter(
            UserContentInteraction.implicit_score > 0
        ).all()
        if not all_interactions:
            return {}

        # Build user vectors: user_id → {content_id: score}
        user_vectors: Dict[int, Dict[int, float]] = defaultdict(dict)
        for inter in all_interactions:
            score = inter.implicit_score or 0.0
            if inter.rating:
                score = max(score, inter.rating / 5.0)
            # Recency boost: more recent interactions count more
            user_vectors[inter.user_id][inter.content_id] = score

        excluded = user_ctx["excluded_ids"] | user_ctx["seen_content_ids"]

        # ── Part 1: Standard cosine similarity CF ─────────────────────────────
        cf_scores: Dict[int, float] = defaultdict(float)
        sim_sum:   Dict[int, float] = defaultdict(float)

        if user_id in user_vectors:
            target_vec = user_vectors[user_id]

            def cosine_sim(a: Dict, b: Dict) -> float:
                common = set(a) & set(b)
                if not common: return 0.0
                dot    = sum(a[k] * b[k] for k in common)
                norm_a = math.sqrt(sum(v**2 for v in a.values()))
                norm_b = math.sqrt(sum(v**2 for v in b.values()))
                return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0

            similarities = sorted(
                [(uid, cosine_sim(target_vec, vec))
                 for uid, vec in user_vectors.items() if uid != user_id],
                key=lambda x: x[1], reverse=True
            )[:20]

            for neighbor_id, sim in similarities:
                if sim <= 0.05: continue
                for cid, score in user_vectors[neighbor_id].items():
                    if cid not in excluded:
                        cf_scores[cid] += sim * score
                        sim_sum[cid]   += sim

        standard_cf = {
            cid: (cf_scores[cid] / sim_sum[cid]) if sim_sum[cid] > 0 else 0.0
            for cid in cf_scores
        }

        # ── Part 2: Co-completion chains ──────────────────────────────────────
        # Find content the user completed, then find what other users completed next
        completed_ids = user_ctx["completed_ids"]
        co_completion: Dict[int, float] = defaultdict(float)

        if completed_ids:
            # Users who also completed the same content
            similar_users = set()
            for inter in all_interactions:
                if inter.content_id in completed_ids and inter.user_id != user_id:
                    if inter.is_completed or inter.completion_pct >= 80:
                        similar_users.add(inter.user_id)

            # What did those users complete AFTER?
            for inter in all_interactions:
                if (inter.user_id in similar_users and
                    inter.content_id not in excluded and
                    (inter.is_completed or inter.completion_pct >= 80)):
                    # Weight by how many similar users completed it
                    co_completion[inter.content_id] += 1.0

            # Normalise co-completion scores to 0-1
            max_co = max(co_completion.values(), default=1) or 1
            co_completion = {cid: v / max_co for cid, v in co_completion.items()}

        # Merge: standard CF + co-completion boost
        all_cids = set(standard_cf) | set(co_completion)
        merged_cf = {}
        for cid in all_cids:
            merged_cf[cid] = round(
                standard_cf.get(cid, 0.0) * 0.7 + co_completion.get(cid, 0.0) * 0.3, 4
            )

        return merged_cf

    # ── CONTENT-BASED FILTERING ───────────────────────────────────────────────

    def _content_based_filtering(self, user_ctx: Dict, gap_topics: List[str]) -> Dict[int, float]:
        """
        Profile-driven CBF with gap-aware scoring.

        Scoring priority:
          1. Gap topics (low accuracy / error patterns) — highest boost
          2. Interested topics from profile
          3. Weak areas (agent-detected)
          4. Language match
          5. Difficulty alignment (skill_level + difficulty_pref)
          6. Learning goals / interests
          7. Preferred content types
          8. Quality signal (avg_rating)
        """
        excluded = user_ctx["excluded_ids"] | user_ctx["seen_content_ids"]
        contents = self.db.query(Content).filter(
            Content.is_active == True,
            ~Content.id.in_(excluded or {0}),
        ).all()

        skill_map     = {"beginner": 0, "intermediate": 1, "advanced": 2}
        user_skill    = skill_map.get(user_ctx["skill_level"], 0)
        diff_pref_map = {"easy": 0, "medium": 1, "hard": 2}
        target_diff   = diff_pref_map.get(user_ctx["difficulty_pref"], user_skill)

        gap_set       = {t.lower() for t in gap_topics}
        interested    = {t.lower().replace("_", " ") for t in user_ctx["interested_topics"]}
        weak_areas    = {t.lower() for t in user_ctx["weak_areas"]}
        pref_langs    = {l.lower() for l in user_ctx["preferred_languages"]}
        interests     = {t.lower() for t in user_ctx["interests"]}
        goals         = {g.lower() for g in user_ctx["learning_goals"]}
        pref_types    = {t.lower() for t in user_ctx["preferred_content_types"]}
        topic_scores  = {k.lower(): v for k, v in user_ctx["topic_scores"].items()}
        error_topics  = {e.lower() for e in user_ctx["error_patterns"]}

        cbf_scores: Dict[int, float] = {}

        for c in contents:
            score    = 0.0
            c_topics = {t.lower().replace("_", " ") for t in (c.topics or [])}
            c_skills = {s.lower() for s in (c.skills_gained or [])}
            c_lang   = (c.language or "").lower()
            c_diff   = skill_map.get(c.difficulty.value, 0)

            # 1. Gap topics — highest priority (student needs this most)
            gap_overlap = c_topics & gap_set
            if gap_overlap:
                score += min(len(gap_overlap) * 0.30, 0.60)

            # 2. Interested topics from profile
            topic_overlap = c_topics & interested
            if topic_overlap:
                score += min(len(topic_overlap) * 0.20, 0.40)
                # Extra boost for topics with low mastery score
                for t in topic_overlap:
                    ts = topic_scores.get(t, 0.5)
                    if ts < 0.5:
                        score += 0.08

            # 3. Error pattern topics — student keeps making mistakes here
            error_overlap = c_topics & error_topics
            score += min(len(error_overlap) * 0.12, 0.24)

            # 4. Weak areas (agent-detected)
            weak_overlap = c_topics & weak_areas
            score += min(len(weak_overlap) * 0.10, 0.20)

            # 5. Language match
            if c_lang and c_lang in pref_langs:
                score += 0.15
            elif c_lang in ("general", ""):
                score += 0.03

            # 6. Difficulty alignment
            diff_gap = abs(c_diff - target_diff)
            if diff_gap == 0:
                score += 0.20
            elif diff_gap == 1:
                score += 0.08

            # 7. Interests + learning goals
            score += min(len(c_topics & interests) * 0.05, 0.10)
            score += min(len(c_skills & goals) * 0.04, 0.08)

            # 8. Preferred content type
            if pref_types and c.content_type.value in pref_types:
                score += 0.06

            # 9. Quality signal
            if c.avg_rating >= 4.5:
                score += 0.05
            elif c.avg_rating >= 4.0:
                score += 0.02

            cbf_scores[c.id] = min(score, 1.0)

        return cbf_scores

    # ── RELATED TOPIC EXPANSION ───────────────────────────────────────────────

    def _expand_related_topics(self, user_ctx: Dict, next_topics: List[str]) -> Dict[int, float]:
        """Finds content on adjacent/prerequisite topics when fresh content is scarce."""
        excluded  = user_ctx["excluded_ids"] | user_ctx["seen_content_ids"]
        interested = {t.lower().replace("_", " ") for t in user_ctx["interested_topics"]}
        pref_langs = {l.lower() for l in user_ctx["preferred_languages"]}
        skill_map  = {"beginner": 0, "intermediate": 1, "advanced": 2}
        user_skill = skill_map.get(user_ctx["skill_level"], 0)
        diff_pref_map = {"easy": 0, "medium": 1, "hard": 2}
        target_diff = diff_pref_map.get(user_ctx["difficulty_pref"], user_skill)

        # Combine next_topics with adjacency suggestions
        related = set(next_topics)
        for topic in interested:
            for adj in TOPIC_ADJACENCY.get(topic, []):
                if adj not in interested:
                    related.add(adj)

        if not related:
            return {}

        all_unseen = self.db.query(Content).filter(
            Content.is_active == True,
            ~Content.id.in_(excluded or {0}),
        ).all()

        expansion: Dict[int, float] = {}
        for c in all_unseen:
            c_topics = {t.lower().replace("_", " ") for t in (c.topics or [])}
            overlap  = c_topics & related
            if not overlap:
                continue
            score = min(len(overlap) * 0.18, 0.36)
            c_diff = skill_map.get(c.difficulty.value, 0)
            if abs(c_diff - target_diff) == 0: score += 0.12
            elif abs(c_diff - target_diff) == 1: score += 0.04
            if (c.language or "").lower() in pref_langs: score += 0.08
            expansion[c.id] = min(score * 0.75, 0.55)  # slightly lower than direct match

        return expansion

    # ── MERGE + RL EXPLORATION BONUS ─────────────────────────────────────────

    def _merge_and_rank(
        self, cf_scores: Dict, cbf_scores: Dict,
        user_ctx: Dict, expansion_scores: Dict = None,
    ) -> List[Dict]:
        """
        Merges CF + CBF + expansion, applies RL exploration bonus,
        enforces content-type and topic diversity.

        RL bonus: rewards content types and topics the user hasn't explored much.
        This prevents the agent from always recommending the same format.
        """
        expansion_scores = expansion_scores or {}
        all_ids = set(cf_scores) | set(cbf_scores) | set(expansion_scores)
        if not all_ids:
            return []

        # Count seen content types (for RL exploration)
        seen_types: Dict[str, int] = defaultdict(int)
        if user_ctx["seen_content_ids"]:
            for _, ct in self.db.query(Content.id, Content.content_type).filter(
                Content.id.in_(user_ctx["seen_content_ids"])
            ).all():
                seen_types[ct.value] += 1

        rows = self.db.query(
            Content.id, Content.content_type, Content.topics, Content.language
        ).filter(Content.id.in_(list(all_ids))).all()

        cid_to_type   = {r[0]: r[1].value for r in rows}
        cid_to_topics = {r[0]: (r[2] or []) for r in rows}
        cid_to_lang   = {r[0]: (r[3] or "").lower() for r in rows}
        max_seen      = max(seen_types.values(), default=1) or 1
        pref_langs    = {l.lower() for l in user_ctx["preferred_languages"]}

        candidates = []
        for cid in all_ids:
            cf  = cf_scores.get(cid, 0.0)
            cbf = cbf_scores.get(cid, 0.0)
            exp = expansion_scores.get(cid, 0.0)
            ct  = cid_to_type.get(cid, "article")

            # RL: reward under-explored content types
            rl = RL_WEIGHT * (1.0 - seen_types.get(ct, 0) / max_seen)

            # Language bonus
            lang_bonus = 0.05 if cid_to_lang.get(cid, "") in pref_langs else 0.0

            effective_cbf = max(cbf, exp)
            blended = round(
                min(CF_WEIGHT * cf + CBF_WEIGHT * effective_cbf + rl + lang_bonus, 1.0), 4
            )

            candidates.append({
                "content_id":    cid,
                "cf_score":      round(cf, 4),
                "cbf_score":     round(effective_cbf, 4),
                "rl_bonus":      round(rl, 4),
                "blended_score": blended,
                "content_type":  ct,
                "topics":        cid_to_topics.get(cid, []),
                "is_expansion":  cid in expansion_scores and cid not in cbf_scores,
            })

        candidates.sort(key=lambda x: x["blended_score"], reverse=True)

        # Diversity enforcement: max 3 per content_type, max 2 per primary topic
        type_count:  Dict[str, int] = defaultdict(int)
        topic_count: Dict[str, int] = defaultdict(int)
        diverse, overflow = [], []

        for c in candidates:
            ct    = c["content_type"]
            ptopic = (c["topics"][0] if c["topics"] else "general").lower()
            if type_count[ct] < 3 and topic_count[ptopic] < 2:
                diverse.append(c)
                type_count[ct] += 1
                topic_count[ptopic] += 1
            else:
                overflow.append(c)
            if len(diverse) >= CANDIDATE_K:
                break

        if len(diverse) < CANDIDATE_K:
            diverse.extend(overflow[:CANDIDATE_K - len(diverse)])

        return diverse

    # ── GROQ LLM RE-RANKING ───────────────────────────────────────────────────

    def _llm_reasoning(
        self, user_ctx: Dict, candidates: List[Dict],
        gap_topics: List[str], next_topics: List[str],
    ) -> Dict:
        """
        Sends candidates to Groq for final re-ranking with full profile context.
        The prompt includes: skill level, languages, topics, gaps, error patterns,
        time spent, accuracy rate — so explanations are genuinely personalised.
        """
        cids        = [c["content_id"] for c in candidates]
        contents    = self.db.query(Content).filter(Content.id.in_(cids)).all()
        content_map = {c.id: c for c in contents}

        summaries = []
        for c in candidates:
            cobj = content_map.get(c["content_id"])
            if not cobj: continue
            summaries.append({
                "id":            c["content_id"],
                "title":         cobj.title,
                "type":          cobj.content_type.value,
                "difficulty":    cobj.difficulty.value,
                "language":      cobj.language or "general",
                "topics":        cobj.topics,
                "skills_gained": cobj.skills_gained,
                "duration_mins": cobj.duration_mins,
                "has_url":       bool(cobj.url),
                "blended_score": c["blended_score"],
                "cf_score":      c["cf_score"],
                "cbf_score":     c["cbf_score"],
                "is_expansion":  c.get("is_expansion", False),
            })

        # Build time-spent summary for the prompt
        time_summary = ", ".join(
            f"{t}: {int(m)}min" for t, m in
            sorted(user_ctx["time_per_topic"].items(), key=lambda x: -x[1])[:5]
        ) or "no history yet"

        system_prompt = f"""You are a personalized video recommendation assistant inside aiTA.

User Profile:
- Skill Level: {user_ctx['skill_level']}
- Preferred Language: {', '.join(user_ctx['preferred_languages']) or 'not specified'}
- Interested Topics: {', '.join(user_ctx['interested_topics']) or 'not set'}
- Learning Goals: {', '.join(user_ctx.get('learning_goals', [])) or 'not specified'}
- Weak Areas: {', '.join(user_ctx['weak_areas']) or 'none'}
- Recommended Next Topics: {', '.join(next_topics) or 'continue current topics'}

Additional context:
- Knowledge gaps (low accuracy): {', '.join(gap_topics) or 'none detected'}
- Error patterns: {', '.join(user_ctx['error_patterns'][:3]) or 'none'}
- Accuracy rate: {user_ctx['accuracy_rate']:.0%}
- Time spent per topic: {time_summary}

Task:
Recommend {TOP_N} videos (5–8) tailored to this user from the candidates below.

Guidelines:
- Match difficulty to skill level ({user_ctx['skill_level']})
- Prioritize interested_topics and learning_goals
- Focus on weak_areas and recommended_next for improvement
- Prefer videos in the user's preferred language
- Prefer items with has_url: true (real video links)
- Diversify content types when possible
- Expansion items (is_expansion: true) rank lower unless gaps are exhausted

For each recommended item provide:
- title (from candidate)
- description: 1–2 line description of what the video covers
- difficulty: the difficulty level
- why_relevant: why it's relevant to this specific user (reference their topics, gaps, goals)

Respond ONLY with valid JSON — no markdown, no extra text:
{{"summary": "one sentence personalized learning strategy", "ranked": [{{"id": <int>, "title": "...", "description": "1-2 lines", "difficulty": "...", "why_relevant": "1-2 sentences referencing user profile"}}]}}"""

        user_prompt = f"Candidates:\n{json.dumps(summaries, indent=2)}\n\nReturn ONLY valid JSON."

        models_to_try = [GROQ_MODEL_PRIMARY, GROQ_MODEL_FALLBACK]
        last_exc: Exception = Exception("No models tried")

        for model in models_to_try:
            try:
                resp = httpx.post(
                    GROQ_API_URL,
                    headers={"Authorization": f"Bearer {self.groq_api_key}",
                             "Content-Type": "application/json"},
                    json={"model": model, "max_tokens": 2000, "temperature": 0.3,
                          "messages": [{"role": "system", "content": system_prompt},
                                       {"role": "user", "content": user_prompt}]},
                    timeout=60.0,
                )
                resp.raise_for_status()
                data     = resp.json()
                raw      = data["choices"][0]["message"]["content"]
                tokens   = data.get("usage", {}).get("total_tokens", 0)
                clean    = raw.strip()
                if clean.startswith("```"):
                    clean = clean.split("```")[1]
                    if clean.startswith("json"): clean = clean[4:]
                parsed = json.loads(clean.strip())
                return {
                    "ranked_ids":   [item["id"] for item in parsed.get("ranked", [])],
                    "explanations": {
                        str(item["id"]): (
                            f"{item.get('description', '')} {item.get('why_relevant', item.get('explanation', ''))}"
                        ).strip()
                        for item in parsed.get("ranked", [])
                    },
                    "descriptions": {
                        str(item["id"]): item.get("description", "")
                        for item in parsed.get("ranked", [])
                    },
                    "difficulties": {
                        str(item["id"]): item.get("difficulty", "")
                        for item in parsed.get("ranked", [])
                    },
                    "summary":      parsed.get("summary", ""),
                    "tokens_used":  tokens,
                    "model_used":   model,
                }
            except (httpx.HTTPStatusError, httpx.TimeoutException) as exc:
                last_exc = exc; continue
            except (httpx.HTTPError, json.JSONDecodeError, KeyError) as exc:
                last_exc = exc; break

        # ── Fallback: score-based ranking, surface the LLM error ─────────────
        fallback_ids = [c["content_id"] for c in candidates[:TOP_N]]
        return {
            "ranked_ids":   fallback_ids,
            "explanations": {str(cid): "" for cid in fallback_ids},
            "summary":      f"❌ LLM unavailable: {last_exc}",
            "tokens_used":  0,
            "model_used":   "fallback",
        }


