# LinkedIn video and post kit

## The video

- File: [`docs/media/TalkToData_demo.mp4`](media/TalkToData_demo.mp4) (2 min 27 s, 1920×1080, male voice-over, burned-in captions)
- Made from the real app (recorded in a browser), the 3D schema view from the project portal, and animated slides.
- The video says the app is powered by an LLM; it does not name the model vendor.
- All data shown is fictional.

### Voice-over script

| Scene | What is on screen | Voice-over |
|---|---|---|
| Hook | "Simple questions. Locked behind SQL." | HR and payroll teams ask simple questions every day. How many people are active? Which payroll issues are still open? But the answer is locked inside a database, and only someone who knows SQL can get it out. |
| Problem | Manager → ticket → analyst → days later | So every question becomes a ticket. The analyst is busy, the manager waits for days, and decisions get delayed. That costs the company time, and money. |
| Solution | TalkToData AI and its six steps | So I built TalkToData, an AI assistant for HR and payroll data, powered by a large language model. You ask in plain English. It writes the SQL, checks it, runs it, and explains the answer with a chart. |
| Under the hood | 3D view of the 9 tables | Under the hood, an AI agent maps nine connected tables, from employees and salaries to payroll runs and attendance. For every question, the LLM picks only the tables it needs, and writes the query. |
| Demo: ask | App: a sample question is answered | Here it is, live. I click a question: how many active employees does each company have? The agent picks the right tables, writes the query, and in seconds I get the answer. |
| Demo: proof | App: chart, data, SQL | Nothing is a black box. Every answer shows the chart, the data, a CSV download, and the exact SQL that was used. |
| Demo: safety | App: "Delete all employees" is refused | Now, what if someone tries to change the data? I ask it to delete all employees. It refuses. |
| Security | Four safety layers | Security is built in. A SQL parser allows only read-only queries on approved tables. The database connection itself is read-only, and every query has a row limit and a timeout. |
| Proof | 84% accuracy, 100% valid SQL, ~12 s, 76 tests | And I measured it. On a fifty-question benchmark it scores eighty-four percent, and seventy-six automated tests run on every change. |
| Value | Days → seconds, analysts freed, zero risk | For a business, that means answers in seconds instead of days, analysts free for real work, and zero risk to the data. |
| Close | Live link, QR code, GitHub | The project is live, and the full code is on GitHub. Try it yourself with the link below. If your team has a problem like this, I can build the solution: secure, tested, and ready to use. |

## LinkedIn post

> Every HR and payroll team has the same problem: the questions are simple, but the answers are locked behind SQL. 🔒
>
> "How many active employees do we have?"
> "Which payroll exceptions are still open?"
>
> Each one becomes a ticket, waits for an analyst, and decisions slow down. That costs time and money.
>
> So I built **TalkToData**: an AI assistant that lets anyone ask HR and payroll data questions in plain English. 🤖
>
> 🔹 Ask a question, get the answer in seconds, with a chart
> 🔹 Every answer shows the exact SQL, the data and a CSV download, so nothing is a black box
> 🔹 Secure by design: read-only SELECT queries on approved tables only, a read-only database connection, row limits and timeouts. Ask it to "delete all employees" and it refuses.
> 🔹 An LLM inside a LangGraph agent picks the right tables, writes the SQL, checks it and fixes its own mistakes
> 🔹 Measured, not guessed: 84% execution accuracy on a 50-question benchmark (78–84% across runs) and 76 automated tests on every change
>
> 🎥 Demo video below
> 🌐 Try it live: https://hrpayrollassistant.streamlit.app/
> 💻 Code on GitHub: https://github.com/brajeshpowwal/Ask-your-HR-payroll-Assistant-AI-Chat-Bot-
>
> The demo runs on fictional data, but the same approach works on real HRMS, payroll, CRM or finance databases. If your team spends hours waiting for data answers, let's talk. I'd be glad to build it for you.
>
> #GenerativeAI #AI #LLM #TextToSQL #LangGraph #Python #HRTech #Payroll #DataAnalytics #Automation

### Short version

> I built an AI assistant that answers HR and payroll questions in plain English, in seconds, without ever being able to change the data. 🔒🤖
>
> ✅ Plain English → safe SQL → answer + chart
> ✅ Read-only by design, every query visible
> ✅ 84% accuracy on a 50-question benchmark, 76 automated tests
>
> 🌐 Live: https://hrpayrollassistant.streamlit.app/
> 💻 GitHub: https://github.com/brajeshpowwal/Ask-your-HR-payroll-Assistant-AI-Chat-Bot-
>
> Have a data problem like this in your team? Let's build the solution together.
>
> #AI #LLM #GenerativeAI #HRTech #Python

## First comment (post it right after publishing)

> 🌐 Live demo (fictional data, ask anything): https://hrpayrollassistant.streamlit.app/
> 💻 Code: https://github.com/brajeshpowwal/Ask-your-HR-payroll-Assistant-AI-Chat-Bot-
> 📖 How it works: README → "How it works"

## Posting tips

- Upload the MP4 natively to LinkedIn (not a YouTube link); native video gets more reach. Add a title such as "TalkToData: ask your HR data in plain English".
- LinkedIn shows fewer people posts with links in the text. If you want maximum reach, remove the two links from the post and keep them only in the first comment.
- Post Tuesday to Thursday morning in your target audience's time zone, and reply to every comment in the first two hours.
- Add the project to your LinkedIn **Featured** and **Projects** sections with the GitHub link.
- Resume line: *"Built a text-to-SQL AI assistant (LLM, LangGraph, Python, SQLite) with 4-layer SQL safety and a 50-question benchmark (78–84% execution accuracy); deployed publicly on Streamlit."*
