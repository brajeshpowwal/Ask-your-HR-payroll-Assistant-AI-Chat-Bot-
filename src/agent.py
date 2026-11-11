"""The text-to-SQL agent, built as a LangGraph state machine.

    select_tables -> retrieve_examples -> generate_sql -> validate -> execute -> answer
                                              ^              |          |
                                              +---- retry ---+----------+   (max N times)

Each node is a small function that reads the shared state and returns the
fields it changed. LangGraph wires them together and handles the loop.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, TypedDict

import pandas as pd
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from src import prompts
from src.config import Settings, get_settings
from src.db import QueryError, run_query
from src.examples_store import ExampleStore
from src.schema import SchemaInfo
from src.sql_guard import UnsafeSQLError, validate_sql


class AgentState(TypedDict, total=False):
    question: str
    history: list[dict]
    tables: list[str]
    examples: list[dict]
    sql: str
    error: str | None
    attempts: int
    result: pd.DataFrame | None
    answer: str
    status: str            # ok | clarify | cannot_answer | failed
    llm_calls: int
    steps: list[str]


@dataclass
class AgentResult:
    question: str
    answer: str
    status: str
    sql: str = ""
    data: pd.DataFrame | None = None
    tables: list[str] = field(default_factory=list)
    attempts: int = 0
    llm_calls: int = 0
    seconds: float = 0.0
    steps: list[str] = field(default_factory=list)


# ----------------------------------------------------------------- helpers
def _text(message: Any) -> str:
    """Get plain text from a model reply (some providers return a list of parts)."""
    content = getattr(message, "content", message)
    if isinstance(content, list):
        content = "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in content)
    return str(content).strip()


def extract_sql(text: str) -> str:
    match = re.search(r"```(?:sql|sqlite)?\s*(.*?)```", text, flags=re.S | re.I)
    if match:
        return match.group(1).strip()
    start = re.search(r"\b(WITH|SELECT)\b", text, flags=re.I)  # model forgot the fence
    return text[start.start():].strip() if start else text.strip()


def _history_text(history: list[dict]) -> str:
    if not history:
        return "(none)"
    lines = []
    for turn in history[-3:]:
        lines.append(f"Q: {turn.get('question', '')}")
        if turn.get("sql"):
            lines.append(f"SQL: {turn['sql']}")
    return "\n".join(lines)


ROWS_SHOWN_TO_MODEL = 30  # keeps the explain prompt small; the user still sees every row


def build_answer_prompt(question: str, df: pd.DataFrame, max_rows: int, snapshot: str) -> str:
    """Tell the model how much of the result it sees, so it never summarises hidden rows."""
    row_info = f"{len(df)} rows"
    if len(df) > ROWS_SHOWN_TO_MODEL:
        row_info += f", showing the first {ROWS_SHOWN_TO_MODEL}"
    if len(df) >= max_rows:
        row_info += ", cut off at the row limit"
    result = df.head(ROWS_SHOWN_TO_MODEL).to_csv(index=False, lineterminator="\n") if not df.empty else "(no rows)"
    return prompts.ANSWER_USER.format(question=question, snapshot=snapshot, row_info=row_info, result=result)


# ------------------------------------------------------------------- agent
class SQLAgent:
    def __init__(self, llm: BaseChatModel, settings: Settings | None = None):
        self.llm = llm
        self.settings = settings or get_settings()
        self.schema = SchemaInfo(self.settings)
        self.examples = ExampleStore(self.settings)
        self.graph = self._build_graph()

    def _ask(self, system: str, user: str) -> str:
        reply = self.llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
        return _text(reply)

    # ---- nodes
    def select_tables(self, state: AgentState) -> AgentState:
        reply = self._ask(prompts.SELECT_TABLES_SYSTEM, prompts.SELECT_TABLES_USER.format(
            catalog=self.schema.table_catalog(),
            history=_history_text(state.get("history", [])),
            question=state["question"]))
        tables: list[str] = []
        match = re.search(r"\[.*?\]", reply, flags=re.S)
        if match:
            try:
                tables = [t for t in json.loads(match.group(0)) if t in self.schema.tables]
            except (json.JSONDecodeError, TypeError):
                tables = []
        if not tables:  # fall back to the full schema rather than fail
            tables = list(self.schema.tables)
        return {"tables": tables, "llm_calls": state.get("llm_calls", 0) + 1,
                "steps": state.get("steps", []) + [f"Picked tables: {', '.join(tables)}"]}

    def retrieve_examples(self, state: AgentState) -> AgentState:
        found = self.examples.search(state["question"], k=self.settings.num_examples)
        return {"examples": [{"question": e.question, "sql": e.sql} for e in found],
                "steps": state.get("steps", []) + [f"Retrieved {len(found)} similar examples"]}

    def generate_sql(self, state: AgentState) -> AgentState:
        attempts = state.get("attempts", 0)
        retry_block = ""
        tables = state.get("tables")
        if state.get("error"):
            retry_block = prompts.RETRY_BLOCK.format(previous_sql=state.get("sql", ""), error=state["error"])
            tables = None  # on a retry show the full schema in case a table was missed
        examples = "\n\n".join(f"Q: {e['question']}\n```sql\n{e['sql']}\n```" for e in state.get("examples", []))
        reply = self._ask(prompts.GENERATE_SQL_SYSTEM, prompts.GENERATE_SQL_USER.format(
            schema=self.schema.schema_prompt(tables),
            glossary=self.schema.glossary_prompt(),
            examples=examples or "(none)",
            history=_history_text(state.get("history", [])),
            question=state["question"],
            retry_block=retry_block))
        update: AgentState = {"attempts": attempts + 1, "llm_calls": state.get("llm_calls", 0) + 1}
        steps = state.get("steps", [])
        if not reply:
            # Nothing to fix: retrying an empty reply only repeats slow model calls.
            return {**update, "status": "failed",
                    "answer": ("The model returned an empty reply, so no query was run. "
                               "Please rephrase the question. Note that this assistant can only read data."),
                    "steps": steps + ["Model returned an empty reply"]}
        if reply.upper().startswith("CLARIFY:"):
            return {**update, "status": "clarify", "answer": reply.split(":", 1)[1].strip(),
                    "steps": steps + ["Asked a clarifying question"]}
        if reply.upper().startswith("CANNOT_ANSWER:"):
            return {**update, "status": "cannot_answer",
                    "answer": "I can't answer that from this database: " + reply.split(":", 1)[1].strip(),
                    "steps": steps + ["Question cannot be answered from the data"]}
        label = "Wrote SQL" if attempts == 0 else f"Fixed SQL (attempt {attempts + 1})"
        return {**update, "sql": extract_sql(reply), "error": None, "status": "running",
                "steps": steps + [label]}

    def validate(self, state: AgentState) -> AgentState:
        try:
            checked = validate_sql(state["sql"], self.settings.allowed_tables, self.settings.max_rows)
            return {"sql": checked.sql, "error": None,
                    "steps": state.get("steps", []) + ["Passed the safety guard"]}
        except UnsafeSQLError as exc:
            return {"error": f"Rejected by safety guard: {exc}",
                    "steps": state.get("steps", []) + [f"Guard rejected: {exc}"]}

    def execute(self, state: AgentState) -> AgentState:
        try:
            df = run_query(state["sql"], self.settings.db_path, self.settings.query_timeout_s)
            return {"result": df, "error": None,
                    "steps": state.get("steps", []) + [f"Ran query: {len(df)} rows"]}
        except QueryError as exc:
            return {"error": f"Database error: {exc}",
                    "steps": state.get("steps", []) + [f"Database error: {exc}"]}

    def answer(self, state: AgentState) -> AgentState:
        df = state.get("result")
        df = df if df is not None else pd.DataFrame()
        text = self._ask(prompts.ANSWER_SYSTEM, build_answer_prompt(
            state["question"], df, self.settings.max_rows, self.schema.snapshot_date()))
        return {"answer": text, "status": "ok", "llm_calls": state.get("llm_calls", 0) + 1,
                "steps": state.get("steps", []) + ["Explained the result"]}

    def give_up(self, state: AgentState) -> AgentState:
        return {"status": "failed",
                "answer": ("I couldn't build a working query for that after "
                           f"{state.get('attempts', 0)} attempts. Try rephrasing or being more specific. "
                           f"Last error: {state.get('error')}")}

    # ---- routing
    def _after_generate(self, state: AgentState) -> str:
        return "validate" if state.get("status") == "running" else END

    def _after_check(self, state: AgentState) -> str:
        if not state.get("error"):
            return "ok"
        return "retry" if state.get("attempts", 0) < self.settings.max_retries else "give_up"

    def _build_graph(self):
        g = StateGraph(AgentState)
        g.add_node("select_tables", self.select_tables)
        g.add_node("retrieve_examples", self.retrieve_examples)
        g.add_node("generate_sql", self.generate_sql)
        g.add_node("validate", self.validate)
        g.add_node("execute", self.execute)
        g.add_node("answer", self.answer)
        g.add_node("give_up", self.give_up)
        g.add_edge(START, "select_tables")
        g.add_edge("select_tables", "retrieve_examples")
        g.add_edge("retrieve_examples", "generate_sql")
        g.add_conditional_edges("generate_sql", self._after_generate, {"validate": "validate", END: END})
        g.add_conditional_edges("validate", self._after_check,
                                {"ok": "execute", "retry": "generate_sql", "give_up": "give_up"})
        g.add_conditional_edges("execute", self._after_check,
                                {"ok": "answer", "retry": "generate_sql", "give_up": "give_up"})
        g.add_edge("answer", END)
        g.add_edge("give_up", END)
        return g.compile()

    # ---- public API
    def ask(self, question: str, history: list[dict] | None = None) -> AgentResult:
        start = time.perf_counter()
        state: AgentState = self.graph.invoke(
            {"question": question.strip(), "history": history or [], "attempts": 0,
             "llm_calls": 0, "steps": []},
            config={"recursion_limit": 30})
        return AgentResult(
            question=question,
            answer=state.get("answer", ""),
            status=state.get("status", "failed"),
            sql=state.get("sql", "") if state.get("status") in ("ok", "failed") else "",
            data=state.get("result"),
            tables=state.get("tables", []),
            attempts=state.get("attempts", 0),
            llm_calls=state.get("llm_calls", 0),
            seconds=round(time.perf_counter() - start, 2),
            steps=state.get("steps", []),
        )
