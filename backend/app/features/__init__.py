"""Importing every model module here keeps SQLAlchemy's mapper registry complete.

Without it, an entry point that imports only one model (a script, a worker) fails at
mapper configuration time on relationships that name a class it never loaded.
"""

from app.core import llm_call  # noqa: F401
from app.features.accounts import models as accounts_models  # noqa: F401
from app.features.chat import models as chat_models  # noqa: F401
from app.features.feedback import models as feedback_models  # noqa: F401
from app.features.gamification import models as gamification_models  # noqa: F401
from app.features.grading import models as grading_models  # noqa: F401
from app.features.hints import models as hints_models  # noqa: F401
from app.features.learner_model import models as learner_model_models  # noqa: F401
from app.features.onboarding import models as onboarding_models  # noqa: F401
from app.features.practice import models as practice_models  # noqa: F401
from app.features.problems import models as problems_models  # noqa: F401
