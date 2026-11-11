"""MCP server: lets Claude Desktop (or any MCP client) query the dummy HR & payroll database.

The client's own model writes the SQL, so this server needs no API key. It exposes only
read tools, and every query goes through the same safety layers as the chat app:
sql_guard (single SELECT, table allow-list, LIMIT) and db (read-only connection, timeout).

Run:  python src/mcp_server.py        (stdio transport, which is what Claude Desktop uses)
"""
from __future__ import annotations

import sys
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

# Claude Desktop starts this file by path from any folder; make the project importable.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import Settings, get_settings  # noqa: E402
from src.db import QueryError, ensure_database, run_query  # noqa: E402
from src.schema import SchemaInfo  # noqa: E402
from src.sql_guard import UnsafeSQLError, validate_sql  # noqa: E402

ROWS_RETURNED = 100  # keeps tool replies small enough for the client's context window
READ_ONLY = ToolAnnotations(read_only_hint=True, destructive_hint=False, open_world_hint=False)

INSTRUCTIONS = """Fictional HR & payroll data for four made-up companies.
Start with list_tables and business_rules, then describe_tables for the tables you need,
then run_sql with one SQLite SELECT. Follow the business rules (for example, today is the
snapshot date, not the real date). The database is read-only."""


def build_server(settings: Settings | None = None) -> MCPServer:
    """Create the server; tools are closures over one settings object, so tests can pass their own."""
    s = settings or get_settings()
    ensure_database(s.db_path)
    schema = SchemaInfo(s)
    server = MCPServer(name="talktodata", instructions=INSTRUCTIONS)

    @server.tool(annotations=READ_ONLY)
    def list_tables() -> str:
        """List the tables you can query, each with a one-line description."""
        return schema.table_catalog()

    @server.tool(annotations=READ_ONLY)
    def describe_tables(tables: list[str]) -> str:
        """Show columns, their meaning, foreign keys and 3 sample rows for the given tables."""
        unknown = [t for t in tables if t not in schema.tables]
        if unknown:
            return f"Error: unknown table(s): {', '.join(unknown)}. Use list_tables to see what exists."
        return schema.schema_prompt(tables)

    @server.tool(annotations=READ_ONLY)
    def business_rules() -> str:
        """Company definitions (headcount, attrition, payroll cost ...) that every query must follow."""
        return f"Today in the data: {schema.snapshot_date()}\n{schema.glossary_prompt()}"

    @server.tool(annotations=READ_ONLY)
    def run_sql(sql: str) -> str:
        """Run one read-only SQLite SELECT and return the result as CSV."""
        try:
            checked = validate_sql(sql, s.allowed_tables, s.max_rows)
            df = run_query(checked.sql, s.db_path, s.query_timeout_s)
        except (UnsafeSQLError, QueryError) as exc:
            return f"Error: {exc}"
        header = f"{len(df)} rows"
        if len(df) > ROWS_RETURNED:
            header += f", showing the first {ROWS_RETURNED}"
        if len(df) >= s.max_rows:
            header += f" (stopped at the {s.max_rows}-row limit)"
        body = df.head(ROWS_RETURNED).to_csv(index=False, lineterminator="\n") if not df.empty else "(no rows)"
        return f"{header}\nSQL run: {checked.sql}\n\n{body}"

    return server


def main() -> None:
    build_server().run()  # stdio


if __name__ == "__main__":
    main()
