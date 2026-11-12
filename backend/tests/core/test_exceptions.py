import pytest

from app.core.exceptions import (
    ExecutorUnavailable,
    LLMUnavailable,
    PetError,
    ProblemNotFound,
    SubmissionNotFound,
    UnverifiableSubmission,
)


def test_all_domain_errors_share_a_base():
    for cls in (SubmissionNotFound, ProblemNotFound, ExecutorUnavailable,
                LLMUnavailable, UnverifiableSubmission):
        assert issubclass(cls, PetError)


def test_status_codes():
    assert SubmissionNotFound("x").status_code == 404
    assert ProblemNotFound("x").status_code == 404
    assert ExecutorUnavailable("x").status_code == 503
    assert LLMUnavailable("x").status_code == 503


def test_detail_is_the_message():
    assert SubmissionNotFound("no such submission").detail == "no such submission"


def test_unverifiable_carries_a_reason():
    err = UnverifiableSubmission("reference_unvalidated")
    assert err.reason == "reference_unvalidated"


def test_domain_errors_are_not_builtins():
    assert not issubclass(PetError, (ValueError, RuntimeError))
    with pytest.raises(PetError):
        raise SubmissionNotFound("boom")
