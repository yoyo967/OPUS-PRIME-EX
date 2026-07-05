"""Ingest fixture tests: chunk boundaries and metadata per spec.

# SPEC: CLAUDE.md §4.2 (fixtures must chunk to expected boundaries with correct metadata)
# SPEC: KNOWLEDGE_ARCHITECTURE.md §7 (Ingest-Tests: § 19 UStG, Art. 28 DSGVO,
# Art. 6 + Anhang III AI Act, Art. 5 Data Act, § 42 MarkenG + Art. 46 UMV)
"""

from pathlib import Path

from src.rag.chunker import (
    MAX_TOKENS_PER_CHUNK,
    Chunk,
    chunk_de_gesetz,
    chunk_eu_verordnung,
    estimate_tokens,
)

FIXTURES = Path(__file__).resolve().parent.parent.parent / "data" / "fixtures"


def _lade(pfad: str) -> str:
    return (FIXTURES / pfad).read_text(encoding="utf-8")


class TestDeGesetz:
    def test_ustg_p19_ein_chunk_pro_paragraph(self) -> None:
        chunks = chunk_de_gesetz(
            _lade("de/ustg_p19.xml"),
            gesetz="UStG",
            gueltig_ab="2025-01-01",
            rechtsstand_abruf="2026-07-05",
            quelle_url="https://www.gesetze-im-internet.de/ustg/__19.html",
            domaene=("steuerrecht",),
        )
        ids = [c.chunk_id for c in chunks]
        assert ids == ["de-ustg-2025-01-01-p19", "de-ustg-2025-01-01-p19a"]
        p19 = chunks[0]
        assert p19.einheit == "§ 19"
        assert p19.ueberschrift == "Besteuerung der Kleinunternehmer"
        assert p19.quelle_typ == "gesetz"
        assert p19.jurisdiktion == "DE"
        assert p19.parent_id is None
        assert p19.hash.startswith("sha256:")
        assert "25 000 Euro" in p19.text and "100 000 Euro" in p19.text

    def test_markeng_p42_metadaten(self) -> None:
        chunks = chunk_de_gesetz(
            _lade("de/markeng_p42.xml"),
            gesetz="MarkenG",
            gueltig_ab="2025-01-01",
            rechtsstand_abruf="2026-07-05",
            quelle_url="https://www.gesetze-im-internet.de/markeng/__42.html",
            domaene=("markenrecht",),
        )
        assert len(chunks) == 1
        p42 = chunks[0]
        assert p42.chunk_id == "de-markeng-2025-01-01-p42"
        assert p42.einheit == "§ 42"
        assert p42.domaene == ("markenrecht",)
        # DE-Frist laeuft ab Veroeffentlichung der EINTRAGUNG (Addendum-verifiziert)
        assert "Eintragung" in p42.text

    def test_langer_paragraph_split_auf_absatz_ebene(self) -> None:
        chunks = chunk_de_gesetz(
            _lade("de/synthetisch_langer_paragraph.xml"),
            gesetz="TESTG",
            gueltig_ab="2026-01-01",
            rechtsstand_abruf="2026-07-05",
            quelle_url="https://example.invalid/testg",
            domaene=("steuerrecht",),
        )
        assert [c.chunk_id for c in chunks] == [
            "de-testg-2026-01-01-p99-abs1",
            "de-testg-2026-01-01-p99-abs2",
        ]
        for chunk in chunks:
            assert chunk.parent_id == "de-testg-2026-01-01-p99"
            assert chunk.ueberschrift == "Synthetischer Langparagraph"
            assert estimate_tokens(chunk.text) <= MAX_TOKENS_PER_CHUNK
        assert chunks[0].einheit == "§ 99 Abs. 1"

    def test_zitierkopf_enthaelt_pflichtfelder(self) -> None:
        # SPEC: KNOWLEDGE_ARCHITECTURE.md §6 (Zitierkopf aus gesetz + einheit +
        # ueberschrift + gueltig_ab + quelle_url)
        chunk = chunk_de_gesetz(
            _lade("de/ustg_p19.xml"),
            gesetz="UStG",
            gueltig_ab="2025-01-01",
            rechtsstand_abruf="2026-07-05",
            quelle_url="https://www.gesetze-im-internet.de/ustg/__19.html",
            domaene=("steuerrecht",),
        )[0]
        kopf = chunk.zitierkopf()
        for pflicht in ("UStG", "§ 19", "Besteuerung", "2025-01-01", "gesetze-im-internet"):
            assert pflicht in kopf


class TestEuVerordnung:
    def _ai_act(self) -> list[Chunk]:
        return chunk_eu_verordnung(
            _lade("eu/ai_act_art6_anhang3.xml"),
            celex="32024R1689",
            gueltig_ab="2026-02-17",
            rechtsstand_abruf="2026-07-05",
            quelle_url="https://eur-lex.europa.eu/legal-content/DE/TXT/?uri=CELEX:32024R1689",
            domaene=("eu_ai_act",),
        )

    def test_ai_act_artikel_und_anhang_als_eigene_chunks(self) -> None:
        chunks = self._ai_act()
        ids = {c.chunk_id for c in chunks}
        assert "eu-32024r1689-2026-02-17-art6" in ids
        # SPEC: KNOWLEDGE_ARCHITECTURE.md §5 (Anhang III Nr. 4 = eigener Chunk)
        assert "eu-32024r1689-2026-02-17-anhiii-nr4" in ids
        assert "eu-32024r1689-2026-02-17-anhiii-nr8" in ids
        anhang4 = next(c for c in chunks if c.chunk_id.endswith("anhiii-nr4"))
        assert anhang4.typ == "anhang"
        assert anhang4.einheit == "Anhang III Nr. 4"
        assert "Bewerbungen" in anhang4.text

    def test_erwaegungsgruende_in_5er_gruppen_mit_typ_recital(self) -> None:
        chunks = self._ai_act()
        recitals = [c for c in chunks if c.typ == "recital"]
        assert [c.chunk_id.rsplit("-", 2)[-2:] for c in recitals] == [
            ["rec1", "5"],
            ["rec6", "7"],
        ]
        assert all(c.jurisdiktion == "EU" for c in recitals)

    def test_dsgvo_art28_und_data_act_art5_und_umv_art46(self) -> None:
        for pfad, celex, art, erwartung in (
            ("eu/dsgvo_art28.xml", "32016R0679", "art28", "Auftragsverarbeiter"),
            ("eu/data_act_art5.xml", "32023R2854", "art5", "Dateninhaber"),
            ("eu/umv_art46.xml", "32017R1001", "art46", "Anmeldung"),
        ):
            chunks = chunk_eu_verordnung(
                _lade(pfad),
                celex=celex,
                gueltig_ab="2026-01-01",
                rechtsstand_abruf="2026-07-05",
                quelle_url=f"https://eur-lex.europa.eu/legal-content/DE/TXT/?uri=CELEX:{celex}",
                domaene=("dsgvo",),
            )
            treffer = next(c for c in chunks if c.chunk_id.endswith(art))
            assert treffer.celex == celex
            assert erwartung in treffer.text
