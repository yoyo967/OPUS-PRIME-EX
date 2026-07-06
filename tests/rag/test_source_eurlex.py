"""EUR-Lex adapter tests: fetch Formex ZIP (fake opener) -> normalize -> chunk.

Structure matches the real Formex-4 (CONSID/NP/NO.P/TXT, ARTICLE/TI.ART/STI.ART).

# SPEC: KNOWLEDGE_ARCHITECTURE.md §2 Prio 1 (EUR-Lex), §5 (EU-VO: 1 Chunk = 1 Artikel)
"""

from __future__ import annotations

import io
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

import pytest

from src.rag.sources.eurlex import (
    chunks_from_eurlex,
    eurlex_formex_url,
    extract_formex_from_zip,
    fetch_eurlex,
    normalize_eurlex,
)
from src.shared.exceptions import ToolInputError

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


def _zip_bytes(xml: str, name: str = "L_2017DE.01000101.xml") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        # zusaetzliches .doc.xml (Metadaten) - muss ignoriert werden
        zf.writestr("L_2017DE.01000101.doc.xml", "<meta/>")
        zf.writestr(name, xml)
    return buf.getvalue()


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
        assert eurlex_formex_url("32017R1001") == (
            "http://publications.europa.eu/resource/celex/32017R1001"
        )

    def test_fetch_liefert_zip_und_ruft_cellar(self) -> None:
        zip_data = _zip_bytes(_raw())
        aufgerufen: list[str] = []

        def _opener(request: urllib.request.Request) -> Any:
            aufgerufen.append(request.full_url)
            return _FakeResponse(zip_data)

        out = fetch_eurlex("32017R1001", opener=_opener)
        assert out == zip_data
        assert aufgerufen == ["http://publications.europa.eu/resource/celex/32017R1001"]


class TestZipExtraktion:
    def test_extrahiert_haupt_xml_ohne_doc(self) -> None:
        xml = extract_formex_from_zip(_zip_bytes("<ACT>Hauptdokument mit mehr Inhalt</ACT>"))
        assert xml.startswith("<ACT>") and "Hauptdokument" in xml

    def test_zip_ohne_xml_fehler(self) -> None:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("readme.txt", "kein xml")
        with pytest.raises(ToolInputError, match="keine XML"):
            extract_formex_from_zip(buf.getvalue())


class TestNormalisierung:
    def test_recitals_aus_np_struktur(self) -> None:
        root = ET.fromstring(normalize_eurlex(_raw()))
        recitals = root.findall("erwaegungsgrund")
        assert [r.get("nr") for r in recitals] == ["1", "2"]
        assert "Binnenmarkt" in (recitals[0].text or "")

    def test_artikel(self) -> None:
        root = ET.fromstring(normalize_eurlex(_raw()))
        artikel = root.findall("artikel")
        assert len(artikel) == 1
        assert artikel[0].get("nr") == "46"
        assert artikel[0].findtext("ueberschrift") == "Widerspruch"
        assert "drei Monaten" in (artikel[0].findtext("text") or "")

    def test_anhang_parsing(self) -> None:
        root = ET.fromstring(normalize_eurlex(_ANNEX_FORMEX))
        anhang = root.findall("anhang")
        assert len(anhang) == 1 and anhang[0].get("nr") == "III"
        nummer = anhang[0].findall("nummer")
        assert [n.get("nr") for n in nummer] == ["4"]
        assert "Bewerbungen" in (nummer[0].text or "")


class TestEndToEnd:
    def test_umv_formex_bis_chunks(self) -> None:
        chunks = chunks_from_eurlex(
            _raw(), celex="32017R1001", gueltig_ab="2017-10-01",
            rechtsstand_abruf="2026-07-06",
            quelle_url="https://eur-lex.europa.eu/eli/reg/2017/1001/oj",
            domaene=("markenrecht",),
        )
        art46 = next(c for c in chunks if c.einheit == "Art. 46")
        assert art46.celex == "32017R1001"
        assert art46.chunk_id == "eu-32017r1001-2017-10-01-art46"
        assert "Anmeldung" in art46.text
        recitals = [c for c in chunks if c.typ == "recital"]
        assert len(recitals) == 1

    def test_ai_act_anhang_bis_chunks(self) -> None:
        chunks = chunks_from_eurlex(
            _ANNEX_FORMEX, celex="32024R1689", gueltig_ab="2026-02-17",
            rechtsstand_abruf="2026-07-06",
            quelle_url="https://eur-lex.europa.eu/eli/reg/2024/1689/oj",
            domaene=("eu_ai_act",),
        )
        einheiten = {c.einheit for c in chunks}
        assert "Art. 6" in einheiten
        assert "Anhang III Nr. 4" in einheiten
