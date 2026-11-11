import pandas as pd
import pytest

from eval.run_eval import ask_with_retry, results_match
from src.charts import choose_chart


def test_results_match_ignores_order_names_and_extra_columns():
    expected = pd.DataFrame({"company": ["A", "B"], "n": [10, 20]})
    predicted = pd.DataFrame({"headcount": [20, 10], "company_name": ["B", "A"], "extra": [1, 2]})
    assert results_match(expected, predicted)


def test_results_match_detects_wrong_values():
    expected = pd.DataFrame({"n": [10, 20]})
    assert not results_match(expected, pd.DataFrame({"n": [10, 21]}))
    assert not results_match(expected, pd.DataFrame({"n": [10]}))
    assert not results_match(expected, None)


class _FlakyAgent:
    """Fails with a rate-limit error a few times, then answers."""

    def __init__(self, failures: int, message: str = "[429] Too Many Requests"):
        self.failures, self.message, self.calls = failures, message, 0

    def ask(self, question):
        self.calls += 1
        if self.calls <= self.failures:
            raise RuntimeError(self.message)
        return f"answer to {question}"


def test_ask_with_retry_waits_out_rate_limits():
    agent = _FlakyAgent(failures=2)
    assert ask_with_retry(agent, "q", attempts=3, wait_s=0) == "answer to q"
    assert agent.calls == 3


def test_ask_with_retry_gives_up_and_does_not_retry_other_errors():
    with pytest.raises(RuntimeError, match="429"):
        ask_with_retry(_FlakyAgent(failures=5), "q", attempts=3, wait_s=0)
    agent = _FlakyAgent(failures=1, message="model not found")
    with pytest.raises(RuntimeError, match="not found"):
        ask_with_retry(agent, "q", attempts=3, wait_s=0)
    assert agent.calls == 1


def test_chart_choice():
    assert choose_chart(pd.DataFrame({"total": [5]})).kind == "kpi"
    assert choose_chart(pd.DataFrame({"pay_month": ["2026-01", "2026-02"], "gross": [1.0, 2.0]})).kind == "line"
    assert choose_chart(pd.DataFrame({"company": ["A", "B"], "n": [1, 2]})).kind == "bar"
    assert choose_chart(pd.DataFrame({"name": ["A"], "title": ["B"]})).kind == "none"
