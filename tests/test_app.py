"""UI tests with Streamlit's AppTest: render the page without a browser or a model call."""
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parent.parent / "app" / "streamlit_app.py")
SAMPLE = "How many active employees does each company have?"


def _labels(buttons) -> list[str]:
    return [b.label for b in buttons]


def test_empty_chat_shows_sample_questions_in_main_area():
    """Phones hide the sidebar, so a new visitor must see the samples on the page itself."""
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    assert SAMPLE in _labels(at.main.button)
    assert SAMPLE not in _labels(at.sidebar.button)


def test_answer_keeps_the_model_line_breaks():
    """Markdown joins single newlines, which ran a per-company list into one line."""
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["messages"] = [{"role": "assistant", "id": 1, "question": "q", "status": "failed",
                                     "answer": "Brightwave: 168\nCedarline: 143", "sql": ""}]
    at.run()
    assert not at.exception
    assert "Brightwave: 168  \nCedarline: 143" in [m.value for m in at.markdown]


def test_samples_move_to_sidebar_once_chat_has_messages():
    at = AppTest.from_file(APP, default_timeout=60)
    at.session_state["messages"] = [{"role": "user", "content": "hello"}]
    at.run()
    assert not at.exception
    assert SAMPLE not in _labels(at.main.button)
    assert SAMPLE in _labels(at.sidebar.button)
