# Publish on GitHub and deploy the live demo

## 1. Public-safety check (do this every time before pushing)

- [ ] No real employer, client or colleague names anywhere. In VS Code press `Ctrl+Shift+F` and search for each real name you can think of.
- [ ] `.env` is NOT in the repo (`git status` must not list it).
- [ ] No real screenshots, exports or connection strings.
- [ ] All data comes from `data/generate_data.py`.

## 2. Create the repository

1. Sign in at github.com → **New repository**.
2. Name: `talk-to-data-sql-assistant`. Description: *Chat with an HR & payroll database in plain English. LangGraph + LLM text-to-SQL with safety guardrails and an accuracy benchmark.*
3. **Public**. Do NOT tick "Add a README" (you already have one). Click **Create repository**.

## 3. Push your code (first time)

In the VS Code terminal, inside the project folder:

```powershell
git init
git add .
git status                      # check .env and hr_payroll.db are NOT listed
git commit -m "TalkToData: text-to-SQL assistant with LangGraph, safety guard and eval"
git branch -M main
git remote add origin https://github.com/<your-username>/talk-to-data-sql-assistant.git
git push -u origin main
```

GitHub asks you to sign in the first time (a browser window opens).

## 4. Make the repo look professional

- **About** (gear icon on the repo page): add the description, your live demo URL, and topics: `text-to-sql`, `langchain`, `langgraph`, `llm`, `streamlit`, `sqlite`, `python`, `genai`, `hr-analytics`, `rag`.
- Check the **Actions** tab: the "tests" workflow should be green. Add the badge to the top of the README:
  `![tests](https://github.com/<your-username>/talk-to-data-sql-assistant/actions/workflows/ci.yml/badge.svg)`
- **Pin** the repo on your GitHub profile (Profile → Customize your pins).
- Add a 20–30 second GIF as `docs/demo.gif` (record with ScreenToGif on Windows, free) and uncomment the image line in the README.

## 5. Commit in small, meaningful steps from now on

Your commit history shows how you work. Good messages:

```
feat(agent): add answer caching for repeated questions
fix(guard): block sqlite_master access
docs: add accuracy results for Groq and Gemini
test: cover follow-up question history
```

Workflow for each change:

```powershell
python -m pytest
git add .
git commit -m "feat: ..."
git push
```

## 6. Deploy free on Streamlit Community Cloud

1. Go to share.streamlit.io and sign in with GitHub.
2. **Create app** → choose your repo, branch `main`, main file `app/streamlit_app.py`.
3. **Advanced settings → Secrets**, paste:

   ```toml
   LLM_PROVIDER = "groq"
   GROQ_API_KEY = "gsk_your_key"
   MAX_QUESTIONS_PER_SESSION = "15"
   ```
4. **Deploy**. First start takes a few minutes (it installs packages and generates the database).
5. Copy the app URL into the README and the repo's About box.

Your key stays private in Streamlit's secrets; visitors use your free quota, which is why the session question limit exists. If the quota runs out, the app shows a friendly error and you can switch provider in Secrets.

Alternative host: Hugging Face Spaces (choose the Streamlit SDK, add the same secrets).

## 7. Tag a release

When the README has your accuracy numbers and the demo link:

```powershell
git tag -a v1.0 -m "First public release"
git push origin v1.0
```

Then on GitHub: **Releases → Draft a new release → v1.0**, with three bullets on what it does.
