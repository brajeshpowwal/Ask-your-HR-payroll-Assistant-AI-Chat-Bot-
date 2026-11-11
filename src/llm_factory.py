"""Return a LangChain chat model for the chosen provider.

Every provider is wrapped by LangChain behind the same interface
(`model.invoke(messages)`), so the rest of the app never needs to know which
company's model is answering. Imports are lazy: you only need to install the
package for the provider you actually use.
"""
from __future__ import annotations

import os

from langchain_core.language_models.chat_models import BaseChatModel

from src.config import API_KEY_ENV, Settings, get_settings


class LLMConfigError(RuntimeError):
    """Raised when the provider is unknown, its package is missing, or the API key is not set."""


def missing_api_key(settings: Settings) -> str | None:
    """Return the name of the missing environment variable, or None if all good."""
    env = API_KEY_ENV.get(settings.provider)
    if env and not os.getenv(env):
        return env
    return None


def nvidia_model_kwargs(settings: Settings) -> dict:
    """Extra request fields for NVIDIA; thinking is switched off via the chat template."""
    if settings.thinking:
        return {}
    return {"chat_template_kwargs": {"enable_thinking": False}}


def nvidia_token_limit(settings: Settings) -> int:
    """Thinking uses output tokens too; 1,024 can run out before the answer is written."""
    return 4096 if settings.thinking else 1024


def get_llm(settings: Settings | None = None) -> BaseChatModel:
    s = settings or get_settings()
    if s.provider not in API_KEY_ENV:
        raise LLMConfigError(
            f"Unknown LLM_PROVIDER '{s.provider}'. Use one of: {', '.join(API_KEY_ENV)}."
        )
    key_env = missing_api_key(s)
    if key_env:
        raise LLMConfigError(f"{key_env} is not set. Add it to your .env file (see .env.example).")

    try:
        if s.provider == "groq":
            from langchain_groq import ChatGroq
            return ChatGroq(model=s.model_name, temperature=s.temperature)
        if s.provider == "gemini":
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(model=s.model_name, temperature=s.temperature)
        if s.provider == "ollama":
            from langchain_ollama import ChatOllama
            return ChatOllama(model=s.model_name, temperature=s.temperature,
                              base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
        if s.provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(model=s.model_name, temperature=s.temperature, max_tokens=2048)
        if s.provider == "nvidia":
            from langchain_nvidia_ai_endpoints import ChatNVIDIA
            return ChatNVIDIA(model=s.model_name, temperature=s.temperature,
                              max_completion_tokens=nvidia_token_limit(s),
                              model_kwargs=nvidia_model_kwargs(s))
    except ImportError as exc:  # package for this provider not installed
        package = {
            "groq": "langchain-groq", "gemini": "langchain-google-genai",
            "ollama": "langchain-ollama", "anthropic": "langchain-anthropic",
            "nvidia": "langchain-nvidia-ai-endpoints",
        }[s.provider]
        raise LLMConfigError(f"Install the provider package first:  pip install {package}") from exc
    raise LLMConfigError(f"Provider '{s.provider}' is not wired up.")  # pragma: no cover
