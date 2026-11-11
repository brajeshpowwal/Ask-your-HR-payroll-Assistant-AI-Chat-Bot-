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
