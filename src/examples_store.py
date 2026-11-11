"""Find the example question/SQL pairs most similar to a new question.

This is the "retrieval" in RAG: instead of pasting all 30 examples into the
prompt, we pick the few that look most like the user's question.

We use TF-IDF + cosine similarity (scikit-learn). It is free, fast, needs no
model download and works well for short questions. Swapping in neural
embeddings (e.g. Chroma + sentence-transformers) only means changing this file.
"""
from __future__ import annotations

from dataclasses import dataclass

import yaml
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from src.config import Settings, get_settings


@dataclass
class Example:
    question: str
    sql: str
    score: float = 0.0


class ExampleStore:
    def __init__(self, settings: Settings | None = None):
        s = settings or get_settings()
        with open(s.examples_path, encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or []
        self.examples = [Example(r["question"].strip(), r["sql"].strip()) for r in raw]
        # single words and word pairs ("payroll cost", "open exceptions"), common words ignored
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words="english")
        self.matrix = self.vectorizer.fit_transform([e.question for e in self.examples])

    def search(self, question: str, k: int = 4) -> list[Example]:
        if not self.examples:
            return []
        scores = cosine_similarity(self.vectorizer.transform([question]), self.matrix)[0]
        best = scores.argsort()[::-1][:k]
        return [Example(self.examples[i].question, self.examples[i].sql, float(scores[i])) for i in best]
