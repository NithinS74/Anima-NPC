from pathlib import Path

import pytest

from npc.generation.config import ConfigurationFailure, load_provider
from npc.generation.provider import ChatCompletionsProvider, OfflineProvider


@pytest.mark.parametrize("profile,key_var,host", [
    ("openrouter", "OPENROUTER_API_KEY", "openrouter.ai/api/v1"),
    ("gemini", "GEMINI_API_KEY", "generativelanguage.googleapis.com/v1beta/openai"),
])
def test_public_profiles_use_local_secrets_and_models(profile, key_var, host):
    provider = load_provider(Path(f"configs/providers/{profile}.yaml"), environ={key_var: "PRIVATE_KEY", "NPC_LLM_MODEL": "chosen-model"})
    assert isinstance(provider, ChatCompletionsProvider)
    assert provider.config.model == "chosen-model"
    assert host in provider.config.base_url
    assert "PRIVATE_KEY" not in repr(provider.config)


def test_offline_profile_requires_no_credentials():
    assert isinstance(load_provider(Path("configs/providers/offline.yaml"), environ={}), OfflineProvider)


def test_missing_config_is_actionable_without_secret_values():
    with pytest.raises(ConfigurationFailure, match="NPC_LLM_MODEL"):
        load_provider(Path("configs/providers/gemini.yaml"), environ={})


def test_profiles_reject_embedded_secret_fields(tmp_path):
    path = tmp_path/"bad.yaml"
    path.write_text("provider: chat_completions\napi_key: PRIVATE_KEY")
    with pytest.raises(ConfigurationFailure) as error:
        load_provider(path, environ={})
    assert "PRIVATE_KEY" not in str(error.value)


def test_environment_overrides_profile_and_generic_key_is_supported():
    provider = load_provider(Path("configs/providers/openrouter.yaml"), environ={
        "NPC_LLM_BASE_URL": "http://127.0.0.1:1234/v1", "NPC_LLM_MODEL": "local-model", "NPC_LLM_API_KEY": "placeholder",
        "NPC_LLM_RESPONSE_FORMAT": "none",
    })
    assert provider.config.base_url == "http://127.0.0.1:1234/v1"
    assert provider.config.response_format == "none"
