from pydantic import BaseModel, Field


class ChoiceIn(BaseModel):
    provider: str = Field(max_length=30)
    model: str = Field(default="", max_length=200)
    api_key: str = Field(default="", max_length=500, repr=False)
    base_url: str = Field(default="", max_length=300)


class ProviderOut(BaseModel):
    id: str
    label: str
    base_url: str
    needs_key: bool
    local: bool


class ModelSettingsOut(BaseModel):
    source: str
    provider: str
    provider_label: str
    model: str
    key_hint: str
    has_default: bool
    providers: list[ProviderOut]


class CapabilityCheck(BaseModel):
    name: str
    ok: bool
    detail: str


class CheckOut(BaseModel):
    ok: bool
    models: list[str]
    checks: list[CapabilityCheck] = []
    context: int | None = None
