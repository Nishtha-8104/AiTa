from pydantic import BaseModel, Field, model_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from app.models.code_eval import Language, EvalStatus, SeverityLevel


# ─── Issue ───────────────────────────────────────────────────────────────────

class IssueSchema(BaseModel):
    id:         int
    line:       Optional[int] = None
    severity:   SeverityLevel
    category:   str
    message:    str
    suggestion: str


# ─── Submission schemas ───────────────────────────────────────────────────────

class SubmitCodeRequest(BaseModel):
    language:        Language
    code:            str  = Field(..., min_length=1, max_length=50000)
    title:           Optional[str] = Field(None, max_length=300)
    problem_context: Optional[str] = Field(None, max_length=5000)
    expected_output: Optional[str] = Field(None, max_length=2000)


class SubmissionSummary(BaseModel):
    id:          int
    title:       Optional[str]
    language:    Language
    status:      EvalStatus
    eval_count:  int
    created_at:  datetime
    updated_at:  Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── Score breakdown ──────────────────────────────────────────────────────────

class ScoreBreakdown(BaseModel):
    overall:       float = 0.0
    correctness:   float = 0.0
    quality:       float = 0.0
    efficiency:    float = 0.0
    security:      float = 0.0
    style:         float = 0.0
    documentation: float = 0.0


class ComplexityMetrics(BaseModel):
    time_complexity:       Optional[str]  = None
    space_complexity:      Optional[str]  = None
    cyclomatic_complexity: Optional[int]  = None
    lines_of_code:         Optional[int]  = None
    comment_ratio:         Optional[float]= None


# ─── Evaluation result ────────────────────────────────────────────────────────

class EvaluationResult(BaseModel):
    id:                  int
    submission_id:       int
    scores:              ScoreBreakdown        = ScoreBreakdown()
    complexity:          ComplexityMetrics      = ComplexityMetrics()
    issues:              List[IssueSchema]      = []
    summary:             Optional[str]          = None
    detailed_feedback:   Optional[str]          = None
    corrected_code:      Optional[str]          = None
    key_improvements:    List[str]              = []
    learning_points:     List[str]              = []
    best_practices_used: List[str]              = []
    anti_patterns:       List[str]              = []
    suggested_resources: List[str]              = []
    agent_steps:         List[str]              = []
    tokens_used:         int                    = 0
    latency_ms:          int                    = 0
    model_used:          Optional[str]          = None
    created_at:          datetime

    @model_validator(mode='before')
    @classmethod
    def build_nested(cls, data: Any) -> Any:
        """
        SQLAlchemy ORM objects have flat columns (overall_score, correctness_score …).
        This validator assembles the nested ScoreBreakdown and ComplexityMetrics
        objects so the response serialises correctly.
        """
        # Works for both ORM objects (getattr) and plain dicts
        def get(key, default=None):
            if isinstance(data, dict):
                return data.get(key, default)
            return getattr(data, key, default)

        # ── Build scores if not already a dict/object ─────────────────────
        if not isinstance(get('scores'), (dict, ScoreBreakdown)):
            scores = {
                'overall':       get('overall_score',       0.0),
                'correctness':   get('correctness_score',   0.0),
                'quality':       get('quality_score',       0.0),
                'efficiency':    get('efficiency_score',    0.0),
                'security':      get('security_score',      0.0),
                'style':         get('style_score',         0.0),
                'documentation': get('documentation_score', 0.0),
            }
            if isinstance(data, dict):
                data['scores'] = scores
            else:
                # ORM object → convert to dict so Pydantic can work with it
                data = {
                    'id':                  get('id'),
                    'submission_id':       get('submission_id'),
                    'scores':              scores,
                    'complexity': {
                        'time_complexity':       get('time_complexity'),
                        'space_complexity':      get('space_complexity'),
                        'cyclomatic_complexity': get('cyclomatic_complexity'),
                        'lines_of_code':         get('lines_of_code'),
                        'comment_ratio':         get('comment_ratio'),
                    },
                    'issues':              get('issues',              []),
                    'summary':             get('summary'),
                    'detailed_feedback':   get('detailed_feedback'),
                    'corrected_code':      get('corrected_code'),
                    'key_improvements':    get('key_improvements',    []),
                    'learning_points':     get('learning_points',     []),
                    'best_practices_used': get('best_practices_used', []),
                    'anti_patterns':       get('anti_patterns',       []),
                    'suggested_resources': get('suggested_resources', []),
                    'agent_steps':         get('agent_steps',         []),
                    'tokens_used':         get('tokens_used',         0),
                    'latency_ms':          get('latency_ms',          0),
                    'model_used':          get('model_used'),
                    'created_at':          get('created_at'),
                }

        # ── Build complexity if not already a dict/object ─────────────────
        if isinstance(data, dict) and not isinstance(data.get('complexity'), (dict, ComplexityMetrics)):
            data['complexity'] = {
                'time_complexity':       get('time_complexity'),
                'space_complexity':      get('space_complexity'),
                'cyclomatic_complexity': get('cyclomatic_complexity'),
                'lines_of_code':         get('lines_of_code'),
                'comment_ratio':         get('comment_ratio'),
            }

        return data

    class Config:
        from_attributes = True
        protected_namespaces = ()


class SubmissionDetail(SubmissionSummary):
    code:            str
    problem_context: Optional[str] = None
    expected_output: Optional[str] = None
    evaluations:     List[EvaluationResult] = []

    class Config:
        from_attributes = True


# ─── History ─────────────────────────────────────────────────────────────────

class HistoryPoint(BaseModel):
    eval_number:   int
    overall_score: float
    language:      Language
    submission_id: int
    evaluation_id: int
    created_at:    datetime

    class Config:
        from_attributes = True


class UserEvalStats(BaseModel):
    total_submissions:  int
    total_evaluations:  int
    avg_overall_score:  float
    best_score:         float
    languages_used:     List[str]
    most_common_issues: List[str]
    improvement_trend:  float
    recent_history:     List[HistoryPoint]