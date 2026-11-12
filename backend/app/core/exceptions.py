from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class PetError(Exception):
    status_code = 500

    def __init__(self, detail: str):
        super().__init__(detail)
        self.detail = detail


class SubmissionNotFound(PetError):
    status_code = 404


class ProblemNotFound(PetError):
    status_code = 404


class ThreadNotFound(PetError):
    """A chat thread that does not exist or is not this user's: one answer for both,
    so thread ids cannot be probed."""

    status_code = 404


class SessionNotFound(PetError):
    status_code = 404


class TurnInProgress(PetError):
    status_code = 409


class OnboardingConflict(PetError):
    status_code = 409


class InvalidAnswer(PetError):
    status_code = 422


class ExecutorUnavailable(PetError):
    status_code = 503


class LLMUnavailable(PetError):
    status_code = 503


class ModelKeyError(PetError):
    """The student's own key or model failed. Never an LLMUnavailable, so no caller
    degrades it into a template: the student must see why."""

    status_code = 424

    def __init__(self, code: str, detail: str, provider_message: str = ""):
        super().__init__(detail)
        self.code = code
        self.provider_message = provider_message


class ModelChoiceRejected(PetError):
    status_code = 422


class LanguageNotExecutable(PetError):
    status_code = 422


class LanguageCheckRequired(PetError):
    status_code = 428


class UnverifiableSubmission(PetError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(PetError)
    def handle(_: Request, exc: PetError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})

    @app.exception_handler(ModelKeyError)
    def handle_model_key(_: Request, exc: ModelKeyError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={
            "detail": exc.detail, "code": exc.code, "provider_message": exc.provider_message})
