"""Embedder factory + dense-path wiring tests (no heavy model, no network).

# SPEC: KNOWLEDGE_ARCHITECTURE.md §4.2 (Hybrid Retrieval BM25 + Dense)
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from src.rag.chunker import Chunk
from src.rag.embeddings import (
    SentenceTransformerEmbedder,
    build_embedder,
    load_embedding_config,
)
from src.rag.store import InMemoryVectorStore
from src.shared.exceptions import ToolInputError

_HAS_ST = importlib.util.find_spec("sentence_transformers") is not None


def _chunk(text: str, cid: str) -> Chunk:
    return Chunk(
        chunk_id=cid, quelle_typ="gesetz", jurisdiktion="DE", gesetz="UStG",
        celex=None, einheit="§ 19", ueberschrift="Test", gueltig_ab="2025-01-01",
        gueltig_bis=None, rechtsstand_abruf="2026-07-07", quelle_url="https://x",
        text=text, hash="sha256:x", typ="norm", domaene=("steuerrecht",),
    )


class TestFactory:
    def test_none_config_kein_embedder(self) -> None:
        assert build_embedder(None) is None

    def test_deaktiviert_kein_embedder(self) -> None:
        assert build_embedder({"enabled": False, "modell": "x"}) is None

    def test_aktiviert_liefert_embedder_lazy(self) -> None:
        emb = build_embedder({"enabled": True, "modell": "mein-modell"})
        assert isinstance(emb, SentenceTransformerEmbedder)
        assert emb.modell == "mein-modell"
        assert emb._model is None  # noch nichts geladen (lazy)

    def test_default_modell_wenn_unbenannt(self) -> None:
        emb = build_embedder({"enabled": True})
        assert isinstance(emb, SentenceTransformerEmbedder) and emb.modell


class TestConfigLaden:
    def test_fehlende_datei_leeres_dict(self, tmp_path: Path) -> None:
        assert load_embedding_config(tmp_path / "gibt-es-nicht.yaml") == {}

    def test_liest_yaml(self, tmp_path: Path) -> None:
        pfad = tmp_path / "embeddings.yaml"
        pfad.write_text("enabled: true\nmodell: abc\n", encoding="utf-8")
        cfg = load_embedding_config(pfad)
        assert cfg["enabled"] is True and cfg["modell"] == "abc"


@pytest.mark.skipif(_HAS_ST, reason="sentence-transformers installiert -> Modell-Load statt Fehler")
def test_embed_ohne_lib_klarer_fehler() -> None:
    with pytest.raises(ToolInputError, match="sentence-transformers"):
        SentenceTransformerEmbedder("x").embed("Testtext")


class TestDensePfad:
    """Beweist die Protokoll-Verdrahtung mit einem deterministischen Fake-Embedder."""

    class _FakeEmbedder:
        def embed(self, text: str) -> tuple[float, ...]:
            # 3-dim, deterministisch: Laenge, Anzahl '§', erster Zeichencode
            return (float(len(text)), float(text.count("§")), float(ord(text[:1] or " ")))

    def test_store_baut_vektoren_und_dense_search_trifft(self) -> None:
        chunks = [
            _chunk("Kleinunternehmer § 19 Grenze 25000 Euro.", "c1"),
            _chunk("Reverse-Charge Regelung fuer Bauleistungen.", "c2"),
        ]
        store = InMemoryVectorStore(chunks, embedder=self._FakeEmbedder())
        assert len(store._vectors) == 2 and len(store._vectors[0]) == 3
        treffer = store.dense_search("Kleinunternehmer Grenze", 5, ("steuerrecht",), None)
        assert treffer  # Dense-Suche liefert Kandidaten (Embedder wird genutzt)

    def test_ohne_embedder_keine_dense_treffer(self) -> None:
        store = InMemoryVectorStore([_chunk("Text", "c1")])  # kein Embedder
        assert store.dense_search("Text", 5, ("steuerrecht",), None) == []
