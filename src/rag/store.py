"""Vector store abstraction: BM25 keyword search + pluggable dense embeddings.

The concrete store choice (EU-hosted, hybrid, metadata-filtering) is deferred to
deployment and wrapped behind this interface (AGENT_ARCHITECTURE.md §8 A3). The
in-memory implementation here is fully deterministic: BM25 is real and needs no
dependency; dense retrieval is optional and injected via the Embedder protocol
(a real EU-hosted embedding model in production; a hashing stub in tests).

# SPEC: KNOWLEDGE_ARCHITECTURE.md §4.2 (Hybrid Retrieval: BM25 + Dense, 0.5/0.5)
# SPEC: KNOWLEDGE_ARCHITECTURE.md §6 (Metadaten-Filter: domaene, gueltig_ab/bis)
"""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from typing import Protocol

from src.rag.chunker import Chunk

# Okapi-BM25-Parameter (Standardwerte; via Eval-Harness kalibrierbar).
_K1 = 1.5
_B = 0.75

# Tokenizer: §/Art.-Zitate als atomare Tokens erhalten (Rechtstexte sind
# zitatgetrieben, exakte §-Treffer schlagen Semantik - KNOWLEDGE_ARCHITECTURE §4.2).
_TOKEN = re.compile(r"§\s*\d+[a-z]?|art\.?\s*\d+[a-z]?|[a-zA-Z0-9äöüß]+", re.IGNORECASE)
_WS = re.compile(r"\s+")


def tokenize(text: str) -> list[str]:
    """Deterministic tokenizer; normalizes §/Art. tokens to a canonical form."""
    tokens: list[str] = []
    for match in _TOKEN.finditer(text.lower()):
        tok = _WS.sub("", match.group(0))
        tok = tok.replace("art.", "art")
        tokens.append(tok)
    return tokens


class Embedder(Protocol):
    """Dense embedding model. Production: EU-hosted; tests: deterministic stub."""

    def embed(self, text: str) -> tuple[float, ...]:
        """Return a fixed-length embedding vector for the text."""
        ...


def _cosine(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


@dataclass
class InMemoryVectorStore:
    """Deterministic in-memory store over a chunk corpus.

    Metadata filtering (domaene, rechtsstand) is applied before scoring so an
    answer never draws on a chunk that isn't valid for the requested legal date.
    """

    chunks: list[Chunk]
    embedder: Embedder | None = None
    _docs: list[list[str]] = field(default_factory=list, init=False)
    _df: Counter[str] = field(default_factory=Counter, init=False)
    _idf: dict[str, float] = field(default_factory=dict, init=False)
    _avgdl: float = field(default=0.0, init=False)
    _vectors: list[tuple[float, ...]] = field(default_factory=list, init=False)

    def __post_init__(self) -> None:
        self._docs = [tokenize(f"{c.einheit} {c.ueberschrift} {c.text}") for c in self.chunks]
        for doc in self._docs:
            for term in set(doc):
                self._df[term] += 1
        n = max(len(self.chunks), 1)
        for term, df in self._df.items():
            # BM25-idf mit +0.5-Glättung
            self._idf[term] = math.log(1 + (n - df + 0.5) / (df + 0.5))
        self._avgdl = (sum(len(d) for d in self._docs) / n) if self.chunks else 0.0
        if self.embedder is not None:
            self._vectors = [self.embedder.embed(c.text) for c in self.chunks]

    def _passt_filter(
        self, chunk: Chunk, domaenen: tuple[str, ...], rechtsstand: date | None
    ) -> bool:
        if domaenen and not any(d in chunk.domaene for d in domaenen):
            return False
        if rechtsstand is not None:
            gueltig_ab = date.fromisoformat(chunk.gueltig_ab)
            gueltig_bis = (
                date.fromisoformat(chunk.gueltig_bis) if chunk.gueltig_bis else date.max
            )
            if not gueltig_ab <= rechtsstand <= gueltig_bis:
                return False
        return True

    def keyword_search(
        self,
        query: str,
        top_n: int,
        domaenen: tuple[str, ...] = (),
        rechtsstand: date | None = None,
    ) -> list[tuple[Chunk, float]]:
        """BM25 keyword ranking over the filtered corpus."""
        q_terms = tokenize(query)
        treffer: list[tuple[Chunk, float]] = []
        for chunk, doc in zip(self.chunks, self._docs, strict=True):
            if not self._passt_filter(chunk, domaenen, rechtsstand):
                continue
            score = self._bm25(q_terms, doc)
            if score > 0.0:
                treffer.append((chunk, score))
        treffer.sort(key=lambda t: t[1], reverse=True)
        return treffer[:top_n]

    def _bm25(self, q_terms: list[str], doc: list[str]) -> float:
        if not doc:
            return 0.0
        tf = Counter(doc)
        dl = len(doc)
        score = 0.0
        for term in q_terms:
            if term not in tf:
                continue
            idf = self._idf.get(term, 0.0)
            freq = tf[term]
            denom = freq + _K1 * (1 - _B + _B * dl / self._avgdl)
            score += idf * (freq * (_K1 + 1)) / denom
        return score

    def dense_search(
        self,
        query: str,
        top_n: int,
        domaenen: tuple[str, ...] = (),
        rechtsstand: date | None = None,
    ) -> list[tuple[Chunk, float]]:
        """Cosine similarity over injected embeddings; empty if no embedder."""
        if self.embedder is None:
            return []
        q_vec = self.embedder.embed(query)
        treffer: list[tuple[Chunk, float]] = []
        for chunk, vec in zip(self.chunks, self._vectors, strict=True):
            if not self._passt_filter(chunk, domaenen, rechtsstand):
                continue
            sim = _cosine(q_vec, vec)
            if sim > 0.0:
                treffer.append((chunk, sim))
        treffer.sort(key=lambda t: t[1], reverse=True)
        return treffer[:top_n]

    def by_ids(self, chunk_ids: set[str]) -> list[Chunk]:
        """Look up chunks by id (for Verweisgraph expansion)."""
        return [c for c in self.chunks if c.chunk_id in chunk_ids]
