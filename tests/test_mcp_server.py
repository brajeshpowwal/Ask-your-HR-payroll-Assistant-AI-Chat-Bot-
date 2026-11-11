"""MCP server tests: call the tools through the server, the way an MCP client would."""
import asyncio
import sys
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from src.mcp_server import build_server

SERVER_SCRIPT = Path(__file__).resolve().parent.parent / "src" / "mcp_server.py"


def _call(server, name: str, args: dict | None = None) -> str:
    result = asyncio.run(server.call_tool(name, args or {}))
    return "\n".join(getattr(part, "text", "") for part in result.content)


def test_only_read_only_tools_are_exposed(settings):
    tools = asyncio.run(build_server(settings).list_tools())
    assert {t.name for t in tools} == {"list_tables", "describe_tables", "business_rules", "run_sql"}
    assert all(t.annotations and t.annotations.read_only_hint for t in tools)


def test_list_and_describe_tables(settings):
    server = build_server(settings)
    assert "payroll_runs" in _call(server, "list_tables")
    described = _call(server, "describe_tables", {"tables": ["companies"]})
    assert "TABLE companies" in described and "company_name" in described


def test_describe_rejects_unknown_tables(settings):
    text = _call(build_server(settings), "describe_tables", {"tables": ["sqlite_master"]})
    assert text.startswith("Error") and "sqlite_master" in text


def test_business_rules_include_snapshot_date(settings):
    assert "2026-10-31" in _call(build_server(settings), "business_rules")


def test_run_sql_returns_rows(settings):
    text = _call(build_server(settings), "run_sql",
                 {"sql": "SELECT company_name FROM companies ORDER BY company_name"})
    assert "4 rows" in text and "Brightwave Solutions" in text


def test_run_sql_blocks_writes_and_hidden_tables(settings):
    server = build_server(settings)
    for sql in ("DELETE FROM employees", "DROP TABLE companies", "SELECT * FROM sqlite_master",
                "SELECT 1; DELETE FROM employees"):
        text = _call(server, "run_sql", {"sql": sql})
        assert text.startswith("Error"), sql
    assert "4 rows" in _call(server, "run_sql", {"sql": "SELECT * FROM companies"})  # data untouched


def test_run_sql_reports_database_errors(settings):
    text = _call(build_server(settings), "run_sql", {"sql": "SELECT no_such_column FROM companies"})
    assert text.startswith("Error") and "no_such_column" in text


def test_runs_as_a_script_over_stdio(tmp_path):
    """Claude Desktop starts the server by file path from any folder, talking JSON-RPC over stdout."""
    async def session() -> tuple[list[str], str]:
        params = StdioServerParameters(command=sys.executable, args=[str(SERVER_SCRIPT)], cwd=str(tmp_path))
        async with stdio_client(params) as (read, write), ClientSession(read, write) as s:
            await s.initialize()
            names = [t.name for t in (await s.list_tools()).tools]
            result = await s.call_tool("run_sql", {"sql": "SELECT COUNT(*) AS n FROM companies"})
            return names, "\n".join(getattr(part, "text", "") for part in result.content)

    names, text = asyncio.run(session())
    assert "run_sql" in names
    assert "n\n4" in text


def test_long_results_are_cut_for_the_client(settings):
    text = _call(build_server(settings), "run_sql", {"sql": "SELECT employee_id FROM employees"})
    assert "showing the first 100" in text
