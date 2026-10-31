"""Public provider profiles plus local secret/model overrides."""

import os
from pathlib import Path
from typing import Mapping

import yaml
from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from npc.generation.provider import ChatCompletionsProvider, ModelProvider, OfflineProvider, ProviderConfig


class ConfigurationFailure(ValueError):
    pass


class ProviderProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    provider: str
    base_url: str = Field(default="", repr=False)
    model: str = ""
    api_key_env: str = "NPC_LLM_API_KEY"
    response_format: str = "json_object"
    reasoning_effort: str | None = None


def load_provider(path: Path, *, environ: Mapping[str, str] | None = None) -> ModelProvider:
    try:
        if path.stat().st_size > 16384:
            raise ConfigurationFailure("provider profile exceeds 16 KB")
        profile = ProviderProfile.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
        local = dotenv_values(".env", interpolate=False) if environ is None else {}
        settings = {**local, **(os.environ if environ is None else environ)}
        if profile.provider == "offline":
            return OfflineProvider()
        if profile.provider != "chat_completions":
            raise ConfigurationFailure("unsupported provider transport")
        model = settings.get("NPC_LLM_MODEL") or profile.model
        key = settings.get(profile.api_key_env) or settings.get("NPC_LLM_API_KEY")
        base_url = settings.get("NPC_LLM_BASE_URL") or profile.base_url
        if not model or not key:
            raise ConfigurationFailure("configure NPC_LLM_MODEL and the profile's key environment variable locally")
        config = ProviderConfig(base_url=base_url, model=model, api_key=key,
                                reasoning_effort=settings.get("NPC_LLM_REASONING_EFFORT") or profile.reasoning_effort,
                                response_format=settings.get("NPC_LLM_RESPONSE_FORMAT") or profile.response_format)
        return ChatCompletionsProvider(config)
    except ConfigurationFailure:
        raise
    except (OSError, ValueError, TypeError, yaml.YAMLError, ValidationError):
        raise ConfigurationFailure("invalid provider profile or local configuration; secrets omitted") from None
