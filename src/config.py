"""Central settings, read from environment variables (and a local .env file).

Nothing secret is ever hard-coded here. Copy .env.example to .env and fill it in.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# Default model per provider. Providers retire models often: if a default stops
# working, set LLM_MODEL in .env to a model from the provider's current list.
DEFAULT_MODELS = {
    "groq": "openai/gpt-oss-120b",
    "gemini": "gemini-2.5-flash",
    "ollama": "qwen2.5-coder:7b",
    "anthropic": "claude-sonnet-5-5",
    "nvidia": "nvidia/nemotron-3.5-lightning-30b-a3b",  # llama-3.3-70b retired 2026-08-26
}

API_KEY_ENV = {
    "groq": "GROQ_API_KEY",
    "gemini": "GOOGLE_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "nvidia": "NVIDIA_API_KEY",
    "ollama": None,  # runs locally, no key needed
}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


@dataclass(frozen=True)
class Settings:
    provider: str = field(default_factory=lambda: os.getenv("LLM_PROVIDER", "groq").strip().lower())
    model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "").strip())
    temperature: float = 0.0
    # Reasoning models "think" before answering. Off by default: on the NVIDIA benchmark
    # sample, thinking off was ~4x faster and more accurate. Currently honoured for NVIDIA.
    thinking: bool = field(default_factory=lambda: os.getenv("LLM_THINKING", "off").strip().lower() == "on")
    db_path: Path = field(default_factory=lambda: Path(os.getenv("DB_PATH", ROOT / "data" / "hr_payroll.db")))
    schema_docs_path: Path = ROOT / "data" / "schema_docs.yaml"
    glossary_path: Path = ROOT / "data" / "glossary.yaml"
    examples_path: Path = ROOT / "data" / "examples.yaml"
    max_rows: int = field(default_factory=lambda: _int("MAX_ROWS", 500))
    query_timeout_s: int = field(default_factory=lambda: _int("QUERY_TIMEOUT_SECONDS", 10))
    max_retries: int = field(default_factory=lambda: _int("MAX_SQL_RETRIES", 3))
    num_examples: int = field(default_factory=lambda: _int("NUM_EXAMPLES", 4))
    max_questions_per_session: int = field(default_factory=lambda: _int("MAX_QUESTIONS_PER_SESSION", 25))
    # Tables the assistant may read. Anything else is blocked by the SQL guard.
    allowed_tables: tuple[str, ...] = (
        "companies", "departments", "employees", "salaries", "payroll_runs",
        "payroll_exceptions", "attendance", "performance_reviews", "leave_balances",
    )

    @property
    def model_name(self) -> str:
        return self.model or DEFAULT_MODELS.get(self.provider, "")


def get_settings(**overrides) -> Settings:
    """Return settings; keyword overrides are handy in tests and the UI."""
    base = Settings()
    if not overrides:
        return base
    values = {f: getattr(base, f) for f in base.__dataclass_fields__}
    values.update(overrides)
    return Settings(**values)
