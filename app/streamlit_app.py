"""TalkToData: chat with an HR & payroll database in plain English.

Run:  streamlit run app/streamlit_app.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Streamlit Cloud keeps keys in "Secrets"; copy them into env vars before config loads.
try:
    for key, value in st.secrets.items():
        if isinstance(value, str):
            os.environ.setdefault(key, value)
except Exception:  # no secrets file locally, that's fine
    pass

from app.ui import TYPING_HTML, hero_html, page_style, style_figure, word_stream  # noqa: E402
from src.agent import AgentResult, SQLAgent  # noqa: E402
from src.charts import choose_chart  # noqa: E402
from src.config import DEFAULT_MODELS, get_settings  # noqa: E402
from src.db import ensure_database, run_query  # noqa: E402
from src.llm_factory import LLMConfigError, get_llm  # noqa: E402

SAMPLE_QUESTIONS = [
    "How many active employees does each company have?",
    "Show total gross payroll by month for 2026",
    "Which open payroll exceptions are older than 14 days?",
    "Attrition rate by company, last 12 months",
    "Who are the top 5 earners at Brightwave Solutions?",
    "Which department has the highest absenteeism rate?",
]

st.set_page_config(page_title="TalkToData · HR & payroll assistant", page_icon="🤖", layout="centered")


# ------------------------------------------------------------------ setup
@st.cache_resource(show_spinner="Preparing the demo database…")
def load_database() -> Path:
    return ensure_database(get_settings().db_path)


@st.cache_resource(show_spinner=False)
def load_agent(provider: str, model: str) -> SQLAgent:
    settings = get_settings(provider=provider, model=model)
    return SQLAgent(get_llm(settings), settings)


@st.cache_data(show_spinner=False)
def table_counts(db_path: str) -> list[tuple[str, int]]:
    s = get_settings()
    return [(t, int(run_query(f"SELECT COUNT(*) AS n FROM {t}", Path(db_path))["n"].sum()))
            for t in s.allowed_tables]


db_path = load_database()
settings = get_settings()
state = st.session_state
state.setdefault("messages", [])
state.setdefault("asked", 0)

# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.subheader("Model")
    providers = list(DEFAULT_MODELS)
    provider = st.selectbox("Provider", providers, index=providers.index(settings.provider)
                            if settings.provider in providers else 0)
    default_model = settings.model if provider == settings.provider and settings.model else DEFAULT_MODELS[provider]
    model = st.text_input("Model name", value=default_model,
                          help="Providers retire models. If this one fails, paste a current model name.")

    if state.messages:  # on an empty chat the samples sit on the page itself (see below)
        st.subheader("Try a question")
        for q in SAMPLE_QUESTIONS:
            if st.button(q, width="stretch", key=f"side-{q}"):
                state.pending = q

    left = max(0, settings.max_questions_per_session - state.asked)
    st.caption(f"{left} questions left in this session (demo limit).")
    if st.button("Clear chat", width="stretch"):
        state.messages, state.asked = [], 0
        st.rerun()

    with st.expander("About the data"):
        st.write("Fictional HR & payroll data for four made-up companies, generated with Faker. "
                 "Today's date in the data is 2026-10-31.")
        for table, n in table_counts(str(db_path)):
            st.write(f"`{table}` · {n:,} rows")

# ------------------------------------------------------------------- main
counts = table_counts(str(db_path))
st.markdown(page_style(), unsafe_allow_html=True)
st.markdown(hero_html(model, len(counts), sum(n for _, n in counts)), unsafe_allow_html=True)

with st.chat_message("assistant"):  # the greeting opens every conversation, like a real assistant
    st.markdown("Hi! I'm your HR & payroll data assistant. Ask me about headcount, payroll, attrition, "
                "exceptions, attendance or reviews for the four demo companies. I only read data, never change it.")

if not state.messages and not state.get("pending"):
    # Phones collapse the sidebar, so new visitors get the samples on the page.
    st.markdown('<div class="ttd-try">Try one of these</div>', unsafe_allow_html=True)
    with st.container(key="samples"):  # CSS lays these out as a card grid; labels wrap instead of being cut
        for q in SAMPLE_QUESTIONS:
            if st.button(q, width="stretch", key=f"main-{q}"):
                state.pending = q
                st.rerun()  # redraw without the cards, so the chat starts right under the greeting


def render_result(msg: dict, stream: bool = False) -> None:
    # Two trailing spaces make Markdown keep the model's single line breaks (lists per company etc.).
    text = msg["answer"].replace("\n", "  \n")
    if stream:  # only a fresh answer is typed out; history redraws instantly
        st.write_stream(word_stream(text))
    else:
        st.markdown(text)
    df = msg.get("data")
    if msg.get("status") != "ok" or df is None:
        return
    chart = choose_chart(df)
    if chart.kind == "kpi":
        st.metric(chart.kpi_label, chart.kpi_value)
    elif chart.figure is not None:
        st.plotly_chart(style_figure(chart.figure), width="stretch", theme=None, key=f"chart-{msg['id']}")
    if chart.kind != "kpi":
        with st.expander(f"Data · {len(df):,} rows", expanded=chart.kind == "none"):
            st.dataframe(df, width="stretch", hide_index=True)
            st.download_button("Download CSV", df.to_csv(index=False), "result.csv", "text/csv",
                               key=f"dl-{msg['id']}")
    with st.expander("SQL used"):
        st.code(msg["sql"], language="sql")
    with st.expander("How I got this"):
        for step in msg.get("steps", []):
            st.write("• " + step)
        st.caption(f"{msg.get('llm_calls', 0)} model calls · {msg.get('attempts', 0)} SQL attempt(s) · "
                   f"{msg.get('seconds', 0)} s")


for msg in state.messages:
    with st.chat_message(msg["role"]):
        if msg["role"] == "user":
            st.markdown(msg["content"])
        else:
            render_result(msg)

question = st.chat_input("Ask about your HR & payroll data…")
if state.get("pending"):
    question, state.pending = state.pending, None

if question:
    if state.asked >= settings.max_questions_per_session:
        st.warning("You've reached the demo limit for this session. "
                   "Clear the chat or run it locally for unlimited use.")
        st.stop()
    try:
        agent = load_agent(provider, model)
    except LLMConfigError as exc:
        st.error(f"The model isn't set up yet: {exc}")
        st.stop()

    state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    history = [{"question": m["question"], "sql": m.get("sql", "")}
               for m in state.messages if m["role"] == "assistant" and m.get("status") == "ok"]
    with st.chat_message("assistant"):
        typing = st.empty()
        typing.markdown(TYPING_HTML, unsafe_allow_html=True)
        try:
            result: AgentResult = agent.ask(question, history=history)
        except Exception as exc:  # provider outage, rate limit, bad model name…
            result = AgentResult(question=question, status="failed",
                                 answer=f"The model call failed: {exc}. Check the model name and API key, "
                                        "or try again in a minute (free tiers have rate limits).")
        typing.empty()
        msg = {"role": "assistant", "id": len(state.messages), "question": question,
               "answer": result.answer, "status": result.status, "sql": result.sql,
               "data": result.data, "steps": result.steps, "attempts": result.attempts,
               "llm_calls": result.llm_calls, "seconds": result.seconds}
        render_result(msg, stream=True)
    state.messages.append(msg)
    state.asked += 1
