"""SQL safety guard: the LLM's SQL must pass these checks before it runs.

We do NOT trust the LLM to behave. We parse its SQL into a syntax tree with
sqlglot and only allow:
  * exactly one statement
  * a read-only query (SELECT, optionally with WITH / UNION)
  * tables from the allow-list
  * no dangerous functions
Then we add a LIMIT so a query can never return millions of rows.

This is layer 2 of 4. The others: a read-only database connection (db.py),
a query timeout (db.py) and a table allow-list (config.py).
"""
from __future__ import annotations

from dataclasses import dataclass

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

# Statement types that change data or the database itself.
FORBIDDEN_NODES = (
    exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter,
    exp.Merge, exp.Command, exp.Transaction, exp.Commit, exp.Rollback,
    exp.Pragma, exp.Attach, exp.Detach, exp.Copy,
)
# SQLite functions that can touch files or load code.
FORBIDDEN_FUNCTIONS = {"load_extension", "readfile", "writefile", "edit", "fts3_tokenizer", "sqlite_offset"}
READ_ONLY_ROOTS = (exp.Select, exp.Union, exp.Intersect, exp.Except)


class UnsafeSQLError(ValueError):
    """The SQL was rejected. The message explains why (it is fed back to the LLM)."""


@dataclass
class GuardResult:
    sql: str            # the cleaned SQL that will actually run
    tables: list[str]   # tables the query reads


def _clean(sql: str) -> str:
    sql = sql.strip()
    if sql.startswith("```"):
        sql = sql.strip("`")
        if sql.lower().startswith("sql"):
            sql = sql[3:]
    return sql.strip().rstrip(";").strip()


def validate_sql(sql: str, allowed_tables: tuple[str, ...] | list[str], max_rows: int = 500) -> GuardResult:
    cleaned = _clean(sql)
    if not cleaned:
        raise UnsafeSQLError("The SQL is empty.")

    try:
        statements = [s for s in sqlglot.parse(cleaned, read="sqlite") if s is not None]
    except ParseError as exc:
        raise UnsafeSQLError(f"The SQL could not be parsed: {str(exc).splitlines()[0]}") from exc
    if len(statements) != 1:
        raise UnsafeSQLError(f"Only one statement is allowed, found {len(statements)}.")
    tree = statements[0]

    if not isinstance(tree, READ_ONLY_ROOTS):
        raise UnsafeSQLError(f"Only SELECT queries are allowed, got {tree.key.upper()}.")
    for node in tree.walk():
        if isinstance(node, FORBIDDEN_NODES):
            raise UnsafeSQLError(f"Forbidden operation in query: {node.key.upper()}.")
        if isinstance(node, exp.Func):
            name = (node.sql_name() if not isinstance(node, exp.Anonymous) else node.name).lower()
            if name in FORBIDDEN_FUNCTIONS:
                raise UnsafeSQLError(f"Forbidden function: {name}.")

    cte_names = {cte.alias_or_name.lower() for cte in tree.find_all(exp.CTE)}
    used = sorted({t.name.lower() for t in tree.find_all(exp.Table) if t.name})
    allowed = {t.lower() for t in allowed_tables}
    blocked = [t for t in used if t not in allowed and t not in cte_names]
    if blocked:
        raise UnsafeSQLError(
            f"Unknown or blocked table(s): {', '.join(blocked)}. "
            f"Allowed tables: {', '.join(sorted(allowed))}."
        )

    # Enforce a row limit on the outermost query.
    existing = tree.args.get("limit")
    if existing is None:
        tree = tree.limit(max_rows)
    else:
        try:
            if int(existing.expression.this) > max_rows:
                tree = tree.limit(max_rows)
        except (AttributeError, ValueError, TypeError):
            tree = tree.limit(max_rows)

    return GuardResult(sql=tree.sql(dialect="sqlite"), tables=[t for t in used if t not in cte_names])
