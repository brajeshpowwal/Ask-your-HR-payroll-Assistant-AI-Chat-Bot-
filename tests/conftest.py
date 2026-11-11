"""Shared test fixtures. Tests build their own copy of the dummy database."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from data.generate_data import generate  # noqa: E402
from src.config import get_settings  # noqa: E402


@pytest.fixture(scope="session")
def db_path(tmp_path_factory) -> Path:
    return generate(tmp_path_factory.mktemp("db") / "test.db")


@pytest.fixture(scope="session")
def settings(db_path):
    return get_settings(db_path=db_path, provider="groq")
