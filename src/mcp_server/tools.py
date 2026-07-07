"""MCP-Tool-Logik (dependency-frei, offline testbar).

Die eigentlichen Faehigkeiten als plain Funktionen; server.py registriert sie duenn
als MCP-Tools. So laufen Tests ohne das mcp-SDK und ohne Netz.

# SPEC: KNOWLEDGE_ARCHITECTURE.md §4 (Retrieval); ADR-0002 (MCP)
"""

from __future__ import annotations

from typing import Any

from src.rag.retrieval import build_rag_suche
from src.rag.store import InMemoryVectorStore
from src.router.classifier import classify


def suche_rechtsquellen(
    query: str, store: InMemoryVectorStore, k: int = 5
) -> list[dict[str, Any]]:
    """Relevante deutsche/EU-Rechtsquellen zur Anfrage (Hybrid-Retrieval).

    Domaenen werden wie in der Pipeline deterministisch klassifiziert; das Ergebnis ist
    eine kompakte, maschinenlesbare Trefferliste (Zitierkopf + Auszug) fuer MCP-Clients.
    """
    klass = classify(query)
    rag_suche = build_rag_suche(store)
    treffer = rag_suche(query, klass.domaenen)[: max(1, k)]
    return [
        {
            "id": c.chunk_id,
            "quelle": c.gesetz or (f"CELEX {c.celex}" if c.celex else "?"),
            "einheit": c.einheit,
            "ueberschrift": c.ueberschrift,
            "auszug": c.text[:280],
            "gueltig_ab": c.gueltig_ab,
            "url": c.quelle_url,
        }
        for c in treffer
    ]
