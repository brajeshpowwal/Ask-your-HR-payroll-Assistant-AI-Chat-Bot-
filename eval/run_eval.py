"""Measure how accurate the assistant is on the 50-question test set.

For each question we run the agent, then run the hand-written "gold" SQL, and
compare the two RESULTS (not the SQL text, since many different queries are
equally correct). This is called execution accuracy.

Usage:
    python eval/run_eval.py                       # provider from .env
    python eval/run_eval.py --provider gemini     # another provider
    python eval/run_eval.py --limit 10            # quick check
    python eval/run_eval.py --difficulty hard
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.agent import SQLAgent  # noqa: E402
from src.config import get_settings  # noqa: E402
from src.db import run_query  # noqa: E402
from src.llm_factory import get_llm  # noqa: E402


def _norm(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "NULL"
    if isinstance(value, (int, float)):
        return f"{round(float(value), 1):.1f}"
    try:
        return f"{round(float(value), 1):.1f}"
    except (TypeError, ValueError):
        return str(value).strip().lower()


def results_match(expected: pd.DataFrame, predicted: pd.DataFrame | None) -> bool:
    """True when every expected column appears in the prediction with the same values.

    Row order, column order, column names and extra columns are ignored, because
    those do not change whether the answer is right.
    """
    if predicted is None or len(expected) != len(predicted):
        return False
    if expected.empty:
        return True
    pred_cols = [sorted(_norm(v) for v in predicted[c]) for c in predicted.columns]
    used: set[int] = set()
    for col in expected.columns:
        target = sorted(_norm(v) for v in expected[col])
        hit = next((i for i, p in enumerate(pred_cols) if i not in used and p == target), None)
        if hit is None:
            return False
        used.add(hit)
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider")
    parser.add_argument("--model")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--difficulty", choices=["easy", "medium", "hard"])
    parser.add_argument("--sleep", type=float, default=1.0, help="pause between questions (free-tier rate limits)")
    args = parser.parse_args()

    overrides = {k: v for k, v in {"provider": args.provider, "model": args.model}.items() if v}
    settings = get_settings(**overrides)
    agent = SQLAgent(get_llm(settings), settings)

    questions = [json.loads(line) for line in open(ROOT / "eval" / "questions.jsonl", encoding="utf-8")]
    if args.difficulty:
        questions = [q for q in questions if q["difficulty"] == args.difficulty]
    if args.limit:
        questions = questions[: args.limit]

    rows = []
    for i, q in enumerate(questions, 1):
        expected = run_query(q["sql"], settings.db_path)
        try:
            res = agent.ask(q["question"])
            correct = res.status == "ok" and results_match(expected, res.data)
            rows.append({"id": q["id"], "difficulty": q["difficulty"], "question": q["question"],
                         "correct": correct, "status": res.status, "valid_sql": res.status == "ok",
                         "attempts": res.attempts, "retries": max(0, res.attempts - 1),
                         "seconds": res.seconds, "sql": res.sql})
        except Exception as exc:  # rate limit, network…
            rows.append({"id": q["id"], "difficulty": q["difficulty"], "question": q["question"],
                         "correct": False, "status": f"error: {exc}", "valid_sql": False,
                         "attempts": 0, "retries": 0, "seconds": 0.0, "sql": ""})
        mark = "PASS" if rows[-1]["correct"] else "FAIL"
        print(f"[{i:>2}/{len(questions)}] {mark}  {q['id']}  {q['question']}")
        time.sleep(args.sleep)

    df = pd.DataFrame(rows)
    out_dir = ROOT / "eval" / "results"
    out_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    out = out_dir / f"{settings.provider}_{settings.model_name.replace('/', '-')}_{stamp}.csv"
    df.to_csv(out, index=False)

    def pct(series) -> str:
        return f"{100 * series.mean():.0f}%" if len(series) else "-"

    print("\n| Provider | Model | Questions | Execution accuracy | Easy | Medium | Hard "
          "| Valid SQL | Avg retries | Avg seconds |")
    print("|---|---|---|---|---|---|---|---|---|---|")
    by = {d: df[df.difficulty == d]["correct"] for d in ("easy", "medium", "hard")}
    print(f"| {settings.provider} | {settings.model_name} | {len(df)} | {pct(df.correct)} | {pct(by['easy'])} | "
          f"{pct(by['medium'])} | {pct(by['hard'])} | {pct(df.valid_sql)} | {df.retries.mean():.2f} | "
          f"{df.seconds.mean():.1f} |")
    print(f"\nDetails saved to {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
