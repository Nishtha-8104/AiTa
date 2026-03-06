from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status
from typing import List, Optional
import uuid

from app.models.recommendation import (
    Content, UserContentInteraction, Recommendation,
    AgentRunLog, InteractionType
)
from app.models.user import User
from app.schemas.recommendation import (
    LogInteractionRequest, CreateContentRequest, RecommendationResponse, RecommendationItem
)
from app.agents.recommendation_agent import ContentRecommendationAgent


class RecommendationService:

    # ─── Run the AI Agent ────────────────────────────────────────────────────

    @staticmethod
    def run_agent(db: Session, user_id: int) -> dict:
        """Invoke the Content Recommendation Agent for a given user."""
        agent = ContentRecommendationAgent(db)
        result = agent.run(user_id)
        return result

    # ─── Fetch stored recommendations ────────────────────────────────────────

    @staticmethod
    def get_recommendations(db: Session, user_id: int) -> List[Recommendation]:
        return (
            db.query(Recommendation)
            .options(joinedload(Recommendation.content))
            .filter(
                Recommendation.user_id == user_id,
                Recommendation.is_dismissed == False,
            )
            .order_by(Recommendation.rank.asc())
            .all()
        )

    @staticmethod
    def get_latest_run_log(db: Session, user_id: int) -> Optional[AgentRunLog]:
        return (
            db.query(AgentRunLog)
            .filter(AgentRunLog.user_id == user_id)
            .order_by(AgentRunLog.created_at.desc())
            .first()
        )

    # ─── Log a user interaction ───────────────────────────────────────────────

    @staticmethod
    def log_interaction(db: Session, user_id: int, req: LogInteractionRequest) -> dict:
        """
        Upsert an interaction row. Compute implicit score from time + completion.
        Also mark the recommendation as clicked if it exists.
        """
        content = db.query(Content).filter(Content.id == req.content_id).first()
        if not content:
            raise HTTPException(status_code=404, detail="Content not found.")

        existing = db.query(UserContentInteraction).filter(
            UserContentInteraction.user_id == user_id,
            UserContentInteraction.content_id == req.content_id,
        ).first()

        # Compute implicit score (0.0 – 1.0)
        time_score       = min((req.time_spent_mins or 0) / max(content.duration_mins or 10, 1), 1.0)
        completion_score = (req.completion_pct or 0) / 100.0
        implicit         = round((time_score * 0.4 + completion_score * 0.6), 4)

        if existing:
            existing.interaction     = req.interaction
            existing.implicit_score  = max(existing.implicit_score, implicit)
            if req.rating is not None:
                existing.rating = req.rating
            if req.time_spent_mins:
                existing.time_spent_mins = req.time_spent_mins
            if req.completion_pct is not None:
                existing.completion_pct = req.completion_pct
                existing.is_completed   = req.completion_pct >= 90
        else:
            existing = UserContentInteraction(
                user_id        = user_id,
                content_id     = req.content_id,
                interaction    = req.interaction,
                rating         = req.rating,
                implicit_score = implicit,
                time_spent_mins= req.time_spent_mins or 0,
                completion_pct = req.completion_pct or 0,
                is_completed   = (req.completion_pct or 0) >= 90,
                is_bookmarked  = req.interaction == InteractionType.BOOKMARK,
            )
            db.add(existing)

        # Mark recommendation as clicked
        if req.interaction in (InteractionType.VIEW, InteractionType.COMPLETE):
            rec = db.query(Recommendation).filter(
                Recommendation.user_id == user_id,
                Recommendation.content_id == req.content_id,
            ).first()
            if rec:
                rec.is_clicked = True

        db.commit()
        return {"success": True, "message": "Interaction logged.", "implicit_score": implicit}

    @staticmethod
    def dismiss_recommendation(db: Session, user_id: int, rec_id: int):
        rec = db.query(Recommendation).filter(
            Recommendation.id == rec_id,
            Recommendation.user_id == user_id,
        ).first()
        if not rec:
            raise HTTPException(status_code=404, detail="Recommendation not found.")
        rec.is_dismissed = True
        db.commit()

    # ─── Content catalog management ───────────────────────────────────────────

    @staticmethod
    def seed_content(db: Session, req: CreateContentRequest) -> Content:
        c = Content(**req.model_dump())
        db.add(c)
        db.commit()
        db.refresh(c)
        return c

    @staticmethod
    def list_content(db: Session, skip=0, limit=50) -> List[Content]:
        return db.query(Content).filter(Content.is_active == True).offset(skip).limit(limit).all()

    @staticmethod
    def bulk_seed_content(db: Session) -> int:
        """Seed a starter content catalog if DB is empty."""
        existing = db.query(Content).count()
        if existing > 0:
            return existing

        sample_content = [
            # Python basics
            {"title": "Python for Beginners – Complete Tutorial", "content_type": "video", "difficulty": "beginner", "language": "Python", "topics": ["variables", "loops", "functions", "conditionals"], "skills_gained": ["Python basics", "problem solving"], "duration_mins": 120, "source": "YouTube", "description": "Full beginner Python course covering fundamentals.", "avg_rating": 4.7},
            {"title": "Python Lists, Dicts & Sets – Deep Dive", "content_type": "article", "difficulty": "beginner", "language": "Python", "topics": ["lists", "dictionaries", "sets", "data structures"], "skills_gained": ["data structures", "Python"], "duration_mins": 25, "source": "GeeksForGeeks", "description": "Comprehensive guide to Python's built-in data structures.", "avg_rating": 4.5},
            {"title": "Recursion Problems – 10 Practice Exercises", "content_type": "exercise", "difficulty": "intermediate", "language": "Python", "topics": ["recursion", "functions", "problem solving"], "skills_gained": ["recursion", "algorithmic thinking"], "duration_mins": 60, "source": "HackerRank", "description": "Practice recursion with 10 graded exercises.", "avg_rating": 4.6},
            # OOP
            {"title": "Object-Oriented Programming in Python", "content_type": "tutorial", "difficulty": "intermediate", "language": "Python", "topics": ["OOP", "classes", "inheritance", "polymorphism"], "skills_gained": ["OOP", "software design"], "duration_mins": 90, "source": "Real Python", "description": "Master OOP concepts with hands-on Python examples.", "avg_rating": 4.8},
            {"title": "Design Patterns in Python – Gang of Four", "content_type": "article", "difficulty": "advanced", "language": "Python", "topics": ["design patterns", "OOP", "software architecture"], "skills_gained": ["software design", "architecture"], "duration_mins": 45, "source": "Refactoring.Guru", "description": "Implement classic design patterns in Python.", "avg_rating": 4.6},
            # Algorithms & DS
            {"title": "Data Structures & Algorithms – Full Course", "content_type": "video", "difficulty": "intermediate", "language": "Python", "topics": ["arrays", "linked lists", "trees", "graphs", "sorting"], "skills_gained": ["DSA", "competitive programming"], "duration_mins": 180, "source": "freeCodeCamp", "description": "Complete DSA course with Python implementations.", "avg_rating": 4.9},
            {"title": "Binary Search – Variants & Tricks", "content_type": "exercise", "difficulty": "intermediate", "language": "Python", "topics": ["binary search", "arrays", "algorithms"], "skills_gained": ["search algorithms", "problem solving"], "duration_mins": 40, "source": "LeetCode", "description": "12 binary search problems from easy to hard.", "avg_rating": 4.7},
            {"title": "Graph Algorithms: BFS, DFS, Dijkstra", "content_type": "tutorial", "difficulty": "advanced", "language": "Python", "topics": ["graphs", "BFS", "DFS", "shortest path"], "skills_gained": ["graph algorithms", "competitive programming"], "duration_mins": 120, "source": "CP-Algorithms", "description": "Complete guide to graph traversal and shortest path algorithms.", "avg_rating": 4.8},
            # Java
            {"title": "Java Fundamentals for Beginners", "content_type": "video", "difficulty": "beginner", "language": "Java", "topics": ["variables", "loops", "functions", "OOP basics"], "skills_gained": ["Java", "programming fundamentals"], "duration_mins": 150, "source": "Udemy", "description": "Start Java from zero — syntax, OOP, exceptions.", "avg_rating": 4.6},
            {"title": "Java Collections Framework Explained", "content_type": "article", "difficulty": "intermediate", "language": "Java", "topics": ["collections", "ArrayList", "HashMap", "generics"], "skills_gained": ["Java", "data structures"], "duration_mins": 35, "source": "Baeldung", "description": "In-depth guide to Java's Collections API.", "avg_rating": 4.5},
            # JavaScript & Web
            {"title": "JavaScript ES6+ – Modern Features", "content_type": "tutorial", "difficulty": "intermediate", "language": "JavaScript", "topics": ["arrow functions", "promises", "async/await", "destructuring"], "skills_gained": ["JavaScript", "Web Development"], "duration_mins": 75, "source": "javascript.info", "description": "Master modern JS features used in every web project.", "avg_rating": 4.8},
            {"title": "React.js – Build Your First App", "content_type": "project", "difficulty": "intermediate", "language": "JavaScript", "topics": ["React", "components", "state", "hooks"], "skills_gained": ["Web Development", "React", "frontend"], "duration_mins": 180, "source": "Scrimba", "description": "Build a full Todo app with React hooks and state management.", "avg_rating": 4.7},
            # ML & AI
            {"title": "Machine Learning with scikit-learn", "content_type": "tutorial", "difficulty": "intermediate", "language": "Python", "topics": ["machine learning", "classification", "regression", "scikit-learn"], "skills_gained": ["Machine Learning", "Data Science"], "duration_mins": 120, "source": "Kaggle", "description": "Hands-on ML tutorial with real datasets.", "avg_rating": 4.8},
            {"title": "Neural Networks from Scratch in Python", "content_type": "video", "difficulty": "advanced", "language": "Python", "topics": ["neural networks", "backpropagation", "deep learning", "numpy"], "skills_gained": ["Deep Learning", "AI/ML"], "duration_mins": 200, "source": "YouTube", "description": "Build a neural net from scratch using only NumPy.", "avg_rating": 4.9},
            {"title": "Pandas for Data Analysis – Beginner Guide", "content_type": "tutorial", "difficulty": "beginner", "language": "Python", "topics": ["pandas", "data analysis", "dataframes", "CSV"], "skills_gained": ["Data Science", "data analysis"], "duration_mins": 60, "source": "Towards Data Science", "description": "Learn Pandas from scratch with real datasets.", "avg_rating": 4.6},
            # C++
            {"title": "C++ STL – Containers and Algorithms", "content_type": "article", "difficulty": "intermediate", "language": "C++", "topics": ["STL", "vectors", "maps", "algorithms"], "skills_gained": ["C++", "competitive programming"], "duration_mins": 40, "source": "cppreference.com", "description": "Master C++ Standard Template Library.", "avg_rating": 4.7},
            {"title": "Competitive Programming with C++ – CSES Problems", "content_type": "exercise", "difficulty": "advanced", "language": "C++", "topics": ["competitive programming", "dynamic programming", "graphs"], "skills_gained": ["competitive programming", "problem solving"], "duration_mins": 300, "source": "CSES", "description": "Solve 50 classic competitive programming problems.", "avg_rating": 4.9},
            # Database
            {"title": "SQL Fundamentals – Complete Beginner Course", "content_type": "tutorial", "difficulty": "beginner", "language": "SQL", "topics": ["SQL", "databases", "queries", "joins"], "skills_gained": ["databases", "SQL", "backend"], "duration_mins": 90, "source": "Mode Analytics", "description": "Learn SQL from SELECT to complex JOIN queries.", "avg_rating": 4.7},
            # System Design
            {"title": "System Design Interview – Key Concepts", "content_type": "article", "difficulty": "advanced", "language": "general", "topics": ["system design", "scalability", "microservices", "caching"], "skills_gained": ["System Design", "software architecture"], "duration_mins": 60, "source": "Grokking System Design", "description": "Core concepts for system design interviews at top companies.", "avg_rating": 4.8},
            # Git & Dev tools
            {"title": "Git & GitHub for Beginners", "content_type": "video", "difficulty": "beginner", "language": "general", "topics": ["git", "version control", "GitHub", "collaboration"], "skills_gained": ["version control", "collaboration"], "duration_mins": 60, "source": "freeCodeCamp", "description": "Learn Git and GitHub from scratch.", "avg_rating": 4.6},
        ]

        for item in sample_content:
            c = Content(
                title         = item["title"],
                description   = item.get("description", ""),
                content_type  = item["content_type"],
                difficulty    = item["difficulty"],
                language      = item.get("language"),
                topics        = item.get("topics", []),
                skills_gained = item.get("skills_gained", []),
                source        = item.get("source"),
                avg_rating    = item.get("avg_rating", 0.0),
                duration_mins = item.get("duration_mins"),
                is_active     = True,
            )
            db.add(c)

        db.commit()
        return len(sample_content)