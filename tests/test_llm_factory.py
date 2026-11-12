"""LLM factory tests: pure settings logic only, no network calls."""
import pytest

from src.config import get_settings
from src.llm_factory import LLMConfigError, get_llm, nvidia_model_kwargs, nvidia_token_limit


def test_thinking_is_off_by_default(monkeypatch):
    monkeypatch.delenv("LLM_THINKING", raising=False)
    assert get_settings().thinking is False


def test_thinking_on_from_env(monkeypatch):
    monkeypatch.setenv("LLM_THINKING", "on")
    assert get_settings().thinking is True


def test_thinking_gets_a_bigger_token_budget():
    """With thinking on, 1,024 tokens ran out mid-thought and the reply came back empty."""
    assert nvidia_token_limit(get_settings(thinking=False)) == 1024
    assert nvidia_token_limit(get_settings(thinking=True)) == 4096


def test_nvidia_kwargs_disable_thinking_only_when_off():
    assert nvidia_model_kwargs(get_settings(thinking=True)) == {}
    assert nvidia_model_kwargs(get_settings(thinking=False)) == {
        "chat_template_kwargs": {"enable_thinking": False}
    }


def test_unknown_provider_is_rejected():
    with pytest.raises(LLMConfigError, match="Unknown LLM_PROVIDER"):
        get_llm(get_settings(provider="nope"))


def test_retired_model_errors_are_recognised():
    """Providers retire models (NVIDIA answers 410 Gone); the app then falls back to the default model."""
    from src.llm_factory import is_retired_model_error
    gone = Exception("[410] Gone\nThe model 'meta/llama-3.3-70b-instruct' has reached its end of life on 2026-08-26")
    assert is_retired_model_error(gone)
    assert is_retired_model_error(Exception("model_decommissioned: this model has been decommissioned"))
    assert not is_retired_model_error(Exception("[429] Too Many Requests"))
    assert not is_retired_model_error(Exception("[401] Unauthorized"))


def test_hosting_secrets_are_trimmed_into_env(monkeypatch):
    """A key pasted with a trailing space or newline is rejected by the provider (403)."""
    from src.config import apply_secrets
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    apply_secrets({"NVIDIA_API_KEY": "  nvapi-test\n", "LLM_PROVIDER": "nvidia", "nested": {"a": 1}})
    import os
    assert os.environ["NVIDIA_API_KEY"] == "nvapi-test"
    assert os.environ["LLM_PROVIDER"] == "groq"  # real environment variables win over secrets
