from pydantic import BaseModel

from app.core.config import settings
from app.core.exceptions import ModelChoiceRejected, ModelKeyError
from app.core.llm import structured
from app.core.llm_choice import Choice, has_server_model, server_choice
from app.core.llm_providers import PROVIDERS, build_client, classify, label, list_models
from app.features.model_settings.schemas import (
    CapabilityCheck, CheckOut, ChoiceIn, ModelSettingsOut, ProviderOut,
)

# Chat prompts carry book passages, code and history; below this they get cut off.
MIN_CONTEXT = 16_000
_NOT_THE_MODEL = ("invalid_key", "out_of_credit", "rate_limited", "provider_unreachable",
                  "model_not_found")
_ADD_TOOL = {"type": "function", "function": {
    "name": "add", "description": "Add two integers.",
    "parameters": {"type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
                   "required": ["a", "b"]}}}
_TOOL_PROMPT = "Use the add tool to add 2 and 3. Do not answer in text."
_SUM_PROMPT = "What is 2 + 3? Put the number in the answer field."


class _Sum(BaseModel):
    answer: int


def view(choice: Choice | None) -> ModelSettingsOut:
    providers = [ProviderOut(id=p.id, label=p.label, base_url=p.base_url, needs_key=p.needs_key,
                             local=p.local)
                 for p in PROVIDERS.values()]
    if choice is None and not has_server_model():
        provider, model, source, hint = "", "", "none", ""
    elif choice is None:
        default = server_choice()
        provider = default.provider if default else "nvidia"
        model = default.model if default else settings.NVIDIA_MODEL
        source, hint = "default", ""
    else:
        provider, model, hint = choice.provider, choice.model, choice.key_hint
        source = "local" if PROVIDERS[provider].local else "own"
    return ModelSettingsOut(source=source, provider=provider,
                            provider_label=label(provider) if provider else "",
                            model=model, key_hint=hint,
                            has_default=has_server_model(), providers=providers)


def resolve(data: ChoiceIn, existing: Choice | None) -> Choice:
    provider = PROVIDERS.get(data.provider)
    if provider is None:
        raise ModelChoiceRejected("Unknown provider.")
    base_url = provider.base_url
    if provider.local:
        base_url = data.base_url.strip() or provider.base_url
        if not base_url.startswith(("http://", "https://")):
            raise ModelChoiceRejected("Enter the server address, starting with http:// or https://.")
    key = data.api_key.strip()
    if not key and existing is not None and existing.provider == provider.id:
        key = existing.api_key
    if provider.needs_key and not key:
        raise ModelChoiceRejected(f"Enter your {provider.label} API key.")
    return Choice(provider.id, data.model.strip(), base_url.rstrip("/"), key)


def _probe(choice: Choice, name: str, run, passed: str, failed: str) -> CapabilityCheck:
    """A provider that refuses the feature (400) fails the check; a key, credit or
    network problem is not about the model, so it stops the test with its own error."""
    try:
        ok = run()
    except Exception as exc:
        error = exc if isinstance(exc, ModelKeyError) else classify(exc, choice)
        if error.code in _NOT_THE_MODEL:
            raise error from exc
        return CapabilityCheck(name=name, ok=False, detail=f"{failed} ({error.provider_message})")
    return CapabilityCheck(name=name, ok=ok, detail=passed if ok else failed)


def _context_check(context: int | None) -> CapabilityCheck:
    if context is None:
        return CapabilityCheck(name="Context window", ok=True,
                               detail="Not reported by the provider, so not checked.")
    if context < MIN_CONTEXT:
        return CapabilityCheck(name="Context window", ok=False,
                               detail=f"{context:,} tokens. PET needs at least {MIN_CONTEXT:,}.")
    return CapabilityCheck(name="Context window", ok=True, detail=f"{context:,} tokens.")


def check(choice: Choice) -> CheckOut:
    """Lists the account's models; with a model chosen, also proves the three things PET
    relies on: tool calls (the chatbot), structured replies (grading, hints, feedback) and
    enough context. Listing alone does not prove a key everywhere (OpenRouter's is public)."""
    try:
        listed = list_models(choice)
    except ModelKeyError as error:
        if not choice.model or error.code not in ("model_not_found", "provider_error"):
            raise
        listed = {}
    models = list(listed)
    if not choice.model:
        return CheckOut(ok=True, models=models)

    chat = build_client(choice, temperature=0.0, max_tokens=1024, timeout=60)
    try:
        chat.invoke("Reply with OK.")
    except ModelKeyError:
        raise
    except Exception as exc:
        raise classify(exc, choice) from exc

    checks = [
        CapabilityCheck(name="Connection", ok=True, detail="The model answered."),
        _probe(choice, "Tool calling",
               lambda: bool(chat.bind_tools([_ADD_TOOL]).invoke(_TOOL_PROMPT).tool_calls),
               "Calls tools, so the chatbot can search the books and run code.",
               "Did not call a tool. The chatbot needs this to search the books and run code."),
        _probe(choice, "Structured output",
               lambda: structured(chat, _Sum).invoke(_SUM_PROMPT).get("parsed") is not None,
               "Answers in PET's JSON shapes, used by grading, hints and feedback.",
               "Could not answer in a fixed JSON shape. Grading, hints and feedback need this."),
        _context_check(listed.get(choice.model)),
    ]
    return CheckOut(ok=all(c.ok for c in checks), models=models, checks=checks,
                    context=listed.get(choice.model))


def require_capable(choice: Choice) -> None:
    result = check(choice)
    failed = [c for c in result.checks if not c.ok]
    if failed:
        reasons = " ".join(f"{c.name}: {c.detail}" for c in failed)
        raise ModelChoiceRejected(f"{choice.model} can't run PET. {reasons} Pick another model.")
