"""SCC-Decision adapter tests (32021D0914): Klausel-Struktur, Modul-Split (offline).

# SPEC: KNOWLEDGE_ARCHITECTURE.md §2 (EUR-Lex), §5 (1 Chunk = 1 Einheit). Die SCC
# ist ein Durchfuehrungsbeschluss ohne ARTICLE/CONSID -> eigener Parser.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.rag.chunker import MAX_TOKENS_PER_CHUNK, estimate_tokens
from src.rag.sources.eurlex import chunks_from_scc
from src.shared.exceptions import ToolInputError

_SAMPLE = (
    Path(__file__).resolve().parent.parent.parent
    / "data" / "fixtures" / "raw" / "eurlex_scc_sample.xml"
)


def _chunks() -> list:
    return chunks_from_scc(
        _SAMPLE.read_text(encoding="utf-8"), celex="32021D0914",
        gueltig_ab="2021-06-27", rechtsstand_abruf="2026-07-07",
        quelle_url="https://eur-lex.europa.eu/eli/dec_impl/2021/914/oj", domaene=("dsgvo",),
    )


class TestSccParser:
    def test_klauseln_und_modul_split(self) -> None:
        chunks = _chunks()
        einheiten = [c.einheit for c in chunks]
        # Klausel 1 (ohne Module) + Klausel 8 in zwei Modulen
        assert einheiten == ["Klausel 1", "Klausel 8 (Modul Eins)", "Klausel 8 (Modul Zwei)"]

    def test_nummer_nicht_vom_namen_verschluckt(self) -> None:
        # Regression: IGNORECASE liess frueher "Klausel 1Z" statt "Klausel 1" entstehen
        c1 = _chunks()[0]
        assert c1.einheit == "Klausel 1"
        assert c1.ueberschrift.startswith("Zweck und Anwendungsbereich")
        assert "Garantien" in c1.text

    def test_metadaten_und_celex(self) -> None:
        c = _chunks()[0]
        assert c.celex == "32021D0914" and c.gesetz is None
        assert c.quelle_typ == "eu_verordnung" and c.jurisdiktion == "EU"
        assert "CELEX 32021D0914" in c.zitierkopf()

    def test_modul_texte_getrennt(self) -> None:
        chunks = _chunks()
        m1 = next(c for c in chunks if c.einheit == "Klausel 8 (Modul Eins)")
        m2 = next(c for c in chunks if c.einheit == "Klausel 8 (Modul Zwei)")
        assert "Grundsaetze" in m1.text and "Weisung" in m2.text
        assert m1.chunk_id != m2.chunk_id

    def test_grosses_modul_wird_an_unterklauseln_gesplittet(self) -> None:
        filler = "Wort " * 500  # ~675 Tokens je Unterklausel -> Modul > 1.200
        xml = (
            "<CONTENTS><GR.SEQ><TITLE><TI>STANDARDVERTRAGSKLAUSELN</TI></TITLE>"
            "<GR.SEQ><TITLE><TI>Klausel 8Datenschutzgarantien</TI></TITLE>"
            "<GR.SEQ><TITLE><TI>MODUL EINS: X</TI></TITLE>"
            f"<GR.SEQ><TITLE><TI>8.1. Zweckbindung</TI></TITLE><P>{filler}</P></GR.SEQ>"
            f"<GR.SEQ><TITLE><TI>8.2. Transparenz</TI></TITLE><P>{filler}</P></GR.SEQ>"
            "</GR.SEQ></GR.SEQ></GR.SEQ></CONTENTS>"
        )
        chunks = chunks_from_scc(
            xml, celex="32021D0914", gueltig_ab="2021-06-27",
            rechtsstand_abruf="2026-07-07", quelle_url="x", domaene=("dsgvo",),
        )
        einheiten = [c.einheit for c in chunks]
        assert "Klausel 8 (Modul Eins) 8.1" in einheiten
        assert "Klausel 8 (Modul Eins) 8.2" in einheiten
        # Kein Chunk sprengt das Token-Budget mehr
        assert all(estimate_tokens(c.text) <= MAX_TOKENS_PER_CHUNK for c in chunks)

    def test_kleines_modul_bleibt_ganz(self) -> None:
        # Fixture-Module sind klein (<1.200) -> kein Sub-Split
        einheiten = [c.einheit for c in _chunks()]
        assert "Klausel 8 (Modul Eins)" in einheiten  # ganzes Modul, keine 8.x-Splits

    def test_leerer_input_fehler(self) -> None:
        with pytest.raises(ToolInputError, match="keine Klauseln"):
            chunks_from_scc(
                "<CONTENTS/>", celex="32021D0914", gueltig_ab="2021-06-27",
                rechtsstand_abruf="2026-07-07", quelle_url="x", domaene=("dsgvo",),
            )
