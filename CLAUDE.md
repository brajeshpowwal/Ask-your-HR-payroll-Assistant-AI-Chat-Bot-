# Instructions for Claude Code

This repo is **TalkToData**, a text-to-SQL assistant over a dummy HR & payroll SQLite database.
Read `PLAN.md` for the full plan and `docs/INTERVIEW_GUIDE.md` for how everything works.

## Rules
- All data is dummy. Never add real company, client or employee names, real exports, or screenshots of real systems.
- Never put API keys or secrets in code. Settings come from `.env` via `src/config.py`.
- The database must stay read-only. Any new query path must go through `src/sql_guard.py` and `src/db.py`.
- Python 3.11+, type hints, small functions, docstrings that explain *why*.
- Keep `data/examples.yaml` and `eval/questions.jsonl` different: never copy eval questions into examples.
- Run `ruff check .`, `mypy` and `python -m pytest` before every commit; all must pass.

## Map
- `data/generate_data.py`: builds `data/hr_payroll.db` (seeded, repeatable)
- `data/schema_docs.yaml`, `data/glossary.yaml`, `data/examples.yaml`: what the LLM is told
- `src/agent.py`: LangGraph flow (select tables, retrieve examples, generate, validate, execute, answer)
- `src/sql_guard.py`: SELECT-only, allow-list, LIMIT
- `src/db.py`: read-only connection, timeout
- `app/streamlit_app.py`: chat UI
- `eval/run_eval.py`: execution-accuracy benchmark
