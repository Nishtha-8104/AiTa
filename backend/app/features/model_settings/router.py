# Endpoints, under /api/v1/model-settings:
#   GET    /      the model in use (never the key) and the providers on offer
#   POST   /test  check a provider, key and model: connection, tool calls, structured
#                 output, context window; returns the account's models
#   PUT    /      refuse a model that fails a check, else keep the choice in this
#                 browser's encrypted cookie
#   DELETE /      forget the choice, back to PET default

from fastapi import APIRouter, Depends, Response

from app.core.dependencies import get_current_active_user
from app.core.exceptions import ModelChoiceRejected
from app.core.llm_choice import clear_cookie, current_choice, set_cookie
from app.features.accounts.models import User
from app.features.model_settings.schemas import ChoiceIn, CheckOut, ModelSettingsOut
from app.features.model_settings.service import check, require_capable, resolve, view

router = APIRouter(prefix="/model-settings", tags=["Model settings"])


@router.get("", response_model=ModelSettingsOut, summary="The model in use")
def get_settings(_: User = Depends(get_current_active_user)):
    return view(current_choice())


@router.post("/test", response_model=CheckOut, summary="Check a provider, key and model")
def test_settings(data: ChoiceIn, _: User = Depends(get_current_active_user)):
    return check(resolve(data, current_choice()))


@router.put("", response_model=ModelSettingsOut, summary="Use this model from now on")
def save_settings(data: ChoiceIn, response: Response,
                  _: User = Depends(get_current_active_user)):
    choice = resolve(data, current_choice())
    if not choice.model:
        raise ModelChoiceRejected("Pick a model.")
    require_capable(choice)
    set_cookie(response, choice)
    return view(choice)


@router.delete("", response_model=ModelSettingsOut, summary="Back to PET default")
def remove_settings(response: Response, _: User = Depends(get_current_active_user)):
    clear_cookie(response)
    return view(None)
