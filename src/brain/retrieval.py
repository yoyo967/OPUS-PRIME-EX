"""Brain-Retrieval — reuset die OPUS-PRIME-EX-RAG-Engine (Hybrid BM25 + optional Embeddings).

BrainDocs werden auf das Chunk-Format gemappt und in den getesteten InMemoryVectorStore
gegeben; `brain_search` liefert eine maschinenlesbare Trefferliste fuer MCP-Clients.

# SPEC: opus-deck/spec/SECOND_BRAIN.md §4 (Retrieval: Wiki-first + Raw-Fallback)
"""

from __future__ import annotations

from typing import Any

from src.brain.store import BrainDoc
from src.rag.chunker import Chunk
from src.rag.store import Embedder, InMemoryVectorStore


def _to_chunk(doc: BrainDoc) -> Chunk:
    # Brain-Doc auf das getestete Chunk-Format abbilden (einheit leer -> kein Token-Rauschen;
    # domaene leer -> keyword_search filtert nicht). Datumsfelder sind neutrale Platzhalter,
    # da Brain-Retrieval keinen Rechtsstand-Filter nutzt.
    return Chunk(
        chunk_id=doc.id, quelle_typ="brain", jurisdiktion="", gesetz=doc.titel, celex=None,
        einheit="", ueberschrift=doc.titel, gueltig_ab="2026-01-01", gueltig_bis=None,
        rechtsstand_abruf="2026-01-01", quelle_url=doc.id, text=doc.text,
        hash="sha256:brain", typ="norm", domaene=(),
    )


def build_brain_index(
    docs: list[BrainDoc], embedder: Embedder | None = None
) -> InMemoryVectorStore:
    """Build a searchable index over brain documents (raw + wiki)."""
    return InMemoryVectorStore([_to_chunk(d) for d in docs], embedder=embedder)


def brain_search(index: InMemoryVectorStore, query: str, k: int = 5) -> list[dict[str, Any]]:
    """Hybrid-Suche ueber das Gehirn; kompakte Trefferliste (id, titel, schicht, auszug)."""
    treffer = index.keyword_search(query, max(1, k))  # domaenen=() -> alle Dokumente
    return [
        {
            "id": c.chunk_id,
            "titel": c.ueberschrift,
            "schicht": "wiki" if c.chunk_id.startswith("wiki/") else "raw",
            "auszug": c.text[:280],
            "score": round(score, 3),
        }
        for c, score in treffer
    ]
