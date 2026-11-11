"""Few-shot examples must not leak benchmark questions, or the accuracy number means nothing."""
import json
from pathlib import Path

import yaml
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

ROOT = Path(__file__).resolve().parent.parent
# TF-IDF word overlap: a lightly re-worded eval question scores ~0.98, while genuinely
# different questions on the same topic (other grouping or period) score up to ~0.77.
MAX_SIMILARITY = 0.85


def _questions():
    examples = [e["question"] for e in yaml.safe_load((ROOT / "data" / "examples.yaml").read_text("utf-8"))]
    lines = (ROOT / "eval" / "questions.jsonl").read_text("utf-8").splitlines()
    evals = [json.loads(line)["question"] for line in lines if line.strip()]
    return examples, evals


def test_no_eval_question_is_an_example():
    examples, evals = _questions()
    assert not {q.lower() for q in examples} & {q.lower() for q in evals}


def test_examples_are_not_near_copies_of_eval_questions():
    examples, evals = _questions()
    vec = TfidfVectorizer().fit(examples + evals)
    sims = cosine_similarity(vec.transform(examples), vec.transform(evals))
    too_close = [(examples[i], evals[j], round(float(sims[i, j]), 2))
                 for i in range(len(examples)) for j in range(len(evals)) if sims[i, j] > MAX_SIMILARITY]
    assert not too_close, too_close
