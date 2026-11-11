import hashlib
import sqlite3

from data.generate_data import COMPANIES, EMPLOYER_TAX_RATE, SNAPSHOT_DATE, generate

TABLES = ["companies", "departments", "employees", "salaries", "payroll_runs",
          "payroll_exceptions", "attendance", "performance_reviews", "leave_balances"]


def _fingerprint(path) -> str:
    con = sqlite3.connect(path)
    digest = hashlib.sha256()
    for t in TABLES:
        for row in con.execute(f"SELECT * FROM {t} ORDER BY 1"):
            digest.update(repr(row).encode())
    con.close()
    return digest.hexdigest()


def test_every_table_has_rows(db_path):
    con = sqlite3.connect(db_path)
    for t in TABLES:
        assert con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] > 0, t


def test_only_fictional_companies(db_path):
    con = sqlite3.connect(db_path)
    names = {r[0] for r in con.execute("SELECT company_name FROM companies")}
    assert names == {c[0] for c in COMPANIES}


def test_generation_is_repeatable(db_path, tmp_path):
    again = generate(tmp_path / "again.db")
    assert _fingerprint(db_path) == _fingerprint(again)


def test_no_orphan_foreign_keys(db_path):
    con = sqlite3.connect(db_path)
    checks = [
        "SELECT COUNT(*) FROM employees e LEFT JOIN departments d USING (department_id) WHERE d.department_id IS NULL",
        "SELECT COUNT(*) FROM employees e LEFT JOIN employees m ON m.employee_id = e.manager_id "
        "WHERE e.manager_id IS NOT NULL AND m.employee_id IS NULL",
        "SELECT COUNT(*) FROM payroll_runs p LEFT JOIN employees e USING (employee_id) WHERE e.employee_id IS NULL",
        "SELECT COUNT(*) FROM payroll_exceptions x LEFT JOIN payroll_runs p USING (payroll_id) "
        "WHERE p.payroll_id IS NULL",
    ]
    for sql in checks:
        assert con.execute(sql).fetchone()[0] == 0, sql


def test_employer_tax_follows_fica_rule(db_path):
    """Employees: 7.65% of gross (Social Security + Medicare); contractors: none."""
    con = sqlite3.connect(db_path)
    rows = con.execute(
        "SELECT e.employment_type, p.gross_pay, p.employer_tax "
        "FROM payroll_runs p JOIN employees e USING (employee_id)"
    ).fetchall()
    assert {r[0] for r in rows} >= {"Full-time", "Contract"}
    for employment_type, gross, employer_tax in rows:
        expected = 0.0 if employment_type == "Contract" else round(gross * EMPLOYER_TAX_RATE, 2)
        assert abs(employer_tax - expected) <= 0.01, (employment_type, gross, employer_tax)


def test_no_payment_after_snapshot_date(db_path):
    """'Today' in the data is SNAPSHOT_DATE; a payment after it has not happened yet."""
    con = sqlite3.connect(db_path)
    last_pay, last_raised = con.execute(
        "SELECT (SELECT MAX(pay_date) FROM payroll_runs), (SELECT MAX(raised_date) FROM payroll_exceptions)"
    ).fetchone()
    assert last_pay <= SNAPSHOT_DATE.isoformat()
    assert last_raised <= SNAPSHOT_DATE.isoformat()


def test_planted_duplicates_exist(db_path):
    con = sqlite3.connect(db_path)
    dupes = con.execute(
        "SELECT COUNT(*) FROM (SELECT 1 FROM payroll_runs "
        "GROUP BY employee_id, pay_period_start HAVING COUNT(*) > 1)"
    ).fetchone()[0]
    assert dupes > 0
