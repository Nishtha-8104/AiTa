"""Chat agent context and prompt; no LLM anywhere."""

from app.features.chat.agent import context
from app.features.chat.agent.prompts import system_prompt
from app.features.grading.models import CodeEvaluation, CodeSubmission, Language
from app.features.problems.models import Problem, ProblemSource
from tests.features.chat.agent.conftest import new_thread


def test_system_prompt_carries_the_last_attempt_only_when_there_is_one(db, student):
    thread = new_thread(db, student)
    fresh = system_prompt("pet", context.load(db, student.id, thread))
    assert "Last attempt: none yet" in fresh
    assert "No graded practice yet." in fresh and "Write code in C unless" in fresh
    assert "Tele-MANAS (free, 24x7): 14416, or 112" in fresh
    for rule in ("answer from the Reference passages",
                 "ALWAYS pass it as problem_text", "ALWAYS call evaluate_code before judging",
                 "ALWAYS call get_hint", "NEVER write a citation marker",
                 "no hint or approach has been given for that problem yet",
                 '"for loop C me kaise likhte hai?"', "the result is shown to the student as is",
                 "Never explain the cause", "shown to the student exactly as returned"):
        assert rule in fresh

    problem = Problem(source=ProblemSource.DSA, statement="Largest of N numbers\nRead N...",
                      statement_hash="p" * 64, topic="arrays")
    db.add(problem)
    db.flush()
    submission = CodeSubmission(user_id=student.id, language=Language.C, code="int main(){}",
                                problem_id=problem.id, title="int main(){}")
    db.add(submission)
    db.flush()
    db.add(CodeEvaluation(submission_id=submission.id, user_id=student.id,
                          verification_status="verified", tests_total=4, tests_passed=3))
    thread.summary = "They were tracing a loop over an array."
    db.commit()

    prompt = system_prompt("pet", context.load(db, student.id, thread, language="python"))
    assert (f'"Largest of N numbers" (problem_id {problem.id}), Failed some tests, '
            "3/4 tests passed") in prompt
    assert "may or may not be what they are asking about" in prompt
    assert "Earlier in this conversation: They were tracing a loop" in prompt
    assert "Write code in Python unless" in prompt
