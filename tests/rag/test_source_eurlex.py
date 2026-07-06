"""EUR-Lex adapter tests: fetch (fake opener) -> normalize -> chunk.

# SPEC: KNOWLEDGE_ARCHITECTURE.md §2 Prio 1 (EUR-Lex), §5 (EU-VO: 1 Chunk = 1 Artikel)
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from src.rag.sources.eurlex import (
    chunks_from_eurlex,
    eurlex_xml_url,
    fetch_eurlex,
    normalize_eurlex,
)

_SAMPLE = (
    Path(__file__).resolve().parent.parent.parent
    / "data" / "fixtures" / "raw" / "eurlex_umv_sample.xml"
)

_ANNEX_FORMEX = """<ACT><ENACTING.TERMS>
  <ARTICLE IDENTIFIER="006">
    <TI.ART>Artikel 6</TI.ART><STI.ART>Einstufung</STI.ART>
    <PARAG><ALINEA><P>Die in Anhang III genannten KI-Systeme gelten
      als hochriskant.</P></ALINEA></PARAG>
  </ARTICLE>
  </ENACTING.TERMS>
  <ANNEX><TITLE><TI>ANHANG III</TI></TITLE>
    <DIVISION><NO.P>4</NO.P>
      <TXT>Beschaeftigung: KI-Systeme zur Sichtung von Bewerbungen.</TXT>
    </DIVISION>
  </ANNEX>
</ACT>"""


def _raw() -> str:
    return _SAMPLE.read_text(encoding="utf-8")


class _FakeResponse:
    def __init__(self, data: bytes) -> None:
        self._data = data

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def read(self) -> bytes:
        return self._data


class TestUrlUndFetch:
    def test_url_celex(self) -> None:
        assert eurlex_xml_url("32017R1001") == (
            "https://eur-lex.europa.eu/legal-content/DE/TXT/XML/?uri=CELEX:32017R1001"
        )

    def test_fetch_mit_injiziertem_opener(self) -> None:
        aufgerufen: list[str] = []

        def _opener(url: str) -> Any:
            aufgerufen.append(url)
            return _FakeResponse(_raw().encode("utf-8"))

        out = fetch_eurlex("32017R1001", opener=_opener)
        assert "Artikel 46" in out
        assert aufgerufen == [
            "https://eur-lex.europa.eu/legal-content/DE/TXT/XML/?uri=CELEX:32017R1001"
        ]


class TestNormalisierung:
    def test_recitals_und_artikel(self) -> None:
        root = ET.fromstring(normalize_eurlex(_raw()))
        recitals = root.findall("erwaegungsgrund")
        assert [r.get("nr") for r in recitals] == ["1", "2"]
        artikel = root.findall("artikel")
        assert len(artikel) == 1
        assert artikel[0].get("nr") == "46"
        assert artikel[0].findtext("ueberschrift") == "Widerspruch"
        assert "drei Monaten" in (artikel[0].findtext("text") or "")

    def test_anhang_parsing(self) -> None:
        root = ET.fromstring(normalize_eurlex(_ANNEX_FORMEX))
        anhang = root.findall("anhang")
        assert len(anhang) == 1
        assert anhang[0].get("nr") == "III"
        nummer = anhang[0].findall("nummer")
        assert [n.get("nr") for n in nummer] == ["4"]
        assert "Bewerbungen" in (nummer[0].text or "")


class TestEndToEnd:
    def test_umv_formex_bis_chunks(self) -> None:
        chunks = chunks_from_eurlex(
            _raw(), celex="32017R1001", gueltig_ab="2017-10-01",
            rechtsstand_abruf="2026-07-05",
            quelle_url="https://eur-lex.europa.eu/legal-content/DE/TXT/?uri=CELEX:32017R1001",
            domaene=("markenrecht",),
        )
        art46 = next(c for c in chunks if c.einheit == "Art. 46")
        assert art46.celex == "32017R1001"
        assert art46.chunk_id == "eu-32017r1001-2017-10-01-art46"
        # Kernaussage: Frist ab Veroeffentlichung der ANMELDUNG (Addendum-verifiziert)
        assert "Anmeldung" in art46.text
        # 2 Erwaegungsgruende (<5) -> ein recital-Chunk
        recitals = [c for c in chunks if c.typ == "recital"]
        assert len(recitals) == 1

    def test_ai_act_anhang_bis_chunks(self) -> None:
        chunks = chunks_from_eurlex(
            _ANNEX_FORMEX, celex="32024R1689", gueltig_ab="2026-02-17",
            rechtsstand_abruf="2026-07-05",
            quelle_url="https://eur-lex.europa.eu/legal-content/DE/TXT/?uri=CELEX:32024R1689",
            domaene=("eu_ai_act",),
        )
        einheiten = {c.einheit for c in chunks}
        assert "Art. 6" in einheiten
        assert "Anhang III Nr. 4" in einheiten
