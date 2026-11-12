"""UI tests with Streamlit's AppTest: render the page without a browser or a model call."""
import sys
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


def test_page_has_hero_style_and_greeting():
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    html = "\n".join(m.value for m in at.markdown)
    assert "ttd-hero" in html and "<style>" in html
    assert len(at.chat_message) == 1  # the assistant greets a new visitor
    assert "data assistant" in at.chat_message[0].markdown[0].value


def test_hero_escapes_the_typed_model_name():
    """The model name is free text from the sidebar; it must never reach the page as HTML."""
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.sidebar.text_input[0].set_value("<img src=x onerror=alert(1)>").run()
    html = "\n".join(m.value for m in at.markdown)
    assert "<img src=x" not in html and "&lt;img src=x" in html


def test_app_survives_stale_project_modules_after_a_deploy(monkeypatch):
    """Streamlit Cloud reruns the new script but kept the old src.config in memory (live ImportError)."""
    import types
    monkeypatch.setitem(sys.modules, "src.config", types.ModuleType("src.config"))  # old copy, no new names
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
    assert hasattr(sys.modules["src.config"], "apply_secrets")


def test_word_stream_rebuilds_the_answer_exactly():
    from app.ui import word_stream
    text = "Brightwave: 168  \nCedarline:  143\n\n- one"
    assert "".join(word_stream(text, delay_s=0)) == text


def test_charts_get_the_neon_look():
    import pandas as pd
    import plotly.express as px

    from app.ui import style_figure
    fig = style_figure(px.bar(pd.DataFrame({"company": ["A", "B"], "n": [3, 5]}), x="company", y="n"))
    assert fig.layout.paper_bgcolor == "rgba(0,0,0,0)" and fig.layout.barcornerradius == 8
    assert list(fig.data[0].marker.color) == [3, 5]  # bars shaded by value
