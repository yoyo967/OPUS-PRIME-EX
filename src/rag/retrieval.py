"""Hybrid retrieval pipeline feeding the orchestrator's rag_suche.

Pipeline (KNOWLEDGE_ARCHITECTURE.md §4):
  Query-Analyse -> Hybrid Retrieval (BM25 + Dense, 0.5/0.5) -> Struktur-Expansion
  (Verweisgraph) -> Re-Ranking (deterministischer Bonus) -> Kontextkomposition
  (Prioritaet Norm > Verwaltung > Rechtsprechung > Leitlinie, 12k-Token-Budget).

The deterministic re-ranking (bonus for primary sources, valid Fassung) is done
here; the optional Haiku LLM re-ranker (§4.4) is a later refinement behind the
same interface. build_rag_suche() closes over a store and returns the exact
callable the orchestrator injects.

# SPEC: KNOWLEDGE_ARCHITECTURE.md §4 (RAG-Strategie), §5 (Verweisgraph), §4.5 (12k)
# SPEC: AGENT_ARCHITECTURE.md §3.1 (rag_suche: query, domaene[], rechtsstand, max_chunks)
"""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import date

from src.rag.chunker import Chunk, estimate_tokens
from src.rag.store import InMemoryVectorStore

RagSuche = Callable[[str, tuple[str, ...]], list[Chunk]]

# SPEC: KNOWLEDGE_ARCHITECTURE.md §4.5 (hartes Budget 12k Tokens Kontext)
KONTEXT_TOKEN_BUDGET = 12_000
# SPEC: KNOWLEDGE_ARCHITECTURE.md §4.2 (Gewichtung 0,5/0,5)
_W_KEYWORD = 0.5
_W_DENSE = 0.5
# Top-30 Kandidaten -> Top-8 (KNOWLEDGE_ARCHITECTURE.md §4.4)
_KANDIDATEN = 30
_DEFAULT_MAX_CHUNKS = 8

# Kompositions-Prioritaet (§4.5: Norm > Verwaltung > Rechtsprechung > Leitlinie).
_PRIO = {
    "gesetz": 0,
    "eu_verordnung": 0,
    "bmf": 1,
    "urteil": 2,
    "leitlinie": 3,
    "sekundaer": 4,
}
# Re-Ranking-Bonus fuer Primaerquellen (§4.4 "Bonus fuer Primaerquelle").
_QUELLE_BONUS = {"gesetz": 0.30, "eu_verordnung": 0.30, "bmf": 0.15, "urteil": 0.10}

_DE_ZITAT = re.compile(r"§\s*(\d+[a-z]?)\s*([A-ZÄÖÜ][A-Za-zÄÖÜäöüß]*G|AO|GewO|UStDV)")
_EU_ZITAT = re.compile(r"Art\.\s*(\d+[a-z]?).{0,40}?(DSGVO|UMV|VO\s*\(EU\)\s*\d{4}/\d+)")


def _explizite_zitate(query: str) -> list[str]:
    """Extract explicit norm references so a direct §-hit is boosted (§4.1)."""
    treffer: list[str] = []
    for m in _DE_ZITAT.finditer(query):
        treffer.append(f"§ {m.group(1)}")
    for m in _EU_ZITAT.finditer(query):
        treffer.append(f"Art. {m.group(1)}")
    return treffer


def _normalisiere(paare: list[tuple[Chunk, float]]) -> dict[str, float]:
    """Min-max-normalize scores to [0,1], keyed by chunk_id."""
    if not paare:
        return {}
    werte = [s for _, s in paare]
    lo, hi = min(werte), max(werte)
    spanne = hi - lo
    if spanne == 0.0:
        return {c.chunk_id: 1.0 for c, _ in paare}
    return {c.chunk_id: (s - lo) / spanne for c, s in paare}


def _komponiere(
    kandidaten: list[tuple[Chunk, float]], max_chunks: int
) -> list[Chunk]:
    """Re-rank by score, then trim to max_chunks under the 12k token budget.

    On overflow the lowest-priority, lowest-score chunk is dropped first
    (SPEC: KNOWLEDGE_ARCHITECTURE.md §4.5).
    """
    kandidaten.sort(key=lambda t: t[1], reverse=True)
    ausgewaehlt: list[tuple[Chunk, float]] = []
    tokens = 0
    for chunk, score in kandidaten:
        if len(ausgewaehlt) >= max_chunks:
            break
        chunk_tokens = estimate_tokens(chunk.text)
        if tokens + chunk_tokens > KONTEXT_TOKEN_BUDGET and ausgewaehlt:
            continue
        ausgewaehlt.append((chunk, score))
        tokens += chunk_tokens
    # Kontext geordnet nach Prioritaet, dann Score (§4.5).
    ausgewaehlt.sort(key=lambda t: (_PRIO.get(t[0].quelle_typ, 5), -t[1]))
    return [c for c, _ in ausgewaehlt]


def retrieve(
    store: InMemoryVectorStore,
    query: str,
    domaenen: tuple[str, ...] = (),
    rechtsstand: date | None = None,
    max_chunks: int = _DEFAULT_MAX_CHUNKS,
) -> list[Chunk]:
    """Run the full hybrid pipeline for one query."""
    keyword = store.keyword_search(query, _KANDIDATEN, domaenen, rechtsstand)
    dense = store.dense_search(query, _KANDIDATEN, domaenen, rechtsstand)

    kw_norm = _normalisiere(keyword)
    dense_norm = _normalisiere(dense)
    fusion: dict[str, float] = {}
    chunk_by_id: dict[str, Chunk] = {}
    for chunk, _ in keyword:
        chunk_by_id[chunk.chunk_id] = chunk
    for chunk, _ in dense:
        chunk_by_id.setdefault(chunk.chunk_id, chunk)
    for cid in set(kw_norm) | set(dense_norm):
        fusion[cid] = _W_KEYWORD * kw_norm.get(cid, 0.0) + _W_DENSE * dense_norm.get(cid, 0.0)

    # Direkter Norm-Lookup: explizite Zitate in der Frage stark boosten (§4.1).
    zitate = _explizite_zitate(query)
    if zitate:
        for chunk in chunk_by_id.values():
            if any(chunk.einheit.startswith(z) for z in zitate):
                fusion[chunk.chunk_id] = fusion.get(chunk.chunk_id, 0.0) + 0.5

    # Struktur-Expansion: verwiesene Normen der Top-Kandidaten nachladen (§4.3).
    top_ids = sorted(fusion, key=lambda c: fusion[c], reverse=True)[:8]
    verweis_ids: set[str] = set()
    for cid in top_ids:
        top_chunk = chunk_by_id.get(cid)
        if top_chunk is not None:
            verweis_ids.update(top_chunk.verweist_auf)
    for chunk in store.by_ids(verweis_ids - set(chunk_by_id)):
        chunk_by_id[chunk.chunk_id] = chunk
        fusion.setdefault(chunk.chunk_id, 0.15)  # nachgeladen: niedrigeres Gewicht

    # Re-Ranking: deterministischer Primaerquellen-Bonus (§4.4).
    kandidaten: list[tuple[Chunk, float]] = []
    for cid, score in fusion.items():
        chunk = chunk_by_id[cid]
        final = score + _QUELLE_BONUS.get(chunk.quelle_typ, 0.0)
        kandidaten.append((chunk, final))
    kandidaten.sort(key=lambda t: t[1], reverse=True)
    return _komponiere(kandidaten[:_KANDIDATEN], max_chunks)


def build_rag_suche(
    store: InMemoryVectorStore,
    rechtsstand: date | None = None,
    max_chunks: int = _DEFAULT_MAX_CHUNKS,
) -> RagSuche:
    """Return the orchestrator-shaped rag_suche closing over the store.

    # SPEC: AGENT_ARCHITECTURE.md §3.1 (rechtsstand default heute)
    """
    def _suche(query: str, domaenen: tuple[str, ...]) -> list[Chunk]:
        stichtag = rechtsstand if rechtsstand is not None else date.today()
        return retrieve(store, query, domaenen, stichtag, max_chunks)

    return _suche
