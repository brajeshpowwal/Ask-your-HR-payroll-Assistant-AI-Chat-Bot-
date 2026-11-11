import pytest

from src.sql_guard import UnsafeSQLError, validate_sql

ALLOWED = ("employees", "companies", "payroll_runs")


@pytest.mark.parametrize("sql", [
    "DROP TABLE employees",
    "DELETE FROM employees",
    "UPDATE employees SET status = 'Terminated'",
    "INSERT INTO companies VALUES (9, 'x', 'y', 'TX', 2020)",
    "CREATE TABLE hack (a)",
    "ALTER TABLE employees ADD COLUMN x",
    "ATTACH DATABASE 'other.db' AS other",
    "PRAGMA table_info(employees)",
    "VACUUM",
    "SELECT 1; DROP TABLE employees",
    "SELECT * FROM sqlite_master",
    "SELECT * FROM salaries",                      # not in this allow-list
    "SELECT load_extension('evil')",
    "",
])
def test_blocks_unsafe_sql(sql):
    with pytest.raises(UnsafeSQLError):
        validate_sql(sql, ALLOWED)


@pytest.mark.parametrize("sql", [
    "SELECT * FROM employees",
    "SELECT company_name FROM companies WHERE company_id = 1",
    "WITH a AS (SELECT * FROM employees) SELECT COUNT(*) FROM a",
    "SELECT e.first_name FROM employees e JOIN companies c ON c.company_id = e.company_id",
    "SELECT company_id FROM employees UNION SELECT company_id FROM companies",
    "SELECT strftime('%Y', pay_date) AS y, SUM(gross_pay) FROM payroll_runs GROUP BY y",
])
def test_allows_read_only_sql(sql):
    result = validate_sql(sql, ALLOWED)
    assert "LIMIT" in result.sql.upper()


def test_adds_limit_and_caps_large_limits():
    assert validate_sql("SELECT * FROM employees", ALLOWED, max_rows=50).sql.endswith("LIMIT 50")
    assert validate_sql("SELECT * FROM employees LIMIT 9999", ALLOWED, max_rows=50).sql.endswith("LIMIT 50")
    assert validate_sql("SELECT * FROM employees LIMIT 5", ALLOWED, max_rows=50).sql.endswith("LIMIT 5")


def test_strips_markdown_fences_and_semicolon():
    result = validate_sql("```sql\nSELECT company_name FROM companies;\n```", ALLOWED)
    assert result.sql.startswith("SELECT company_name FROM companies")
    assert result.tables == ["companies"]
