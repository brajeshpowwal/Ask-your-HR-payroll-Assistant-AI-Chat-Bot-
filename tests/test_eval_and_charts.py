import pandas as pd

from eval.run_eval import results_match
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


def test_chart_choice():
    assert choose_chart(pd.DataFrame({"total": [5]})).kind == "kpi"
    assert choose_chart(pd.DataFrame({"pay_month": ["2026-01", "2026-02"], "gross": [1.0, 2.0]})).kind == "line"
    assert choose_chart(pd.DataFrame({"company": ["A", "B"], "n": [1, 2]})).kind == "bar"
    assert choose_chart(pd.DataFrame({"name": ["A"], "title": ["B"]})).kind == "none"
