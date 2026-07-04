"""
Pure-Python TF-IDF semantic search over hidden gems data.

Uses only Python stdlib (math, re, collections) — zero network calls,
zero downloads, works fully offline in air-gapped Docker environments.
Replaces ChromaDB + fastembed/sentence-transformers entirely.
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)


def _tokenize(text: str) -> list[str]:
    """Lowercase, remove punctuation, split on whitespace."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return [t for t in text.split() if len(t) > 1]


class VectorStore:
    """
    In-memory TF-IDF search over hidden gems JSON data.

    - Pure Python stdlib — no pip packages required
    - No runtime downloads (HuggingFace, etc.)
    - All indexing done at seed time; search is fast
    - Supports continent-based metadata filtering
    """

    def __init__(self) -> None:
        self._docs: list[dict[str, Any]] = []
        self._corpus: list[str] = []
        self._tf_idf: list[dict[str, float]] = []
        self._idf: dict[str, float] = {}
        logger.info("vector_store_initialized", backend="pure-python-tfidf")

    # ── Indexing ──────────────────────────────────────────────────────────────

    def seed_from_file(self, data_path: Path) -> int:
        """Load and index gems from JSON. Idempotent."""
        if not data_path.exists():
            logger.warning("seed_file_not_found", path=str(data_path))
            return 0

        if self._docs:
            logger.info("vector_store_already_seeded", count=len(self._docs))
            return 0

        with data_path.open() as f:
            gems: list[dict[str, Any]] = json.load(f)

        self._docs = gems
        self._corpus = [
            (
                f"{g['name']} {g.get('country', '')} {g.get('continent', '')} "
                f"{g.get('description', '')} "
                f"{' '.join(g.get('tags', []))} "
                f"{g.get('best_season', '')} {g.get('tourist_density', '')}"
            )
            for g in gems
        ]
        self._build_index()
        logger.info("vector_store_seeded", count=len(gems))
        return len(gems)

    def _build_index(self) -> None:
        """Compute and store normalised TF-IDF vectors for every document."""
        N = len(self._corpus)
        tokenized = [_tokenize(doc) for doc in self._corpus]

        # Document frequency
        df: dict[str, int] = {}
        for tokens in tokenized:
            for term in set(tokens):
                df[term] = df.get(term, 0) + 1

        # IDF with smoothing
        self._idf = {
            term: math.log((N + 1) / (freq + 1)) + 1.0
            for term, freq in df.items()
        }

        # TF-IDF vectors, L2-normalised
        self._tf_idf = []
        for tokens in tokenized:
            tf = Counter(tokens)
            total = sum(tf.values()) or 1
            vec = {
                term: (cnt / total) * self._idf.get(term, 1.0)
                for term, cnt in tf.items()
            }
            norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
            self._tf_idf.append({k: v / norm for k, v in vec.items()})

    # ── Search ────────────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        n_results: int = 6,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Cosine-similarity search over indexed gems.
        Optional `where={"continent": "Asia"}` for continent filtering.
        """
        if not self._docs:
            return []

        # Build query vector
        q_tokens = _tokenize(query)
        q_tf = Counter(q_tokens)
        q_total = sum(q_tf.values()) or 1
        q_vec: dict[str, float] = {
            term: (cnt / q_total) * self._idf.get(term, 1.0)
            for term, cnt in q_tf.items()
        }
        q_norm = math.sqrt(sum(v * v for v in q_vec.values())) or 1.0
        q_vec = {k: v / q_norm for k, v in q_vec.items()}

        # Score documents
        scored: list[tuple[float, int]] = []
        for idx, doc_vec in enumerate(self._tf_idf):
            gem = self._docs[idx]

            # Optional continent filter
            if where and "continent" in where:
                if gem.get("continent", "").lower() != where["continent"].lower():
                    continue

            sim = sum(
                q_vec.get(term, 0.0) * doc_vec.get(term, 0.0)
                for term in q_vec
            )
            scored.append((sim, idx))

        scored.sort(reverse=True)

        results = []
        for sim, idx in scored[:n_results]:
            gem = self._docs[idx]
            results.append(
                {
                    "document": self._corpus[idx],
                    "metadata": {
                        "name": gem["name"],
                        "country": gem.get("country", ""),
                        "continent": gem.get("continent", ""),
                        "lat": gem.get("lat", 0.0),
                        "lng": gem.get("lng", 0.0),
                        "authenticity_score": gem.get("authenticity_score", 7.0),
                        "tourist_density": gem.get("tourist_density", "low"),
                        "best_season": gem.get("best_season", "year-round"),
                        "tags": gem.get("tags", []),
                        "image_hint": gem.get("image_hint", ""),
                        "ai_pitch": gem.get("ai_pitch", ""),
                        "description": gem.get("description", ""),
                    },
                    "similarity": round(sim, 4),
                }
            )
        return results


# ── Singleton ─────────────────────────────────────────────────────────────────
_vector_store: VectorStore | None = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
