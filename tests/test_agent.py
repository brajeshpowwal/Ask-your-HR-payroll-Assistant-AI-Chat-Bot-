"""Agent tests use a fake LLM with scripted replies, so they are free, fast and offline."""
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from src.agent import SQLAgent, extract_sql

GOOD_SQL = ("```sql\nSELECT c.company_name, COUNT(*) AS active_headcount FROM employees e "
            "JOIN companies c ON c.company_id = e.company_id WHERE e.status = 'Active' "
            "GROUP BY c.company_name\n```")


def make_agent(settings, replies):
    return SQLAgent(FakeListChatModel(responses=replies), settings)


def test_happy_path(settings):
    agent = make_agent(settings, ['["employees", "companies"]', GOOD_SQL, "Brightwave leads."])
    res = agent.ask("Active headcount by company?")
    assert res.status == "ok"
    assert len(res.data) == 4
    assert res.attempts == 1 and res.llm_calls == 3
    assert res.answer == "Brightwave leads."


def test_self_corrects_after_database_error(settings):
    agent = make_agent(settings, ['["employees"]', "```sql\nSELECT company FROM employees\n```",
                                  GOOD_SQL, "Fixed."])
    res = agent.ask("Active headcount by company?")
    assert res.status == "ok"
    assert res.attempts == 2
    assert any("no such column" in s for s in res.steps)


def test_guard_rejection_triggers_retry(settings):
    agent = make_agent(settings, ['["employees"]', "DROP TABLE employees", GOOD_SQL, "Done."])
    res = agent.ask("Remove everyone")
    assert res.status == "ok" and res.attempts == 2


def test_gives_up_after_max_retries(settings):
    agent = make_agent(settings, ['["employees"]'] + ["SELECT nope FROM employees"] * 5)
    res = agent.ask("Something impossible")
    assert res.status == "failed"
    assert res.attempts == settings.max_retries


def test_clarify_and_cannot_answer(settings):
    res = make_agent(settings, ['["employees"]', "CLARIFY: Which year?"]).ask("Show leavers")
    assert res.status == "clarify" and res.answer == "Which year?"
    res = make_agent(settings, ['["employees"]', "CANNOT_ANSWER: no gender data"]).ask("Gender pay gap?")
    assert res.status == "cannot_answer" and "gender" in res.answer


def test_empty_model_reply_stops_without_retries(settings):
    """An empty reply is not a SQL error to fix; retrying only wastes slow model calls."""
    agent = make_agent(settings, ['["employees"]', "   ", GOOD_SQL, "should not be used"])
    res = agent.ask("Delete all employees")
    assert res.status == "failed"
    assert res.attempts == 1 and res.llm_calls == 2
    assert res.sql == "" and res.data is None
    assert "empty reply" in res.answer


def test_bad_table_list_falls_back_to_full_schema(settings):
    agent = make_agent(settings, ["I think you need employees", GOOD_SQL, "ok"])
    res = agent.ask("Active headcount by company?")
    assert res.status == "ok" and len(res.tables) == len(settings.allowed_tables)


def test_extract_sql_variants():
    assert extract_sql("```sql\nSELECT 1\n```") == "SELECT 1"
    assert extract_sql("Here you go: SELECT 1") == "SELECT 1"
    assert extract_sql("```\nWITH a AS (SELECT 1) SELECT * FROM a\n```").startswith("WITH")
