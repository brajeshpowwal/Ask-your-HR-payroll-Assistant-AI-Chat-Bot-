"""Read the real database schema and turn it into text the LLM can understand.

Two outputs:
- table_catalog(): one line per table (name + description), used to pick tables.
- schema_prompt(tables): CREATE-style description of the chosen tables with
  column meanings, foreign keys and 3 sample rows, used to write SQL.

The LLM only ever sees the schema and a few sample rows, never full tables.
"""
from __future__ import annotations

import sqlite3
from functools import lru_cache
from pathlib import Path

import yaml

from src.config import Settings, get_settings


@lru_cache(maxsize=4)
def _load_docs(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def load_glossary(settings: Settings | None = None) -> dict:
    s = settings or get_settings()
    return _load_docs(str(s.glossary_path))


class SchemaInfo:
    """Holds table structure read from SQLite plus the business docs."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.docs = _load_docs(str(self.settings.schema_docs_path))
        self.tables = self._read_tables(self.settings.db_path)

    def _read_tables(self, db_path: Path) -> dict[str, dict]:
        con = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            names = [r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
            tables = {}
            for name in names:
                if name not in self.settings.allowed_tables:
                    continue
                cols = con.execute(f"PRAGMA table_info('{name}')").fetchall()
                fks = con.execute(f"PRAGMA foreign_key_list('{name}')").fetchall()
                sample = con.execute(f"SELECT * FROM '{name}' LIMIT 3").fetchall()
                tables[name] = {
                    "columns": [(c[1], c[2], bool(c[5])) for c in cols],  # name, type, is_pk
                    "foreign_keys": [(f[3], f[2], f[4]) for f in fks],     # col -> table.col
                    "sample_rows": sample,
                }
            return tables
        finally:
            con.close()

    # ------------------------------------------------------------------ text
    def table_catalog(self) -> str:
        lines = []
        for name in self.tables:
            desc = self.docs.get(name, {}).get("description", "")
            lines.append(f"- {name}: {desc}")
        return "\n".join(lines)

    def schema_prompt(self, tables: list[str] | None = None) -> str:
        chosen = [t for t in (tables or list(self.tables)) if t in self.tables]
        blocks = []
        for name in chosen:
            info, doc = self.tables[name], self.docs.get(name, {})
            col_docs = doc.get("columns", {})
            lines = [f"TABLE {name}  -- {doc.get('description', '')}"]
            for col, ctype, is_pk in info["columns"]:
                flag = " PRIMARY KEY" if is_pk else ""
                meaning = col_docs.get(col, "")
                lines.append(f"  {col} {ctype}{flag}  -- {meaning}")
            for col, ref_table, ref_col in info["foreign_keys"]:
                lines.append(f"  FOREIGN KEY {col} -> {ref_table}.{ref_col}")
            if info["sample_rows"]:
                header = ", ".join(c[0] for c in info["columns"])
                lines.append(f"  Sample rows ({header}):")
                for row in info["sample_rows"]:
                    lines.append(f"    {row}")
            blocks.append("\n".join(lines))
        return "\n\n".join(blocks)

    def glossary_prompt(self) -> str:
        rules = load_glossary(self.settings).get("rules", [])
        return "\n".join(f"- {r}" for r in rules)
