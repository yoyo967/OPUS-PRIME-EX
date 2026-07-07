"""Hybrid-retrieval tests over the real ingest fixtures.

# SPEC: KNOWLEDGE_ARCHITECTURE.md §4 (RAG-Strategie), §5 (Verweisgraph), §4.5 (Budget)
"""

from __future__ import annotations

import hashlib
from datetime import date
from pathlib import Path

from src.rag.chunker import Chunk, chunk_de_gesetz, chunk_eu_verordnung
from src.rag.retrieval import KONTEXT_TOKEN_BUDGET, build_rag_suche, retrieve
from src.rag.store import InMemoryVectorStore, tokenize

FIXTURES = Path(__file__).resolve().parent.parent.parent / "data" / "fixtures"


def _lade(pfad: str) -> str:
    return (FIXTURES / pfad).read_text(encoding="utf-8")


def _corpus() -> list[Chunk]:
    chunks: list[Chunk] = []
    chunks += chunk_de_gesetz(
        _lade("de/ustg_p19.xml"), "UStG", "2025-01-01", "2026-07-05",
        "https://www.gesetze-im-internet.de/ustg/__19.html", ("steuerrecht",),
    )
    chunks += chunk_de_gesetz(
        _lade("de/markeng_p42.xml"), "MarkenG", "2025-01-01", "2026-07-05",
        "https://www.gesetze-im-internet.de/markeng/__42.html", ("markenrecht",),
    )
    chunks += chunk_eu_verordnung(
        _lade("eu/dsgvo_art28.xml"), "32016R0679", "2018-05-25", "2026-07-05",
        "https://eur-lex.europa.eu/legal-content/DE/TXT/?uri=CELEX:32016R0679", ("dsgvo",),
    )
    return chunks


class _HashEmbedder:
    """Deterministic bag-of-tokens embedding (stable hash, no dependency)."""

    def __init__(self, dim: int = 64) -> None:
        self.dim = dim

    def embed(self, text: str) -> tuple[float, ...]:
        vec = [0.0] * self.dim
        for tok in tokenize(text):
            idx = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16) % self.dim
            vec[idx] += 1.0
        return tuple(vec)


class TestTokenizer:
    def test_paragraf_und_artikel_atomar(self) -> None:
        assert "§19" in tokenize("Nach § 19 UStG gilt")
        assert "art28" in tokenize("gemäß Art. 28 DSGVO")


class TestKeywordSearch:
    def test_bm25_findet_kleinunternehmer_paragraph(self) -> None:
        store = InMemoryVectorStore(_corpus())
        # Terme, die verbatim im § 19-Volltext stehen (§ 19a ist nur die EU-Norm)
        treffer = store.keyword_search("Steuer Kalenderjahr Euro", 5, ("steuerrecht",))
        assert treffer
        assert treffer[0][0].einheit == "§ 19"

    def test_domaene_filter_schliesst_fremde_domaene_aus(self) -> None:
        store = InMemoryVectorStore(_corpus())
        # Nur markenrecht: DSGVO/UStG-Chunks sind ausgefiltert
        treffer = store.keyword_search("Widerspruch Frist", 5, ("markenrecht",))
        assert all(c.domaene == ("markenrecht",) for c, _ in treffer)

    def test_rechtsstand_filter(self) -> None:
        store = InMemoryVectorStore(_corpus())
        # § 19 UStG gilt ab 2025 -> 2024 filtert es aus
        alt = store.keyword_search("Kleinunternehmer", 5, ("steuerrecht",), date(2024, 6, 1))
        neu = store.keyword_search("Kleinunternehmer", 5, ("steuerrecht",), date(2026, 6, 1))
        assert alt == []
        assert neu


class TestHybridPipeline:
    def test_retrieve_liefert_relevanten_chunk_zuerst(self) -> None:
        store = InMemoryVectorStore(_corpus(), embedder=_HashEmbedder())
        chunks = retrieve(store, "Steuer Kalenderjahr Euro Kleinunternehmer", ("steuerrecht",))
        assert chunks
        assert chunks[0].einheit == "§ 19"

    def test_explizites_zitat_wird_geboostet(self) -> None:
        store = InMemoryVectorStore(_corpus())
        chunks = retrieve(store, "Was sagt § 19 UStG?", ("steuerrecht",))
        assert any(c.einheit == "§ 19" for c in chunks)

    def test_dsgvo_artikel_gefunden(self) -> None:
        store = InMemoryVectorStore(_corpus(), embedder=_HashEmbedder())
        chunks = retrieve(store, "Auftragsverarbeiter Vertrag Pflichten", ("dsgvo",))
        assert any(c.celex == "32016R0679" for c in chunks)


class TestStrukturExpansion:
    def _norm(self, einheit: str, chunk_id: str, text: str, verweist: tuple[str, ...]) -> Chunk:
        return Chunk(
            chunk_id=chunk_id, quelle_typ="gesetz", jurisdiktion="DE", gesetz="UStG",
            celex=None, einheit=einheit, ueberschrift="Test", gueltig_ab="2025-01-01",
            gueltig_bis=None, rechtsstand_abruf="2026-07-05", quelle_url="https://x",
            text=text, hash="sha256:x", typ="norm", domaene=("steuerrecht",),
            verweist_auf=verweist,
        )

    def test_verweisgraph_laedt_referenzierte_norm_nach(self) -> None:
        # § 19 verweist auf § 19a; § 19a hat KEINEN Keyword-Treffer zur Frage
        p19 = self._norm("§ 19", "p19", "Kleinunternehmer Grenze", ("p19a",))
        p19a = self._norm("§ 19a", "p19a", "voellig anderes Thema xyz", ())
        store = InMemoryVectorStore([p19, p19a])
        chunks = retrieve(store, "Kleinunternehmer Grenze", ("steuerrecht",))
        ids = {c.chunk_id for c in chunks}
        assert "p19" in ids and "p19a" in ids  # nachgeladen ueber verweist_auf


class TestKompositionBudget:
    def _grosser_chunk(self, i: int) -> Chunk:
        return Chunk(
            chunk_id=f"c{i}", quelle_typ="gesetz", jurisdiktion="DE", gesetz="UStG",
            celex=None, einheit=f"§ {i}", ueberschrift="Test", gueltig_ab="2025-01-01",
            gueltig_bis=None, rechtsstand_abruf="2026-07-05", quelle_url="https://x",
            text="wort " * 5000, hash="sha256:x", typ="norm", domaene=("steuerrecht",),
        )

    def test_12k_budget_begrenzt_kontext(self) -> None:
        # 5 Chunks à ~6750 Tokens: das 12k-Budget laesst nur ~1 zu
        store = InMemoryVectorStore([self._grosser_chunk(i) for i in range(1, 6)])
        chunks = retrieve(store, "wort", ("steuerrecht",), max_chunks=8)
        from src.rag.chunker import estimate_tokens

        gesamt = sum(estimate_tokens(c.text) for c in chunks)
        assert gesamt <= KONTEXT_TOKEN_BUDGET
        assert len(chunks) >= 1

    def test_max_chunks_cap(self) -> None:
        store = InMemoryVectorStore(_corpus())
        chunks = retrieve(store, "Recht", ("steuerrecht", "markenrecht", "dsgvo"), max_chunks=2)
        assert len(chunks) <= 2


class TestZitatGesetzBoost:
    def _p147(self, gesetz: str, cid: str) -> Chunk:
        return Chunk(
            chunk_id=cid, quelle_typ="gesetz", jurisdiktion="DE", gesetz=gesetz,
            celex=None, einheit="§ 147", ueberschrift="Aufbewahrung", gueltig_ab="2024-01-01",
            gueltig_bis=None, rechtsstand_abruf="2026-07-06", quelle_url="https://x",
            text="Aufbewahrungspflichten Unterlagen Jahre.", hash="sha256:x",
            typ="norm", domaene=("steuerrecht",),
        )

    def test_genanntes_gesetz_rankt_vor_gleicher_nummer(self) -> None:
        # § 147 gibt es in AO und HGB; "§ 147 AO" muss die AO-Norm zuerst liefern
        store = InMemoryVectorStore([self._p147("HGB", "hgb147"), self._p147("AO", "ao147")])
        chunks = retrieve(store, "Was regelt § 147 AO zur Aufbewahrung?", ("steuerrecht",))
        assert chunks[0].chunk_id == "ao147"


class TestBuildRagSuche:
    def test_liefert_orchestrator_callable(self) -> None:
        store = InMemoryVectorStore(_corpus())
        rag_suche = build_rag_suche(store, rechtsstand=date(2026, 7, 5))
        chunks = rag_suche("Steuer Kalenderjahr Euro", ("steuerrecht",))
        assert chunks and chunks[0].einheit == "§ 19"

    def test_integriert_mit_orchestrator(self) -> None:
        # Der Retrieval-Callable wird direkt vom Orchestrator akzeptiert.
        from collections.abc import Sequence

        from src.orchestrator.orchestrator import Antwort, run
        from src.router.router import Klassifikation, Risikosignale, Route

        store = InMemoryVectorStore(_corpus())
        rag_suche = build_rag_suche(store, rechtsstand=date(2026, 7, 5))

        class _FakeLLM:
            def generate(
                self, route: Route, anfrage: str, chunks: Sequence[Chunk],
                korrektur_hinweis: str | None,
            ) -> str:
                return "Nach § 19 UStG gilt Folgendes."

        klass = Klassifikation(
            domaenen=("steuerrecht",), signale=Risikosignale(False, False, (), ())
        )
        # Frage mit Termen, die verbatim im § 19-Text stehen -> Chunk wird retrieved,
        # G3 validiert das "§ 19 UStG"-Zitat der LLM-Antwort dagegen.
        frage = "Wie hoch ist die Steuer im Kalenderjahr für Kleinunternehmer (Euro-Grenzen)?"
        antwort: Antwort = run(frage, klass, _FakeLLM(), rag_suche)
        assert "de-ustg-2025-01-01-p19" in antwort.quellen_ids
