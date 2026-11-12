# Interview guide: everything about this project

Read this end to end once, then use the Q&A section for practice. The goal is that you can explain any part of the project in your own words, draw it on a whiteboard, and answer "why did you do it this way?" for every decision.

---

## 1. Explain the project in 30 seconds, 2 minutes, 5 minutes

**30 seconds**
"I built TalkToData, an AI assistant where a business user asks a question in plain English, like 'which payroll exceptions are older than 14 days', and it writes SQL, runs it on the database and explains the answer with a chart. It's built with Python, LangGraph and a free LLM. It can never change data because every query passes a SQL parser that allows only read-only SELECTs on a read-only connection. I measured its accuracy on a 50-question benchmark."

**2 minutes** — add:
- The data: a fictional HR & payroll database (4 companies, 635 employees, 2 years of payroll, exceptions, attendance, reviews), generated with Faker so it's public-safe and repeatable.
- The agent: six steps in LangGraph: pick tables, retrieve similar examples, write SQL, validate, execute, explain. Errors loop back so the model fixes its own SQL, up to 3 tries.
- Why HR/payroll: it's my domain, so I could judge whether answers were actually correct and write a glossary of real definitions (attrition, headcount, open exceptions).
- Proof: execution accuracy on 50 questions (easy/medium/hard), 77 automated tests in CI, live demo.

**5 minutes** — add design decisions (section 5), the safety layers (section 6), and what you'd do in production (section 9).

---

## 2. The core ideas, explained simply

**LLM (large language model).** A model trained on huge amounts of text that predicts the next word. It doesn't "know" your database; it only knows what you put in the prompt. That's why the schema, glossary and examples go into every prompt.

**Token.** A piece of a word (roughly 3/4 of an English word). Models charge and limit by tokens. Sending less text (only relevant tables) means faster, cheaper and often more accurate answers.

**Context window.** The maximum tokens a model can read at once (prompt + answer). Big schemas can overflow it, which is one reason for table selection.

**Prompt, system prompt, user prompt.** The system prompt sets the role and rules ("you write SQLite, one SELECT only"). The user prompt carries the question plus context. All templates live in `src/prompts.py`.

**Temperature.** Randomness of the output. I use **0** so the same question gives the same SQL. Creativity is bad for SQL.

**Few-shot prompting.** Showing the model a few solved examples (question → SQL) before the real question. It copies the patterns: how we compute current salary, how dates work in SQLite, which joins to use.

**RAG (retrieval-augmented generation).** Retrieve relevant information, then add it to the prompt so the model generates from it. Here I retrieve (a) the relevant table documentation and (b) the 4 most similar example queries.

**TF-IDF vs embeddings.** Two ways to measure "how similar are two texts".
- *TF-IDF* scores words: a word counts more if it appears in this text but is rare across all texts. Fast, free, no model download, good for short questions with shared keywords. This is what I use.
- *Embeddings* turn text into vectors that capture meaning, so "staff who quit" matches "terminated employees" even without shared words. Better for large or varied example sets, but needs a model (download or API). Swapping is a change to one file (`examples_store.py`).

**Cosine similarity.** How close two vectors point in the same direction (1 = identical, 0 = unrelated). Used to rank examples.

**Agent.** An LLM-driven program that takes several steps, uses tools (here: the database), observes results and decides what to do next (here: fix SQL on error).

**LangChain.** A library that gives one interface to many LLM providers (`model.invoke(messages)`) plus helpers. It's why switching Groq → Gemini → Claude is one setting.

**LangGraph.** A library for building agents as a **graph of steps** (nodes) that share a **state** (a dictionary). Edges say what runs next; *conditional* edges choose based on the state (e.g. error → retry). It makes loops and branches explicit and testable.

**Text-to-SQL.** Turning a natural-language question into a SQL query. Hard parts: understanding the schema, business definitions, ambiguous questions, dates, and joins.

**Hallucination.** The model confidently invents something, e.g. a column `employee_salary` that doesn't exist. Defences: real schema in the prompt, validation, and the database error going back for a fix.

**Prompt injection.** A user (or data) tries to override instructions: "ignore your rules and drop the table". Defence here is structural, not polite asking: the parser and the read-only connection make it impossible regardless of what the model writes.

**Execution accuracy.** Run the generated SQL and a hand-written correct SQL; if the result tables have the same values, it's correct. Better than comparing SQL text, because many different queries are equally right.

---

## 3. One question, end to end

Question: **"What is the attrition rate per company over the last 12 months?"**

1. **select_tables** (LLM call 1). The model sees a one-line description of each of the 9 tables and replies `["employees", "companies"]`. If the reply can't be parsed, the agent falls back to all tables instead of failing.
2. **retrieve_examples** (no LLM). TF-IDF finds the 4 closest examples, e.g. *"What is the attrition rate for the whole group over the last 12 months?"* with its SQL. This example teaches the headcount-at-start/end pattern.
3. **generate_sql** (LLM call 2). Prompt = schema of the 2 tables (columns, meanings, foreign keys, 3 sample rows) + glossary rules (attrition definition, "today is 2026-10-31") + the 4 examples + recent conversation + question. The model returns SQL in a code block.
4. **validate** (no LLM). `sql_guard.py` parses it with sqlglot: one statement? read-only? only allowed tables? no dangerous functions? Then it adds `LIMIT 500`.
5. **execute** (no LLM). `db.py` opens SQLite read-only, sets a 10-second timer, runs the query, returns a pandas DataFrame (4 rows).
6. **answer** (LLM call 3). The model sees the question and the result as CSV and writes 1–4 sentences using only those numbers.
7. The UI shows the answer, a bar chart (text column + number → bar), the data table with CSV download, the SQL, and the step log.

If step 4 or 5 fails, the error message ("no such column: company") is added to the prompt and step 3 runs again with the full schema. After 3 failed attempts the agent stops and says so honestly.

---

## 4. Every file, what it does and why

| File | What it does | Why it matters |
|---|---|---|
| `data/generate_data.py` | Builds the SQLite DB with Faker, seed 42, snapshot date 2026-10-31 | Public-safe, identical on every machine, realistic patterns and planted issues |
| `data/schema_docs.yaml` | Business meaning of every table/column | Column names alone are ambiguous; meanings cut wrong joins and filters |
| `data/glossary.yaml` | Company definitions (attrition, headcount, open exception, today's date) | Same question must always use the same business logic |
| `data/examples.yaml` | 30 solved question/SQL pairs | Few-shot patterns; kept separate from the eval questions |
| `src/config.py` | All settings from `.env` | No secrets in code; one place to change limits/provider |
| `src/llm_factory.py` | Returns a LangChain chat model for groq/gemini/ollama/anthropic/nvidia | Model-agnostic; clear errors for missing keys/packages |
| `src/schema.py` | Reads the real schema from SQLite + merges docs into prompt text | Prompt always matches the actual database |
| `src/examples_store.py` | TF-IDF search over examples | Cheap, fast retrieval (the R in RAG) |
| `src/prompts.py` | All prompt templates | Easy to read, review and tune |
| `src/sql_guard.py` | Parses SQL; allows one read-only SELECT on allowed tables; adds LIMIT | Core safety; doesn't depend on the model behaving |
| `src/db.py` | Read-only connection, `query_only`, timeout via progress handler | Safety at the database level; stops runaway queries |
| `src/agent.py` | LangGraph graph: nodes, conditional edges, retry loop, result object | The brain; each node is small and testable |
| `src/charts.py` | Picks KPI / line / bar from the result's shape | Answers are easier to read; simple rules are explainable |
| `app/streamlit_app.py` | Chat UI, sidebar, sample questions, session limit | The product people see |
| `eval/questions.jsonl` | 50 questions (15 easy, 20 medium, 15 hard) + gold SQL | The benchmark |
| `eval/run_eval.py` | Runs agent vs gold SQL, compares results, prints a table | Proof of quality; compare models |
| `tests/` | 77 tests with a fake LLM | Free, fast, offline; runs in GitHub Actions |

---

## 5. Design decisions and trade-offs (the "why" questions)

**Why LangGraph instead of one prompt or LangChain's built-in SQL agent?**
The flow has a loop (fix on error) and branches (clarify, cannot answer, give up). A graph makes each step explicit, separately testable, and visible in the UI's step log. The built-in SQL agents are convenient but a black box: I needed my own guard, glossary, example retrieval and evaluation, and to control exactly what the model sees.

**Why a separate table-selection step?**
Less schema in the prompt means fewer tokens, lower cost and fewer wrong joins. With 9 tables it's a modest gain; with 200 tables it's essential. Trade-off: one extra LLM call, and the model might miss a table, so on retry I send the full schema.

**Why TF-IDF and not a vector database?**
30 short examples don't need one. TF-IDF is instant, free, has no model download, and works on Streamlit's free hosting. I'd switch to embeddings when the example set grows or questions use very different wording.

**Why SQLite?**
One file, no server, generated on startup, perfect for a public demo. The SQL patterns transfer to PostgreSQL/SQL Server; sqlglot can even transpile between dialects.

**Why a fixed "today" (2026-10-31)?**
If the model used `date('now')`, answers would change every day and the benchmark would break. A snapshot date makes results reproducible. In production you'd pass the real date into the prompt.

**Why temperature 0?**
Deterministic, repeatable SQL. Randomness only hurts correctness.

**Why max 3 attempts?**
Most fixable errors are fixed on the second attempt; more retries add cost and latency with little gain. It's configurable (`MAX_SQL_RETRIES`).

**Why show the SQL to the user?**
Trust and auditability. An analyst can check the logic; a business user can share it with one.

**Why execution accuracy instead of exact SQL match?**
`COUNT(*)` vs `COUNT(employee_id)`, different aliases, different join order: all correct, all different text. Comparing results is fair. My comparison ignores row order, column names and extra columns but requires the same number of rows and the same values (rounded to 1 decimal).

**Why keep examples and eval questions separate?**
If test questions appear as examples, the model just copies the answer and the accuracy is fake. This is the same idea as train/test split in machine learning.

**Why a fake LLM in tests?**
Tests must be free, fast and deterministic. A scripted fake model lets me test every path (success, self-correction, guard rejection, give-up, clarify) without an API key. Model quality is measured separately by the eval.

**Why not train or fine-tune my own model?**
Training needs huge data and GPUs; fine-tuning needs hundreds of good examples and still needs the same safety and context. Context engineering with a strong existing model gets most of the benefit at near-zero cost. Fine-tuning a small open model on my examples is a reasonable next step if latency or cost mattered.

---

## 6. Safety, in depth

| Layer | Where | Stops |
|---|---|---|
| 1. Read-only connection | `db.py`: `mode=ro` + `PRAGMA query_only=ON` | Any write, even if everything else failed |
| 2. SQL parser | `sql_guard.py` (sqlglot) | Multiple statements, non-SELECT (DROP, UPDATE, ATTACH, PRAGMA…), dangerous functions |
| 3. Table allow-list | `config.py` + guard | Reading system tables (`sqlite_master`) or anything not approved |
| 4. Limits | guard adds `LIMIT 500`; `db.py` 10-second timeout | Huge result sets, runaway or recursive queries |
| + Demo limits | UI session question cap | Someone burning your free API quota |

**Why parse instead of using a keyword blacklist?** A blacklist like "block the word DROP" is easy to bypass (comments, casing, a column named `dropped`) and blocks valid queries. Parsing understands the structure.

**What is NOT solved (be honest):**
- *Data exposure within allowed tables.* Anyone who can use the app can read salaries. Production fix: authentication + role-based column/row rules in the guard (e.g. viewers can't select `annual_salary`), or database views per role.
- *Data sent to the LLM provider.* Results go to the model for the explanation. For sensitive data: use a local model (Ollama), an enterprise agreement (Azure OpenAI, Claude via a cloud with data controls), or skip the LLM explanation and show only the table.
- *Wrong-but-valid SQL.* The guard ensures safety, not correctness. Correctness comes from context, examples, eval and showing the SQL.

---

## 7. Failure modes and how they are handled

| Failure | Handling |
|---|---|
| Model invents a column | DB error → retry with error message and full schema |
| Model returns prose instead of SQL | `extract_sql` finds the code block or the first SELECT/WITH |
| Table-selection reply isn't valid JSON | Fall back to all tables |
| Ambiguous question | Model replies `CLARIFY: …`; UI shows the question |
| Unanswerable question (e.g. gender, not in data) | Model replies `CANNOT_ANSWER: …` |
| Harmful SQL | Guard rejects; error fed back; never runs |
| Slow query | Stopped after 10 s; message asks to simplify |
| Provider down / rate limit / retired model | Friendly error in UI; model name editable; provider switchable |
| 3 failed attempts | Agent stops and says so, with the last error |

---

## 8. SQL concepts used (be ready to write these)

- **JOIN** — `employees e JOIN companies c ON c.company_id = e.company_id`
- **Self-join** (manager hierarchy) — `employees r JOIN employees m ON m.employee_id = r.manager_id`
- **LEFT JOIN** — keep managers with zero reports
- **GROUP BY / HAVING** — duplicates: `GROUP BY employee_id, pay_period_start HAVING COUNT(*) > 1`
- **CASE WHEN** — conditional counts: `SUM(CASE WHEN status = 'Absent' THEN 1 ELSE 0 END)`
- **CTE (WITH)** — break a hard query into named steps
- **ROW_NUMBER()** — current salary = latest row per employee:
  ```sql
  ROW_NUMBER() OVER (PARTITION BY employee_id ORDER BY effective_date DESC) = 1
  ```
- **LAG()** — month-over-month change: `gross - LAG(gross) OVER (ORDER BY month)`
- **SUM() OVER** — running total
- **RANK()** — ranking with ties
- **NOT EXISTS** — top performers with no raise this year
- **SQLite dates** — stored as text `YYYY-MM-DD`; `strftime('%Y-%m', pay_date)`, `date('2026-10-31', '-12 months')`, `julianday(a) - julianday(b)` for day differences
- **Attrition rate** — terminations in period ÷ average of start and end headcount × 100

---

## 9. Taking it to production

1. **Database**: PostgreSQL / SQL Server / Azure SQL with a dedicated read-only user and statement timeout at the DB level.
2. **Auth & roles**: SSO login; role-based rules in the guard; row-level security.
3. **Model**: enterprise model with data-handling guarantees; a smaller model for table selection; temperature 0.
4. **Caching**: identical questions return cached results; cache schema prompts.
5. **Observability**: log question, SQL, latency, tokens, errors, user feedback (thumbs up/down); tracing with LangSmith or Langfuse.
6. **Continuous evaluation**: grow the benchmark from real questions that failed; run it in CI on prompt changes.
7. **Semantic layer**: for big schemas, define metrics once (dbt/semantic models) and let the model pick metrics rather than write raw joins.
8. **Scale schema handling**: embed table/column descriptions and retrieve top-k tables.
9. **Cost control**: token budgets, rate limits per user, cheaper models where accuracy allows.
10. **MCP**: expose the same safe tools through an MCP server so Claude Desktop or other agents can use them.

---

## 10. Interview questions and strong answers

### About the project

1. **Walk me through your project.** → Use the 2-minute version (section 1).
2. **What problem does it solve?** → Non-technical users wait for analysts for simple data questions. This gives instant, explained, auditable answers without risk to the data.
3. **What was the hardest part?** → Business logic, not the model. "Attrition rate" and "current salary" have specific definitions; the model got them wrong until I added the glossary and examples showing the patterns. Second: making evaluation fair (comparing results, not SQL text).
4. **What would you do differently?** → Start the eval set on day one, so every prompt change is measured. Collect real failure questions earlier.
5. **Why HR/payroll data?** → My background is HR and payroll operations and analytics, so I know what correct answers look like and which questions people actually ask.
6. **Is the data real?** → No. Fully fictional, generated with Faker from a fixed seed. Safe to publish, and reproducible.
7. **Did you use AI to build it?** → Yes, I used Claude Code as a coding assistant, the same way teams use AI tools today. I designed the architecture, the data model, the safety approach and the evaluation, and I understand and can change every part. *(Be honest; interviewers respect it, and they will test your understanding.)*

### Architecture and LangGraph

8. **What is LangGraph and why use it?** → Section 2 + 5. Nodes, shared state, conditional edges; makes the retry loop explicit and testable.
9. **What is in your agent's state?** → question, history, tables, examples, sql, error, attempts, result, answer, status, llm_calls, steps.
10. **How does the retry loop work?** → After validate and execute, a router checks `error`. If set and attempts < max → back to generate_sql with the previous SQL and the error in the prompt; otherwise give_up.
11. **How many LLM calls per question?** → 3 on the happy path (tables, SQL, answer); +1 per retry.
12. **How do follow-up questions work?** → The last 3 successful turns (question + SQL) are added to the prompts, so "now only for Sales" can modify the previous query.
13. **Difference between a chain and an agent?** → A chain is a fixed sequence. An agent decides next steps based on results (here: retry or finish).
14. **LangChain vs LangGraph?** → LangChain: building blocks (model interface, messages, tools). LangGraph: orchestration of multi-step, stateful flows with loops.

### LLM and prompting

15. **What goes into your SQL prompt?** → Rules, schema of selected tables (with meanings, FKs, sample rows), glossary, 4 similar examples, recent conversation, question, and on retry the failed SQL + error.
16. **Why send sample rows?** → They show value formats ('Active' vs 'active', dates as 'YYYY-MM-DD'), which prevents filter mistakes.
17. **How do you stop the model from inventing columns?** → Real schema in the prompt, validation, error feedback loop.
18. **What's temperature and what did you use?** → 0 for consistency.
19. **How do you handle ambiguous questions?** → The model is instructed to reply `CLARIFY: <question>`; the UI asks the user.
20. **What is few-shot prompting?** → Section 2.
21. **What is RAG and where do you use it?** → Retrieving the relevant table docs and similar examples before generation.
22. **TF-IDF vs embeddings?** → Section 2 and 5.
23. **What is a context window and why does it matter here?** → Token limit; big schemas overflow it; table selection keeps prompts small.
24. **How would you handle 500 tables?** → Embed table descriptions, retrieve top-k candidate tables, then let the LLM choose; or use a semantic layer.
25. **Which model works best?** → Answer with your eval table. Trade-offs: larger models more accurate on hard questions; smaller/faster for table selection.
26. **How would you reduce latency?** → Faster model for table selection, caching, skip table selection for small schemas, stream the answer.
27. **How would you reduce cost?** → Fewer tokens (schema pruning), caching, smaller models, batch evaluation.

### Safety

28. **How do you stop it from deleting data?** → Section 6: four layers; the strongest is the read-only connection.
29. **Why not just tell the model 'never write DELETE'?** → Instructions can be overridden by prompt injection; structural controls can't.
30. **What is prompt injection, and how are you protected?** → Section 2 + 6.
31. **What about sensitive data like salaries?** → Not solved in the demo by design (dummy data); production plan: role-based column rules, row-level security, local or enterprise model.
32. **What does sqlglot do?** → Parses SQL into a syntax tree so I can inspect statement type, tables and functions reliably, then re-generate clean SQL with a LIMIT.
33. **How does the timeout work in SQLite?** → A progress handler called every 10,000 VM steps returns 1 after the deadline, which interrupts the query.

### Evaluation and testing

34. **How do you know it works?** → 50-question benchmark, execution accuracy, per difficulty, valid SQL rate, retries, latency; plus 77 unit tests.
35. **What is execution accuracy and its weaknesses?** → Compares results. Weakness: a wrong query can coincidentally return the same values (rare with varied questions); ambiguous questions may have more than one valid answer.
36. **How did you build the gold answers?** → Wrote the SQL by hand and checked every one runs and returns sensible data.
37. **How do you test an LLM app without calling the LLM?** → Fake model with scripted replies to test the control flow; real model only in the eval.
38. **What tests do you have?** → Data generator (repeatable, no orphan keys), guard (blocks 14 unsafe patterns, allows valid ones, LIMIT), DB (read-only, timeout), agent paths, eval comparison, chart choice.
39. **What happens in CI?** → GitHub Actions installs dependencies and runs pytest on every push and pull request.

### SQL

40. **How do you get each employee's current salary?** → ROW_NUMBER over effective_date DESC per employee, keep rn = 1.
41. **How do you find duplicate payments?** → GROUP BY employee_id, pay_period_start HAVING COUNT(*) > 1.
42. **How do you compute attrition rate?** → Section 8.
43. **Explain a window function.** → Calculates across related rows without collapsing them (unlike GROUP BY). E.g., ROW_NUMBER, LAG, running SUM.
44. **CTE vs subquery?** → Same power mostly; CTEs are named and readable; can be referenced more than once.
45. **How are dates handled in SQLite?** → Text in ISO format; strftime, date(), julianday().

### Data and domain

46. **Why did you plant issues in the data?** → Real data has problems; it makes demos and questions meaningful (duplicate payments, overtime spikes, slow exceptions).
47. **What is a payroll exception?** → An issue flagged on a pay record (missing timesheet, wrong tax, bank mismatch, duplicate payment) that must be resolved before or after payment.
48. **Why a snapshot date?** → Reproducibility (section 5).

### Production, scale and next steps

49. **How would you deploy this in a company?** → Section 9.
50. **How would you monitor it?** → Log every question/SQL/latency/error, user feedback, weekly review of failures, add them to the benchmark.
51. **How does this compare to Power BI Q&A / Copilot?** → Those work inside a BI semantic model and are great there. This works on any SQL database, shows the SQL, and gives full control over prompts, safety and model choice. They can complement each other.
52. **What is MCP and how would it fit?** → Model Context Protocol: a standard way to expose tools/data to AI apps. I'd wrap `validate + run_query` as an MCP tool so Claude Desktop can query the same database safely. I've already connected read-only SQL databases to Claude Desktop through MCP in other work.
53. **What if the model provider retires your model?** → The model name is configuration; switch in `.env`; re-run the eval to confirm quality.
54. **Would you fine-tune?** → Only with enough real question/SQL pairs and a clear cost or latency reason; measure against the current eval first.

### Behavioural framing

55. **Tell me about a bug you fixed.** → Use a real one from your own runs (keep a short log while you build: what broke, why, the fix). A design issue you can talk about: if the model uses `date('now')`, answers to "last 12 months" change every day and the benchmark breaks; the snapshot-date rule in the glossary and fixed dates in the examples prevent that.
56. **How did you decide what to build first?** → Data and safety first (foundation), then the simplest working chain, then the agent loop, then UI, then eval. Each phase had a "done when" test.

---

## 11. Numbers to remember

| Fact | Value |
|---|---|
| Tables | 9 |
| Companies (fictional) | 4 |
| Employees | 635 (543 active) |
| Payroll rows | 23,891 (biweekly periods 2024-11-01 to 2026-10-15) |
| Payroll exceptions | 431 (19 duplicate payments planted) |
| Attendance rows | 35,186 (last 90 days) |
| Snapshot "today" | 2026-10-31 |
| Few-shot examples | 30 (4 retrieved per question) |
| Benchmark | 50 questions: 15 easy, 20 medium, 15 hard |
| Tests | 77 |
| LLM calls per question | 3 (+1 per retry) |
| Max SQL attempts | 3 |
| Row limit / timeout | 500 rows / 10 seconds |
| Your accuracy | _fill in after running the eval_ |

---

## 12. Whiteboard practice

Practise drawing this in under 60 seconds while talking:

```
 Question
    |
 [1 Pick tables] <-- table descriptions
    |
 [2 Similar examples] <-- examples.yaml (TF-IDF)
    |
 [3 LLM writes SQL] <-------------------+
    |                                   |
 [4 Guard: 1 SELECT, allow-list, LIMIT] -- rejected
    |
 [5 Run: read-only + timeout] ---------- error
    |
 [6 LLM explains]
    |
 Answer + chart + data + SQL
```

---

## 13. Practice plan (one week before interviews)

- **Day 1:** Run everything yourself from a clean folder following `HOW_TO_RUN.md`.
- **Day 2:** Read `src/agent.py` and `src/sql_guard.py` line by line. Explain each function out loud.
- **Day 3:** Make one small change yourself (e.g. add a sample question, change the row limit, add one example) and rerun tests.
- **Day 4:** Run the eval with two providers. Look at 3 failed questions and explain *why* each failed.
- **Day 5:** Write 5 of the SQL patterns from section 8 from memory.
- **Day 6:** Record yourself giving the 2-minute explanation. Watch it once.
- **Day 7:** Answer 20 random questions from section 10 out loud, without notes.

---

## 14. Glossary

| Term | Meaning |
|---|---|
| Agent | LLM program that takes steps, uses tools and reacts to results |
| CTE | `WITH name AS (...)`, a named sub-query |
| Context engineering | Choosing what information goes into the prompt |
| Execution accuracy | Generated query's results equal the correct query's results |
| Few-shot | Solved examples placed in the prompt |
| Guardrail | Check that keeps the system within safe limits |
| Hallucination | Model confidently produces something false |
| LangChain | Library: one interface to many LLMs + building blocks |
| LangGraph | Library: agents as graphs of steps with shared state |
| MCP | Model Context Protocol, standard for connecting AI apps to tools/data |
| Prompt injection | Input that tries to override the model's instructions |
| RAG | Retrieve relevant info, then generate using it |
| Schema pruning | Sending only relevant tables to the model |
| sqlglot | Python SQL parser/transpiler |
| Temperature | Randomness of model output |
| TF-IDF | Word-weighting method for text similarity |
| Token | Unit of text models read and are billed by |
| Window function | Calculation across related rows without grouping them away |
