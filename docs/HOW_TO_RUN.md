# How to run this project in VS Code (Windows)

This takes about 20 minutes the first time. Commands are for Windows PowerShell; macOS/Linux differences are noted.

## 1. Install the tools (once)

1. **Python 3.11, 3.12 or 3.13** from python.org. In the installer, tick **"Add python.exe to PATH"**.
2. **Git** from git-scm.com (default options are fine).
3. **VS Code** from code.visualstudio.com, then install the **Python** extension (by Microsoft).
4. Optional: **Claude Code** in VS Code, to keep building with AI help.

Check in a new terminal:

```powershell
python --version
git --version
```

## 2. Put the project on your computer

Unzip the project folder, for example to `C:\Projects\talk-to-data-sql-assistant`. In VS Code: **File → Open Folder** and choose it. Open a terminal: **Terminal → New Terminal**.

## 3. Create a virtual environment

A virtual environment keeps this project's packages separate from everything else.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

If PowerShell says scripts are disabled, run this once, then activate again:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

You should now see `(.venv)` at the start of the terminal line. In VS Code, press `Ctrl+Shift+P` → **Python: Select Interpreter** → choose the one inside `.venv`.

macOS/Linux: `source .venv/bin/activate`

## 4. Install the packages

```powershell
pip install -r requirements.txt
```

## 5. Get a free API key

Pick **one**:

- **Groq (recommended, fast, free tier):** sign up at console.groq.com → API Keys → Create. 
- **Google Gemini (free tier):** aistudio.google.com → Get API key.
- **Ollama (fully local, no key):** install from ollama.com, then run `ollama pull qwen2.5-coder:7b`, and `pip install langchain-ollama`. Needs a reasonably strong laptop.

## 6. Create your `.env` file

```powershell
copy .env.example .env
```

Open `.env` in VS Code and fill in, for Groq:

```
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_your_key_here
```

For Gemini: `LLM_PROVIDER=gemini` and `GOOGLE_API_KEY=...`. For Ollama: `LLM_PROVIDER=ollama`.

`.env` is listed in `.gitignore`, so it is never uploaded to GitHub. Never paste your key anywhere else.

## 7. Build the dummy database

```powershell
python data/generate_data.py
```

You should see 9 tables with their row counts. The file `data/hr_payroll.db` is created (the app also does this automatically if it is missing).

## 8. Run the tests

```powershell
pip install -r requirements-dev.txt   # test, lint and type-check tools (once)
ruff check .
mypy
python -m pytest
```

Expected: `All checks passed!`, `Success: no issues found`, and `68 passed`. Tests use a fake model, so they work without an API key.

## 9. Start the app

```powershell
streamlit run app/streamlit_app.py
```

Your browser opens at http://localhost:8501. Click a sample question in the sidebar or type your own. Stop the app with `Ctrl+C` in the terminal.

## 10. Measure accuracy

```powershell
python eval/run_eval.py --limit 10     # quick check, 10 questions
python eval/run_eval.py                # all 50 (takes a few minutes)
```

Copy the markdown table it prints into the README **Accuracy** section. Free tiers have rate limits; if you see rate-limit errors, add `--sleep 3`.

## Good questions to try

- How many active employees does each company have?
- Show total gross payroll by month for 2026
- Now only for Orbitron Retail *(follow-up)*
- Which open payroll exceptions are older than 14 days?
- Who was paid twice for the same pay period?
- What is the attrition rate per company over the last 12 months?
- Which managers have a team average rating below 3 in 2026-H1?
- Delete all employees *(watch the guard refuse it)*

## Troubleshooting

| Problem | Fix |
|---|---|
| `python` not found | Reinstall Python with "Add to PATH" ticked, reopen VS Code |
| `ModuleNotFoundError` | The venv is not active: run `.venv\Scripts\Activate.ps1`, then `pip install -r requirements.txt` |
| "GROQ_API_KEY is not set" | Check `.env` is in the project root and the line has no spaces around `=` |
| Model not found / decommissioned | The provider retired it. Find a current model in their docs and set `LLM_MODEL=` in `.env`, or type it in the sidebar |
| Rate limit / 429 errors | Wait a minute, use `--sleep 3` in eval, or switch provider |
| Port 8501 in use | `streamlit run app/streamlit_app.py --server.port 8502` |

## Keep building with Claude Code

Open Claude Code in the project folder. It reads `CLAUDE.md` automatically. Example prompts:

- "Read PLAN.md and docs/INTERVIEW_GUIDE.md, then explain the agent flow to me step by step."
- "Add a node to the LangGraph agent that caches answers for repeated questions. Add tests."
- "Add role-based column hiding: when ROLE=viewer, block salary columns in sql_guard. Add tests."
- "Run the eval, look at the failed questions, and suggest new few-shot examples (not copies of eval questions)."
