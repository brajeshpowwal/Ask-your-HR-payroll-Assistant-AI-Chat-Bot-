import pytest

from src.db import QueryError, run_query


def test_runs_select(db_path):
    df = run_query("SELECT COUNT(*) AS n FROM companies", db_path)
    assert int(df.iloc[0, 0]) == 4


def test_connection_is_read_only(db_path):
    with pytest.raises(QueryError):
        run_query("DELETE FROM companies", db_path)
    assert int(run_query("SELECT COUNT(*) FROM companies", db_path).iloc[0, 0]) == 4


def test_slow_query_is_stopped(db_path):
    endless = "WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM c) SELECT COUNT(*) FROM c"
    with pytest.raises(QueryError, match="longer than"):
        run_query(endless, db_path, timeout_s=0.5)


def test_bad_sql_gives_clean_message(db_path):
    with pytest.raises(QueryError, match="no such column"):
        run_query("SELECT nope FROM companies", db_path)
