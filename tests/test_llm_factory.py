"""LLM factory tests: pure settings logic only, no network calls."""
import pytest

from src.config import get_settings
from src.llm_factory import LLMConfigError, get_llm, nvidia_model_kwargs


def test_thinking_is_on_by_default(monkeypatch):
    monkeypatch.delenv("LLM_THINKING", raising=False)
    assert get_settings().thinking is True


def test_thinking_off_from_env(monkeypatch):
    monkeypatch.setenv("LLM_THINKING", "off")
    assert get_settings().thinking is False


def test_nvidia_kwargs_disable_thinking_only_when_off():
    assert nvidia_model_kwargs(get_settings(thinking=True)) == {}
    assert nvidia_model_kwargs(get_settings(thinking=False)) == {
        "chat_template_kwargs": {"enable_thinking": False}
    }


def test_unknown_provider_is_rejected():
    with pytest.raises(LLMConfigError, match="Unknown LLM_PROVIDER"):
        get_llm(get_settings(provider="nope"))
