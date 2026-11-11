"""Run SQL against SQLite safely: read-only connection + time limit.

Layer 1 (read-only): the file is opened with mode=ro and PRAGMA query_only=ON,
so even if a write statement slipped past the guard, SQLite itself refuses it.
Layer 3 (timeout): a progress handler aborts any query that runs too long.
"""
from __future__ import annotations

import sqlite3
import time
from pathlib import Path

import pandas as pd


class QueryError(RuntimeError):
    """The database rejected or aborted the query. Message is fed back to the LLM."""


def ensure_database(db_path: Path) -> Path:
    """Create the dummy database on first run (e.g. on Streamlit Cloud)."""
    db_path = Path(db_path)
    if not db_path.exists():
        from data.generate_data import generate  # local import keeps startup fast
        generate(db_path)
    return db_path


def connect_read_only(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{Path(db_path).as_posix()}?mode=ro", uri=True, check_same_thread=False)
    con.execute("PRAGMA query_only = ON")
    return con


def run_query(sql: str, db_path: Path, timeout_s: float = 10) -> pd.DataFrame:
    con = connect_read_only(db_path)
    deadline = time.monotonic() + timeout_s
    # Called every 10,000 SQLite steps; returning non-zero aborts the query.
    con.set_progress_handler(lambda: 1 if time.monotonic() > deadline else 0, 10_000)
    try:
        return pd.read_sql_query(sql, con)
    except Exception as exc:  # sqlite3.OperationalError, DatabaseError, pandas errors
        message = str(exc)
        if message.startswith("Execution failed on sql"):  # pandas wraps the sqlite message
            message = message.rsplit("': ", 1)[-1]
        if "interrupted" in message.lower():
            message = f"Query took longer than {timeout_s} seconds and was stopped. Simplify it."
        raise QueryError(message) from exc
    finally:
        con.close()
