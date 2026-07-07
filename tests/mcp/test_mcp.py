"""MCP-Tool-Logik-Tests (dependency-frei, ohne mcp-SDK/Netz).

Prueft die geteilte Faehigkeit (rechtsquellen_suche), die der MCP-Server exponiert.

# ADR: opus-deck ADR-0002 (MCP-Rueckgrat)
"""

from __future__ import annotations

from src.mcp_server.tools import suche_rechtsquellen
from src.rag.chunker import Chunk
from src.rag.store import InMemoryVectorStore


def _chunk(einheit: str, text: str) -> Chunk:
    return Chunk(
        chunk_id=f"de-ustg-2025-01-01-{einheit.replace(' ', '').replace('§', 'p').lower()}",
        quelle_typ="gesetz", jurisdiktion="DE", gesetz="UStG", celex=None,
        einheit=einheit, ueberschrift="Besteuerung der Kleinunternehmer",
        gueltig_ab="2025-01-01", gueltig_bis=None, rechtsstand_abruf="2026-07-07",
        quelle_url="https://www.gesetze-im-internet.de/ustg_1980/__19.html",
        text=text, hash="sha256:x", typ="norm", domaene=("steuerrecht",),
    )


def _store() -> InMemoryVectorStore:
    return InMemoryVectorStore([
        _chunk("§ 19", "Kleinunternehmer: 25 000 Euro Vorjahr, 100 000 Euro laufend."),
        _chunk("§ 1", "Steuerbare Umsaetze im Inland gegen Entgelt."),
    ])


class TestRechtsquellenSuche:
    def test_findet_relevante_quelle_als_dicts(self) -> None:
        treffer = suche_rechtsquellen("Kleinunternehmer Grenze Umsatzsteuer", _store(), k=5)
        assert treffer, "mindestens ein Treffer"
        top = treffer[0]
        # Maschinenlesbarer Zitierkopf + Auszug fuer MCP-Clients
        assert set(top) >= {"id", "quelle", "einheit", "ueberschrift", "auszug", "url"}
        ids = [t["id"] for t in treffer]
        assert any("p19" in i for i in ids)  # § 19 UStG ist dabei

    def test_k_begrenzt_die_trefferzahl(self) -> None:
        treffer = suche_rechtsquellen("Umsatzsteuer Kleinunternehmer", _store(), k=1)
        assert len(treffer) <= 1

    def test_quelle_und_auszug_gefuellt(self) -> None:
        top = suche_rechtsquellen("Kleinunternehmer Grenze", _store(), k=1)[0]
        assert top["quelle"] == "UStG"
        assert top["auszug"] and len(top["auszug"]) <= 280
