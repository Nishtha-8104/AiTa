from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import httpx, re

from app.agents.code_eval_agent import CodeEvaluationAgent
from app.models.code_eval import CodeSubmission, EvalStatus
from app.schemas.code_eval import SubmitCodeRequest
from app.core.config import settings


def _generate_title(language: str, code: str) -> str:
    """
    Ask Groq to produce a concise, meaningful title for this code snippet.
    Falls back to heuristics if Groq is unavailable.
    """
    # ── Heuristic fallback ────────────────────────────────────────────────────
    def heuristic():
        lines = [l.strip() for l in code.splitlines() if l.strip()]

        # Python: first def / class
        for line in lines:
            m = re.match(r'def\s+(\w+)\s*\(', line)
            if m: return f"{m.group(1).replace('_',' ').title()} ({language.capitalize()})"
            m = re.match(r'class\s+(\w+)', line)
            if m: return f"{m.group(1)} class ({language.capitalize()})"

        # JS/TS/Java/Go: function name
        for line in lines:
            m = re.match(r'(?:function|func|public\s+\w+\s+)(\w+)\s*\(', line)
            if m: return f"{m.group(1).replace('_',' ').title()} ({language.capitalize()})"
            m = re.match(r'(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s*)?\(', line)
            if m: return f"{m.group(1).replace('_',' ').title()} ({language.capitalize()})"

        # First non-comment line
        for line in lines:
            if not line.startswith(('#', '//', '/*', '*', '--')):
                return line[:50] + ('…' if len(line) > 50 else '')

        return f"{language.capitalize()} Submission"

    try:
        resp = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}",
                     "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "max_tokens": 30,
                "temperature": 0.2,
                "messages": [
                    {"role": "system",
                     "content": "You are a code title generator. Given a code snippet, reply with ONLY a concise 3-8 word title describing what the code does. No punctuation, no quotes, no explanation."},
                    {"role": "user",
                     "content": f"Language: {language}\n\n{code[:800]}"}
                ],
            },
            timeout=10.0,
        )
        resp.raise_for_status()
        title = resp.json()["choices"][0]["message"]["content"].strip().strip('"\'')
        return title[:100] if title else heuristic()
    except Exception:
        return heuristic()


class CodeEvalService:

    @staticmethod
    def submit(db: Session, user_id: int, req: SubmitCodeRequest) -> CodeSubmission:
        # Generate a meaningful title if none provided
        title = req.title or _generate_title(req.language.value, req.code)

        submission = CodeSubmission(
            user_id         = user_id,
            language        = req.language,
            code            = req.code,
            title           = title,
            problem_context = req.problem_context,
            expected_output = req.expected_output,
            status          = EvalStatus.PENDING,
        )
        db.add(submission)
        db.commit()
        db.refresh(submission)
        return submission

    @staticmethod
    def evaluate(db: Session, submission_id: int, user_id: int):
        agent = CodeEvaluationAgent(db)
        try:
            return agent.evaluate(submission_id, user_id)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        except RuntimeError as e:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e))

    @staticmethod
    def get_submissions(db: Session, user_id: int):
        agent = CodeEvaluationAgent(db)
        return agent.get_submissions(user_id)

    @staticmethod
    def get_submission(db: Session, submission_id: int, user_id: int):
        agent = CodeEvaluationAgent(db)
        try:
            return agent.get_submission(submission_id, user_id)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    @staticmethod
    def get_stats(db: Session, user_id: int):
        agent = CodeEvaluationAgent(db)
        return agent.get_user_stats(user_id)

    @staticmethod
    def delete_submission(db: Session, submission_id: int, user_id: int):
        sub = db.query(CodeSubmission).filter(
            CodeSubmission.id      == submission_id,
            CodeSubmission.user_id == user_id,
        ).first()
        if sub:
            db.delete(sub)
            db.commit()