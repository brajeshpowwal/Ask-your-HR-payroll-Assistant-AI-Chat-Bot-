# TalkToData: chat with your HR & payroll data in plain English

[![tests](https://github.com/brajeshpowwal/Ask-your-HR-payroll-Assistant-AI-Chat-Bot-/actions/workflows/ci.yml/badge.svg)](https://github.com/brajeshpowwal/Ask-your-HR-payroll-Assistant-AI-Chat-Bot-/actions/workflows/ci.yml)

Ask a question like *"Which open payroll exceptions are older than 14 days?"* and the assistant writes safe SQL, runs it on the database, and replies with a plain-English answer, a chart, the data, and the exact SQL it used.

Built with **Python, LangChain, LangGraph, SQLite and Streamlit**. Works with free LLMs (NVIDIA, Groq, Google Gemini, or a local Ollama model) and with Claude, and from Claude Desktop through an MCP server. Total running cost: **$0**.

> **Live demo:** _add your Streamlit link here_ · **Video walkthrough:** _add your LinkedIn/YouTube link here_

<!-- Add a demo GIF: record 20–30 seconds of the app and save it as docs/demo.gif -->
<!-- ![Demo](docs/demo.gif) -->

All data in this project is **fictional**: four made-up companies and ~635 made-up employees generated with Faker.

---

## Why this project

Business teams wait days for simple data answers because only analysts can write SQL. This assistant lets anyone ask in plain English, while staying **safe** (it can never change data), **transparent** (it always shows its SQL), and **measured** (it has a 50-question accuracy benchmark).

## What it does

- **Plain-English to SQL** with a LangGraph agent: picks the relevant tables, finds similar solved examples, writes the query, checks it, runs it, explains it
- **Self-correction**: if the SQL fails or is rejected, the error goes back to the model to fix (up to 3 tries)
- **Four safety layers**: read-only connection, SQL parser that allows only one `SELECT`, table allow-list, row limit + timeout
- **Business glossary** so "attrition", "headcount", "open exception" follow company definitions
- **Follow-up questions** ("now only for Cedarline Health") using conversation history
- **Auto charts**: KPI card, line chart for trends, bar chart for comparisons; CSV download
- **Chat-style interface**: animated assistant header, typing indicator while it works, answers typed out word by word, sample-question cards, dark "night console" theme
- **Swap the LLM with one setting**: Groq, Gemini, Ollama (local), Claude, NVIDIA
- **Evaluation**: execution accuracy on 50 questions (easy / medium / hard)
- **72 automated tests** run on every push with GitHub Actions

## How it works

```mermaid
flowchart TD
    U[User asks in plain English] --> A
    subgraph Agent [LangGraph agent]
      A[1. Pick relevant tables] --> B[2. Retrieve similar examples]
      B --> C[3. LLM writes the SQL]
      C --> D{4. Safety guard<br/>single SELECT, allow-list, LIMIT}
      D -- rejected --> C
      D -- ok --> E[5. Run on read-only SQLite<br/>with timeout]
      E -- error --> C
      E -- rows --> F[6. LLM explains the result]
    end
    F --> O[Answer + chart + data + SQL in chat]
    S[(schema_docs.yaml<br/>glossary.yaml)] -.-> A
    X[(examples.yaml<br/>TF-IDF search)] -.-> B
    DB[(hr_payroll.db)] -.-> E
```

The model is called 3 times for a normal question: pick tables, write SQL, explain the result. It only ever sees the schema, a few sample rows and the result of its own query, never the full tables.

## The dummy database

| Table | Rows | What it holds |
|---|---|---|
| companies | 4 | Brightwave Solutions, Cedarline Health, Northpeak Logistics, Orbitron Retail |
| departments | 24 | 6 departments per company with cost centers |
| employees | 635 | Hires, leavers, job levels, manager hierarchy, work state |
| salaries | 2,111 | Salary history: new hire, annual merit, promotion |
| payroll_runs | 23,891 | Two years of biweekly payroll (gross, tax, benefits, net, employer tax) |
| payroll_exceptions | 431 | Payroll issues with status and resolution dates |
| attendance | 35,186 | Daily attendance for the last 90 days |
| performance_reviews | 1,706 | Half-yearly ratings 1–5 |
| leave_balances | 1,506 | Annual, sick and personal leave balances |

The data has realistic problems planted in it (duplicate payments, overtime spikes, slow-to-resolve exceptions) so there are interesting things to find. "Today" in the data is **2026-10-31**, so answers never change with the real date.

## Quick start

```bash
git clone https://github.com/brajeshpowwal/Ask-your-HR-payroll-Assistant-AI-Chat-Bot-.git
cd Ask-your-HR-payroll-Assistant-AI-Chat-Bot-
python -m venv .venv
# Windows: .venv\Scripts\activate     macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env               # macOS/Linux: cp .env.example .env
# open .env, set LLM_PROVIDER and paste a free key (NVIDIA: https://build.nvidia.com, Groq: https://console.groq.com)
python data/generate_data.py
streamlit run app/streamlit_app.py
```

Full step-by-step guide for Windows and VS Code: [docs/HOW_TO_RUN.md](docs/HOW_TO_RUN.md).

## Accuracy

Run the benchmark yourself:

```bash
python eval/run_eval.py                        # uses LLM_PROVIDER from .env
python eval/run_eval.py --provider gemini      # compare another model
python eval/run_eval.py --per-difficulty 4     # quick balanced sample (12 questions)
```

Results on the 50 questions (November 2026, NVIDIA free tier, thinking off):

| Provider | Model | Execution accuracy | Easy (15) | Medium (20) | Hard (15) | Valid SQL | Avg retries | Avg seconds |
|---|---|---|---|---|---|---|---|---|
| nvidia | nemotron-3.5-lightning-30b-a3b | **84%** | 100% | 95% | 53% | 100% | 0.04 | 11.9 |

- **Results vary between runs.** Three clean full runs after tuning scored 78%, 82% and 84%; the table shows the latest. Runs that hit provider rate limits are not counted.
- **Before tuning** the same model scored 78% (hard questions 47%). Tuning added business rules to `data/glossary.yaml` and few-shot examples to `data/examples.yaml`, based on the failed questions; a test checks that no example is a copy or near-copy of an eval question.
- **Benchmark change:** three gold queries (q44, q45, q49) returned extra columns the question did not ask for (a count, a job title). Those columns were removed; the answer logic is unchanged.
- **Thinking on** (the model reasons before replying) was slower (57 s per question) and, on a 12-question sample, less accurate, so it is off by default (`LLM_THINKING`).
- **Latency** is about 10–12 s per question with three model calls; the 5 s goal is not met yet.

*Execution accuracy* = the assistant's result table has the same values as a hand-written correct query (row order, column names and extra columns are ignored).

## Project structure

```
├── app/streamlit_app.py     chat interface
├── src/
│   ├── agent.py             LangGraph agent (the brain)
│   ├── sql_guard.py         safety checks on generated SQL
│   ├── db.py                read-only execution with timeout
│   ├── schema.py            schema + business docs for the prompt
│   ├── examples_store.py    finds similar example questions (TF-IDF)
│   ├── prompts.py           all prompt templates
│   ├── llm_factory.py       Groq / Gemini / Ollama / Claude / NVIDIA
│   ├── charts.py            picks the right chart
│   ├── mcp_server.py        read-only MCP tools for Claude Desktop
│   └── config.py            settings from .env
├── data/                    generator, schema docs, glossary, examples
├── eval/                    50 test questions + accuracy runner
├── tests/                   72 pytest tests (no API key needed)
└── docs/                    how-to, interview guide, LinkedIn kit
```

## Run the tests and quality checks

```bash
pip install -r requirements-dev.txt
ruff check .        # lint
mypy                # type-check
python -m pytest    # tests
```

Tests use a fake LLM with scripted replies, so they are free, fast and need no API key. CI runs all three on Python 3.11 and 3.13.

## Use it from Claude Desktop (MCP server)

`src/mcp_server.py` exposes the database to any MCP client through four read-only tools: `list_tables`, `describe_tables`, `business_rules` and `run_sql`. The client's own model writes the SQL, so no API key is needed, and every query passes the same guard and read-only connection as the chat app.

```bash
pip install -r requirements-mcp.txt
```

Then add this to Claude Desktop's config (**Settings → Developer → Edit Config**; on Windows the file is `%APPDATA%\Claude\claude_desktop_config.json`) and restart Claude Desktop:

```json
{
  "mcpServers": {
    "talktodata": {
      "command": "C:\\path\\to\\Ask-your-HR-payroll-Assistant-AI-Chat-Bot-\\.venv\\Scripts\\python.exe",
      "args": ["C:\\path\\to\\Ask-your-HR-payroll-Assistant-AI-Chat-Bot-\\src\\mcp_server.py"]
    }
  }
}
```

On macOS/Linux use `.venv/bin/python` and forward slashes. Ask Claude something like *"Using talktodata, which department had the most leavers in 2026?"*

## Deploy for free

1. Push this repo to GitHub.
2. Go to [share.streamlit.io](https://share.streamlit.io), choose the repo, main file `app/streamlit_app.py`.
3. In **Advanced settings**, pick Python 3.11 or newer. Under **Secrets**, add `LLM_PROVIDER = "nvidia"` and `NVIDIA_API_KEY = "nvapi-..."` (or `LLM_PROVIDER = "groq"` with `GROQ_API_KEY`). Secrets never go in the repo.
4. Deploy. The database is generated automatically on first start.

## What I'd build next

- Role-based access (hide salary columns for some users)
- PostgreSQL / Azure SQL support
- Query result caching and cost tracking
- Neural embeddings for example search when the example set grows

## License

MIT. Data is fictional and generated; any resemblance to real companies or people is coincidental.
