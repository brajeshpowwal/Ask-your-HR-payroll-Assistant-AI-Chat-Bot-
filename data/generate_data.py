"""Generate the dummy HR & payroll SQLite database.

Everything here is fictional: company names, people, IDs and amounts are
generated with Faker and a fixed random seed, so every run produces the
same database. No real employer, client or employee data is used.

Run:  python data/generate_data.py            (writes data/hr_payroll.db)
      python data/generate_data.py --out x.db (custom path)
"""
from __future__ import annotations

import argparse
import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

from faker import Faker

SEED = 42
SNAPSHOT_DATE = date(2026, 10, 31)          # the "today" of the dataset
PAYROLL_START = date(2024, 11, 1)           # two years of biweekly payroll
ATTENDANCE_DAYS = 90                        # attendance kept for the last 90 days
DEFAULT_PATH = Path(__file__).resolve().parent / "hr_payroll.db"

COMPANIES = [
    # name, industry, hq_state, founded, target headcount
    ("Brightwave Solutions", "Software", "TX", 2012, 190),
    ("Cedarline Health", "Healthcare", "OH", 2009, 160),
    ("Northpeak Logistics", "Logistics", "GA", 2015, 140),
    ("Orbitron Retail", "Retail", "AZ", 2018, 110),
]

DEPARTMENTS = ["Engineering", "Sales", "Finance", "Human Resources", "Customer Support"]

ROLE_BY_DEPT = {
    "Engineering": ("Engineer", "Engineering Manager"),
    "Sales": ("Sales Representative", "Sales Manager"),
    "Finance": ("Accountant", "Finance Manager"),
    "Human Resources": ("HR Generalist", "HR Manager"),
    "Customer Support": ("Support Agent", "Support Manager"),
}
LEVEL_PREFIX = {1: "Associate", 2: "", 3: "Senior"}
BASE_SALARY = {  # salary range by job level (USD)
    1: (42000, 58000), 2: (58000, 82000), 3: (82000, 115000),
    4: (110000, 145000), 5: (140000, 190000), 6: (200000, 260000),
}
DEPT_SALARY_FACTOR = {
    "Engineering": 1.25, "Sales": 1.0, "Finance": 1.05,
    "Human Resources": 0.95, "Customer Support": 0.8, "Executive": 1.3,
}
US_STATES = ["TX", "OH", "GA", "AZ", "CA", "NY", "FL", "IL", "NC", "WA", "CO", "PA"]
EXCEPTION_TYPES = [
    "Missing Timesheet", "Overtime Spike", "Incorrect Tax Withholding",
    "Retro Pay Adjustment", "Bank Detail Mismatch",
]
TERMINATION_REASONS = ["Resignation", "Better Offer", "Relocation", "Performance", "Layoff", "Retirement"]

SCHEMA = """
CREATE TABLE companies (
    company_id    INTEGER PRIMARY KEY,
    company_name  TEXT NOT NULL,
    industry      TEXT NOT NULL,
    hq_state      TEXT NOT NULL,
    founded_year  INTEGER NOT NULL
);
CREATE TABLE departments (
    department_id   INTEGER PRIMARY KEY,
    company_id      INTEGER NOT NULL REFERENCES companies(company_id),
    department_name TEXT NOT NULL,
    cost_center     TEXT NOT NULL
);
CREATE TABLE employees (
    employee_id        INTEGER PRIMARY KEY,
    company_id         INTEGER NOT NULL REFERENCES companies(company_id),
    department_id      INTEGER NOT NULL REFERENCES departments(department_id),
    first_name         TEXT NOT NULL,
    last_name          TEXT NOT NULL,
    email              TEXT NOT NULL,
    job_title          TEXT NOT NULL,
    job_level          INTEGER NOT NULL,
    manager_id         INTEGER REFERENCES employees(employee_id),
    employment_type    TEXT NOT NULL,
    work_state         TEXT NOT NULL,
    hire_date          TEXT NOT NULL,
    termination_date   TEXT,
    termination_reason TEXT,
    status             TEXT NOT NULL
);
CREATE TABLE salaries (
    salary_id      INTEGER PRIMARY KEY,
    employee_id    INTEGER NOT NULL REFERENCES employees(employee_id),
    effective_date TEXT NOT NULL,
    annual_salary  REAL NOT NULL,
    change_reason  TEXT NOT NULL
);
CREATE TABLE payroll_runs (
    payroll_id         INTEGER PRIMARY KEY,
    employee_id        INTEGER NOT NULL REFERENCES employees(employee_id),
    company_id         INTEGER NOT NULL REFERENCES companies(company_id),
    pay_period_start   TEXT NOT NULL,
    pay_period_end     TEXT NOT NULL,
    pay_date           TEXT NOT NULL,
    regular_hours      REAL NOT NULL,
    overtime_hours     REAL NOT NULL,
    gross_pay          REAL NOT NULL,
    tax_withheld       REAL NOT NULL,
    benefits_deduction REAL NOT NULL,
    net_pay            REAL NOT NULL
);
CREATE TABLE payroll_exceptions (
    exception_id   INTEGER PRIMARY KEY,
    payroll_id     INTEGER NOT NULL REFERENCES payroll_runs(payroll_id),
    employee_id    INTEGER NOT NULL REFERENCES employees(employee_id),
    company_id     INTEGER NOT NULL REFERENCES companies(company_id),
    exception_type TEXT NOT NULL,
    amount         REAL NOT NULL,
    status         TEXT NOT NULL,
    raised_date    TEXT NOT NULL,
    resolved_date  TEXT
);
CREATE TABLE attendance (
    attendance_id INTEGER PRIMARY KEY,
    employee_id   INTEGER NOT NULL REFERENCES employees(employee_id),
    work_date     TEXT NOT NULL,
    status        TEXT NOT NULL,
    hours_worked  REAL NOT NULL,
    leave_type    TEXT
);
CREATE TABLE performance_reviews (
    review_id    INTEGER PRIMARY KEY,
    employee_id  INTEGER NOT NULL REFERENCES employees(employee_id),
    reviewer_id  INTEGER REFERENCES employees(employee_id),
    review_cycle TEXT NOT NULL,
    review_date  TEXT NOT NULL,
    rating       INTEGER NOT NULL
);
CREATE TABLE leave_balances (
    employee_id   INTEGER NOT NULL REFERENCES employees(employee_id),
    leave_type    TEXT NOT NULL,
    entitled_days REAL NOT NULL,
    used_days     REAL NOT NULL,
    balance_days  REAL NOT NULL,
    PRIMARY KEY (employee_id, leave_type)
);
CREATE INDEX idx_emp_company    ON employees(company_id);
CREATE INDEX idx_emp_department ON employees(department_id);
CREATE INDEX idx_sal_emp        ON salaries(employee_id);
CREATE INDEX idx_pay_emp        ON payroll_runs(employee_id);
CREATE INDEX idx_pay_period     ON payroll_runs(pay_period_end);
CREATE INDEX idx_exc_status     ON payroll_exceptions(status);
CREATE INDEX idx_att_emp_date   ON attendance(employee_id, work_date);
CREATE INDEX idx_rev_emp        ON performance_reviews(employee_id);
"""


def _iso(x: date | None) -> str | None:
    return x.isoformat() if x else None


def _rand_date(rng: random.Random, start: date, end: date) -> date:
    return start + timedelta(days=rng.randint(0, max(0, (end - start).days)))


def generate(out_path: Path | str = DEFAULT_PATH) -> Path:
    """Build the database at out_path (overwrites it) and return the path."""
    rng = random.Random(SEED)
    fake = Faker("en_US")
    fake.seed_instance(SEED)

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        out_path.unlink()

    companies, departments, employees = [], [], []
    salaries, payroll, exceptions = [], [], []
    attendance, reviews, balances = [], [], []
    counter = {"emp": 1000, "dept": 0}

    # ---------------------------------------------------------------- people
    for c_id, (cname, industry, hq, founded, target) in enumerate(COMPANIES, start=1):
        companies.append((c_id, cname, industry, hq, founded))
        domain = cname.lower().replace(" ", "") + ".example"

        def new_emp(dept, title, level, manager, hire, emp_type="Full-time"):
            counter["emp"] += 1
            eid = counter["emp"]
            first, last = fake.first_name(), fake.last_name()
            rec = {
                "employee_id": eid, "company_id": c_id, "department_id": dept[0],
                "dept_name": dept[2], "first_name": first, "last_name": last,
                "email": f"{first}.{last}{eid}@{domain}".lower(),
                "job_title": title, "job_level": level, "manager_id": manager,
                "employment_type": emp_type,
                "work_state": hq if rng.random() < 0.6 else rng.choice(US_STATES),
                "hire_date": hire.isoformat(), "termination_date": None,
                "termination_reason": None, "status": "Active",
            }
            employees.append(rec)
            return rec

        counter["dept"] += 1
        exec_dept = (counter["dept"], c_id, "Executive", f"CC-{c_id}00")
        departments.append(exec_dept)
        ceo = new_emp(exec_dept, "Chief Executive Officer", 6, None,
                      _rand_date(rng, date(founded, 1, 1), date(founded + 3, 12, 31)))

        remaining = target - 1
        for k, dname in enumerate(DEPARTMENTS, start=1):
            counter["dept"] += 1
            dept = (counter["dept"], c_id, dname, f"CC-{c_id}{k:02d}")
            departments.append(dept)
            role, mgr_title = ROLE_BY_DEPT[dname]
            head = new_emp(dept, f"Head of {dname}", 5, ceo["employee_id"],
                           _rand_date(rng, date(max(founded, 2016), 1, 1), date(2022, 12, 31)))
            managers = [new_emp(dept, mgr_title, 4, head["employee_id"],
                                _rand_date(rng, date(2017, 1, 1), date(2024, 6, 30)))
                        for _ in range(2)]
            weight = {"Engineering": 1.3, "Sales": 1.1, "Customer Support": 1.2}.get(dname, 0.6)
            share = remaining // (len(DEPARTMENTS) - k + 1)
            staff_n = max(6, int(share * weight) - 3)
            remaining -= staff_n + 3
            for _ in range(staff_n):
                level = rng.choices([1, 2, 3], weights=[3, 5, 2])[0]
                title = f"{LEVEL_PREFIX[level]} {role}".strip()
                emp_type = rng.choices(["Full-time", "Part-time", "Contract"], weights=[80, 10, 10])[0]
                year = rng.choices(range(2018, 2027), weights=[2, 2, 3, 3, 4, 5, 6, 7, 6])[0]
                last_day = min(date(year, 12, 31), SNAPSHOT_DATE - timedelta(days=20))
                hire = _rand_date(rng, date(year, 1, 1), last_day)
                new_emp(dept, title, level, rng.choice(managers)["employee_id"], hire, emp_type)

    # ---------------------------------------------------------- terminations
    for e in employees:
        if e["job_level"] >= 5:
            continue
        hire = date.fromisoformat(e["hire_date"])
        if rng.random() < 0.18:
            start = max(hire + timedelta(days=60), date(2023, 1, 1))
            if start < SNAPSHOT_DATE - timedelta(days=5):
                t = _rand_date(rng, start, SNAPSHOT_DATE - timedelta(days=5))
                e["termination_date"] = t.isoformat()
                e["termination_reason"] = rng.choices(TERMINATION_REASONS, weights=[30, 25, 10, 12, 15, 8])[0]
                e["status"] = "Terminated"

    # -------------------------------------------------------------- salaries
    history: dict[int, list[tuple[date, float]]] = {}
    sal_id = 0
    for e in employees:
        lo, hi = BASE_SALARY[e["job_level"]]
        base = rng.uniform(lo, hi) * DEPT_SALARY_FACTOR.get(e["dept_name"], 1.0)
        if e["employment_type"] == "Contract":
            base *= 1.1
        hire = date.fromisoformat(e["hire_date"])
        end = date.fromisoformat(e["termination_date"]) if e["termination_date"] else SNAPSHOT_DATE
        sal_id += 1
        salaries.append((sal_id, e["employee_id"], hire.isoformat(), round(base, 2), "New Hire"))
        hist = [(hire, base)]
        year = hire.year + 1
        while date(year, 4, 1) <= end:
            if rng.random() < 0.8:
                promo = rng.random() < 0.12
                base *= 1 + (rng.uniform(0.08, 0.15) if promo else rng.uniform(0.02, 0.06))
                sal_id += 1
                salaries.append((sal_id, e["employee_id"], date(year, 4, 1).isoformat(),
                                 round(base, 2), "Promotion" if promo else "Annual Merit"))
                hist.append((date(year, 4, 1), base))
            year += 1
        history[e["employee_id"]] = hist

    def salary_on(eid: int, day: date) -> float:
        value = history[eid][0][1]
        for eff, amount in history[eid]:
            if eff <= day:
                value = amount
        return value

    # --------------------------------------------------------------- payroll
    pay_id = 0
    period_start = PAYROLL_START
    while period_start + timedelta(days=13) <= SNAPSHOT_DATE:
        period_end = period_start + timedelta(days=13)
        pay_date = period_end + timedelta(days=5)
        for e in employees:
            hire = date.fromisoformat(e["hire_date"])
            term = date.fromisoformat(e["termination_date"]) if e["termination_date"] else None
            if hire > period_end or (term and term < period_start):
                continue
            annual = salary_on(e["employee_id"], period_end)
            factor = 0.5 if e["employment_type"] == "Part-time" else 1.0
            ot_hours = 0.0
            if e["job_level"] <= 2 and e["dept_name"] in ("Customer Support", "Engineering", "Sales"):
                ot_hours = round(rng.choice([0, 0, 0, 2, 4, 6, 8]) * rng.random(), 1)
                if rng.random() < 0.01:
                    ot_hours = round(rng.uniform(25, 40), 1)  # planted overtime spike
            gross = annual / 26 * factor + ot_hours * (annual / 2080) * 1.5
            tax = gross * rng.uniform(0.18, 0.24)
            benefits = 0.0 if e["employment_type"] == "Contract" else (180.0 if factor == 1 else 90.0)
            pay_id += 1
            row = (pay_id, e["employee_id"], e["company_id"], period_start.isoformat(),
                   period_end.isoformat(), pay_date.isoformat(), 80.0 * factor, ot_hours,
                   round(gross, 2), round(tax, 2), benefits, round(gross - tax - benefits, 2))
            payroll.append(row)
            if rng.random() < 0.0008:  # planted duplicate payment
                pay_id += 1
                payroll.append((pay_id,) + row[1:])
        period_start += timedelta(days=14)

    # ---------------------------------------------------- payroll exceptions
    exc_id = 0
    seen: set[tuple[int, str]] = set()
    for row in payroll:
        key = (row[1], row[3])
        if key in seen:
            exc_id += 1
            raised = min(date.fromisoformat(row[5]) + timedelta(days=rng.randint(1, 10)), SNAPSHOT_DATE)
            exceptions.append((exc_id, row[0], row[1], row[2], "Duplicate Payment", row[8],
                               "Open", _iso(raised), None))
        seen.add(key)
    for row in rng.sample(payroll, 420):
        exc_id += 1
        etype = "Overtime Spike" if row[7] > 20 else rng.choice(EXCEPTION_TYPES)
        raised = min(date.fromisoformat(row[5]) + timedelta(days=rng.randint(0, 6)), SNAPSHOT_DATE)
        age = (SNAPSHOT_DATE - raised).days
        if age > 60:
            status = "Resolved" if rng.random() < 0.97 else "In Review"
        elif age > 14:
            status = rng.choices(["Resolved", "In Review", "Open"], weights=[70, 15, 15])[0]
        else:
            status = rng.choices(["Resolved", "In Review", "Open"], weights=[25, 25, 50])[0]
        resolved = (_iso(min(raised + timedelta(days=rng.randint(1, 20)), SNAPSHOT_DATE))
                    if status == "Resolved" else None)
        exceptions.append((exc_id, row[0], row[1], row[2], etype,
                           round(rng.uniform(25, 1500), 2), status, _iso(raised), resolved))

    # ------------------------------------------------------------ attendance
    att_id = 0
    att_start = SNAPSHOT_DATE - timedelta(days=ATTENDANCE_DAYS - 1)
    holidays = {date(2026, 9, 7), date(2026, 10, 12)}
    absence_prone = {e["employee_id"] for e in employees if rng.random() < 0.08}
    for e in employees:
        hire = date.fromisoformat(e["hire_date"])
        term = date.fromisoformat(e["termination_date"]) if e["termination_date"] else None
        day = att_start
        while day <= SNAPSHOT_DATE:
            if day.weekday() < 5 and day >= hire and not (term and day > term):
                leave = None
                if day in holidays:
                    status, hours = "Holiday", 0.0
                else:
                    p_abs = 0.06 if e["employee_id"] in absence_prone else 0.012
                    r = rng.random()
                    if r < p_abs:
                        status, hours = "Absent", 0.0
                    elif r < p_abs + 0.045:
                        status, hours = "Leave", 0.0
                        leave = rng.choices(["Annual", "Sick", "Personal"], weights=[60, 30, 10])[0]
                    else:
                        status = "Present"
                        base_h = 4.0 if e["employment_type"] == "Part-time" else 8.0
                        hours = round(base_h + rng.choice([0, 0, 0, 0.5, 1, -0.5]), 1)
                att_id += 1
                attendance.append((att_id, e["employee_id"], day.isoformat(), status, hours, leave))
            day += timedelta(days=1)

    # --------------------------------------------------- performance reviews
    rev_id = 0
    cycles = [("2024-H2", date(2024, 12, 15)), ("2025-H1", date(2025, 6, 15)),
              ("2025-H2", date(2025, 12, 15)), ("2026-H1", date(2026, 6, 15))]
    for e in employees:
        if e["manager_id"] is None:
            continue
        hire = date.fromisoformat(e["hire_date"])
        term = date.fromisoformat(e["termination_date"]) if e["termination_date"] else None
        for cycle, rdate in cycles:
            if hire <= rdate - timedelta(days=90) and not (term and term < rdate):
                rev_id += 1
                rating = rng.choices([1, 2, 3, 4, 5], weights=[3, 10, 45, 30, 12])[0]
                reviews.append((rev_id, e["employee_id"], e["manager_id"], cycle,
                                (rdate + timedelta(days=rng.randint(0, 20))).isoformat(), rating))

    # -------------------------------------------------------- leave balances
    used_by: dict[tuple[int, str], int] = {}
    for a in attendance:
        if a[3] == "Leave":
            used_by[(a[1], a[5])] = used_by.get((a[1], a[5]), 0) + 1
    for e in employees:
        if e["status"] != "Active" or e["employment_type"] == "Contract":
            continue
        for ltype, entitled in (("Annual", 20.0), ("Sick", 10.0), ("Personal", 3.0)):
            used = min(entitled, float(used_by.get((e["employee_id"], ltype), 0)) + rng.choice([0, 1, 2, 3, 5]))
            balances.append((e["employee_id"], ltype, entitled, used, entitled - used))

    # ----------------------------------------------------------------- write
    con = sqlite3.connect(out_path)
    con.executescript(SCHEMA)
    con.executemany("INSERT INTO companies VALUES (?,?,?,?,?)", companies)
    con.executemany("INSERT INTO departments VALUES (?,?,?,?)", departments)
    con.executemany(
        "INSERT INTO employees VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [(e["employee_id"], e["company_id"], e["department_id"], e["first_name"], e["last_name"],
          e["email"], e["job_title"], e["job_level"], e["manager_id"], e["employment_type"],
          e["work_state"], e["hire_date"], e["termination_date"], e["termination_reason"], e["status"])
         for e in employees],
    )
    con.executemany("INSERT INTO salaries VALUES (?,?,?,?,?)", salaries)
    con.executemany("INSERT INTO payroll_runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", payroll)
    con.executemany("INSERT INTO payroll_exceptions VALUES (?,?,?,?,?,?,?,?,?)", exceptions)
    con.executemany("INSERT INTO attendance VALUES (?,?,?,?,?,?)", attendance)
    con.executemany("INSERT INTO performance_reviews VALUES (?,?,?,?,?,?)", reviews)
    con.executemany("INSERT INTO leave_balances VALUES (?,?,?,?,?)", balances)
    con.commit()
    con.close()
    return out_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the dummy HR & payroll database")
    parser.add_argument("--out", default=str(DEFAULT_PATH), help="output .db path")
    args = parser.parse_args()
    path = generate(args.out)
    con = sqlite3.connect(path)
    print(f"Created {path}")
    for (table,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
        count = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table:<20} {count:>7,} rows")
    con.close()


if __name__ == "__main__":
    main()
