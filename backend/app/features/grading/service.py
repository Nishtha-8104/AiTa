"""Saves code submissions (with an auto-generated title) and runs the Evaluation Agent on
them for the router."""

import re

from sqlalchemy.orm import Session

from app.core.exceptions import SubmissionNotFound
from app.features.grading.agent.graph import evaluate_submission
from app.features.grading.agent.multi_test import display_statement
from app.features.grading.agent.schemas import EvalReport
from app.features.grading.models import CodeSubmission
from app.features.grading.schemas import SubmissionDetail, SubmitCodeRequest
from app.features.problems.logic.listing import is_curated
from app.features.problems.models import Problem


def _generate_title(language: str, code: str) -> str:
    """A concise title for the submission. Heuristic first, LLM only if it fails."""
    lines = [line.strip() for line in code.splitlines() if line.strip()]

    for line in lines:
        match = re.match(r"def\s+(\w+)\s*\(", line)
        if match:
            return f"{match.group(1).replace('_', ' ').title()} ({language.capitalize()})"
        match = re.match(r"class\s+(\w+)", line)
        if match:
            return f"{match.group(1)} class ({language.capitalize()})"

    for line in lines:
        match = re.match(r"(?:function|func|public\s+\w+\s+)(\w+)\s*\(", line)
        if match:
            return f"{match.group(1).replace('_', ' ').title()} ({language.capitalize()})"

    for line in lines:
        if not line.startswith(("#", "//", "/*", "*", "--")):
            return line[:50] + ("…" if len(line) > 50 else "")

    return f"{language.capitalize()} Submission"


class CodeEvalService:

    @staticmethod
    def submit(db: Session, user_id: int, req: SubmitCodeRequest) -> CodeSubmission:
        # A problem_id no longer implies the bank: Code Help sends the id of
        # whatever /problems/generate served, which is curated or generated. Only the
        # row itself can say which, so load it.
        problem = (
            db.query(Problem).filter(Problem.id == req.problem_id).first()
            if req.problem_id is not None else None
        )

        submission = CodeSubmission(
            user_id=user_id,
            language=req.language,
            code=req.code,
            title=req.title or _generate_title(req.language.value, req.code),
            problem_context=req.problem_context,
            expected_output=req.expected_output,
            problem_id=req.problem_id,
            from_bank=problem is not None and is_curated(problem),
        )
        db.add(submission)
        db.commit()
        db.refresh(submission)
        return submission

    @staticmethod
    def evaluate(db: Session, submission_id: int, user_id: int) -> EvalReport:
        return evaluate_submission(db, submission_id, user_id)

    @staticmethod
    def get_submissions(db: Session, user_id: int, limit: int = 20):
        return (
            db.query(CodeSubmission)
            .filter(CodeSubmission.user_id == user_id)
            .order_by(CodeSubmission.created_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_submission(db: Session, submission_id: int, user_id: int) -> SubmissionDetail:
        submission = (
            db.query(CodeSubmission)
            .filter(
                CodeSubmission.id == submission_id,
                CodeSubmission.user_id == user_id,
            )
            .first()
        )
        if submission is None:
            raise SubmissionNotFound(f"submission {submission_id} not found")

        statement = None
        if submission.problem_id:
            problem = db.query(Problem).filter(Problem.id == submission.problem_id).first()
            if problem is not None:
                statement = display_statement(problem.statement)

        detail = SubmissionDetail.model_validate(submission)
        detail.problem_statement = statement
        return detail

    @staticmethod
    def get_stats(db: Session, user_id: int):
        from app.features.grading.logic.code_eval_stats import user_stats
        return user_stats(db, user_id)

    @staticmethod
    def delete_submission(db: Session, submission_id: int, user_id: int) -> None:
        submission = (
            db.query(CodeSubmission)
            .filter(
                CodeSubmission.id == submission_id,
                CodeSubmission.user_id == user_id,
            )
            .first()
        )
        if submission is not None:
            db.delete(submission)
            db.commit()
