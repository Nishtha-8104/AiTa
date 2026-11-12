from app.features.feedback.models import FeedbackTone

TONE_INSTRUCTIONS = {
    FeedbackTone.ENCOURAGING:
        "Be warm and encouraging — praise effort before mentioning problems.",
    FeedbackTone.CONSTRUCTIVE:
        "Be direct and specific — focus on actionable improvement over praise.",
    FeedbackTone.CHALLENGING:
        "Be Socratic — ask why, push deeper understanding, challenge assumptions.",
}

SYSTEM_PROMPT = """You are the Feedback Agent in PET — an AI teaching assistant for \
Indian programming students.
You synthesise the student's latest code evaluation and recent learning activity \
(MCQs, debug challenges, coding problems) into rich, personalised feedback.

Student: {username} | Skill: {skill}
Languages: {languages}
Learner preferences: {style}
Known weak areas: {weak_areas}
Tone: {tone_instruction}

Rules:
- NEVER say "wrong" without explaining WHY it matters for learning
- Adapt language to {skill} level — no jargon for beginners
- Ground every point in the findings below; do not invent work the student did not do
- If a failing test is given, quote its input in the summary and ask what the code does
  with it
- If a misconception has come up more than once, say so with the count, e.g. "this is
  the 3rd time wrong_initial_value has shown up in your recent attempts"
- NEVER state the fix, NEVER write corrected code or a working solution, and never
  write a code block or lines of code; refer to the student's own code in words or a
  short inline fragment
"""

LEARNING_BLOCK = """LEARNER MODEL (measured, not estimated):
Topic: {topic} | Mastery: {mastery} from {evidence} graded attempts
First failing test: {failing}
Per-test results: {statuses}
Misconceptions tagged on this attempt: {this_attempt}
Misconception counts over the last 30 attempts: {counts}
Highest hint level used on this problem since the last pass: {hint_level}
Last 5 attempts: {recent}"""

EVAL_BLOCK = """CODE EVALUATION:
Score: {overall}/100 | Correct: {correctness} | Complexity: {complexity} | \
Efficiency: {efficiency}
Issues: {issues}
Learning points: {learning_points}
Anti-patterns: {anti_patterns}
Agent summary: {summary}"""

ACTIVITY_BLOCK = """RECENT LEARNING ACTIVITY (last {count} graded items, oldest first):
Items: {items}
Topic mastery changes: {topics}
Hints used by level: {hints}
Most repeated mistakes: {mistakes}"""

PATTERN_BLOCK = """PATTERN ANALYSIS:
Error patterns: {errors}
Weak concepts: {weak_concepts}
Strengths: {strengths}"""

PATTERN_ONLY_HEADLINE = (
    "Detailed feedback could not be generated right now — this is what the "
    "automatic analysis alone found"
)

PATTERN_ONLY_MOTIVATIONAL = "Every bug fixed is a lesson learned — keep going!"
