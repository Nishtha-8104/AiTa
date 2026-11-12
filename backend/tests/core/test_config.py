from app.core.config import settings


def test_execution_defaults():
    assert settings.EXECUTION_PROVIDER == "sidecar"
    assert settings.EXEC_WALL_SECONDS == 2.0
    assert settings.EXEC_MEMORY_MB == 256
    assert settings.EXEC_OUTPUT_KB == 64


def test_generation_defaults():
    assert settings.TEST_CASES_MIN == 3
    assert settings.TEST_CASES_TARGET == 8
    assert settings.REFERENCE_MAX_ATTEMPTS == 3


def test_repr_hides_secrets(monkeypatch):
    secret_fields = [name for name, field in type(settings).model_fields.items()
                     if field.annotation is str and (
                         any(word in name for word in ("KEY", "SECRET", "PASSWORD", "TOKEN"))
                         or name in ("DATABASE_URL", "REDIS_URL"))]
    for name in secret_fields:
        monkeypatch.setattr(settings, name, f"leak-{name}")

    text = repr(settings)

    assert "NVIDIA_MODEL" in text
    assert "leak-" not in text


def test_llm_defaults():
    assert settings.LLM_MAX_OUTPUT_TOKENS == 8192
    assert settings.NVIDIA_MODEL
    assert settings.NVIDIA_CODEGEN_MODEL
