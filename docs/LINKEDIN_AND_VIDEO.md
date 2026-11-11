# LinkedIn video and post kit

## Before you record

- Deploy the app and run the benchmark first, so you can show the live link and a real accuracy number.
- Close other tabs and notifications. Zoom the browser to 125% so text is readable on phones.
- Free recording tools: **Clipchamp** (built into Windows 11) or **OBS Studio** for screen + webcam; **Loom** free plan also works.
- Record in 1080p. Keep it **2 to 3 minutes**. LinkedIn autoplays muted, so turn on captions (Clipchamp has auto-captions).
- Do one practice run. Say the words; don't read them.

## Video script (about 2.5 minutes)

**0:00–0:15 · Hook (face on camera or title slide)**
"Most business people can't write SQL, so simple questions like 'how many payroll issues are still open?' wait days for an analyst. I built an AI assistant that answers them in seconds, safely. Let me show you."

**0:15–0:45 · First question (screen)**
Click "How many active employees does each company have?"
"I just type in plain English. It writes the SQL, runs it, and explains the answer, with a chart. And here's the exact SQL it used, so nothing is a black box."
Open the **SQL used** expander for two seconds.

**0:45–1:15 · Harder question + follow-up**
Ask "What is the attrition rate per company over the last 12 months?" then "Now only show companies above 10%."
"It follows our business definition of attrition from a glossary, and it remembers the conversation, so follow-ups work."

**1:15–1:40 · Safety**
Type "Delete all employees."
"What if someone tries to change data? Every query passes a SQL parser that only allows a single read-only SELECT, and the database connection itself is read-only. It can't be talked into deleting anything."

**1:40–2:05 · How it works (show the architecture diagram from the README)**
"Under the hood it's a LangGraph agent: it picks the relevant tables, finds similar solved examples, writes the SQL, checks it, runs it, and if anything fails it reads the error and fixes itself, up to three times. It works with free models like Groq and Gemini, or fully offline with Ollama."

**2:05–2:25 · Proof**
Show the accuracy table.
"I don't just say it works: I test it on 50 questions from easy to hard. It gets 78 to 84% right with a free NVIDIA Nemotron model, depending on the run. There are also 72 automated tests running on every push."

**2:25–2:40 · Close**
"All the data is fictional, and the full code is on GitHub. Link in the comments. I'd love feedback, especially from people working with HR and payroll data."

## Post option 1 (story)

> Payroll and HR teams ask great questions. The problem is that the answer usually sits behind SQL.
>
> So I built **TalkToData**: an AI assistant that turns plain-English questions into safe SQL, runs them, and explains the result with a chart.
>
> 🔹 Ask "Which payroll exceptions are older than 14 days?" and get the answer in seconds
> 🔹 Every answer shows the exact SQL used, so nothing is a black box
> 🔹 It can't change data: a SQL parser allows only read-only queries, and the database connection is read-only too
> 🔹 If a query fails, the agent reads the error and fixes itself
> 🔹 Tested on 50 questions: 78–84% execution accuracy with a free NVIDIA Nemotron model
> 🔹 Runs on free models (Groq, Gemini) or fully offline with Ollama
>
> Stack: Python · LangChain · LangGraph · SQLite · Streamlit · pytest · GitHub Actions
>
> All data is fictional (four made-up companies, ~635 made-up employees).
>
> 🎥 2-minute demo below. Live app and code in the comments.
>
> What question would you ask your HR data first?
>
> #GenerativeAI #LangChain #LangGraph #TextToSQL #Python #HRAnalytics #DataAnalytics #LLM

## Post option 2 (short and technical)

> Built a text-to-SQL agent this month. What I learned:
>
> 1️⃣ The model is the easy part. Context is the hard part: schema descriptions + a business glossary + similar examples made the biggest accuracy difference.
> 2️⃣ Never trust generated SQL. I parse it with sqlglot and allow only a single SELECT, on a read-only connection.
> 3️⃣ Let it fail and retry. Feeding the database error back to the model fixes most mistakes.
> 4️⃣ Measure it. 50 test questions, execution accuracy 78–84% over repeated runs, with thinking on vs off compared.
>
> Demo + code in the comments. Built with LangGraph, Streamlit and free LLMs.
>
> #AI #LLM #LangGraph #Python #DataEngineering

## First comment (post it yourself right after publishing)

> 🔗 Live demo: <your Streamlit link>
> 💻 Code: <your GitHub link>
> 📖 How it works: README → "How it works"

## Posting tips

- Upload the video natively to LinkedIn (not a YouTube link); native video gets more reach.
- Post Tuesday to Thursday morning in your target audience's time zone.
- Reply to every comment in the first two hours.
- Tag no more than 2–3 people, and only ones who would genuinely care.
- Add the project to your LinkedIn **Featured** section and to the **Projects** section with the GitHub link.
- On your resume: *"Built a text-to-SQL AI assistant (LangGraph, Python, SQLite) with 4-layer SQL safety and a 50-question benchmark (78–84% execution accuracy); deployed publicly on Streamlit."*
