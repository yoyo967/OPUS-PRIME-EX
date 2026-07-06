"""gesetze-im-internet.de adapter tests: fetch (fake opener) -> normalize -> chunk.

# SPEC: KNOWLEDGE_ARCHITECTURE.md §2 Prio 1 (gii-XML), §5 (1 Chunk = 1 §)
"""

from __future__ import annotations

import io
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any

import pytest

from src.rag.sources.gii import (
    chunks_from_gii,
    extract_gii_from_zip,
    fetch_gii,
    gii_xml_url,
    normalize_gii,
)
from src.shared.exceptions import ToolInputError

_SAMPLE = (
    Path(__file__).resolve().parent.parent.parent
    / "data" / "fixtures" / "raw" / "gii_ustg_sample.xml"
)


def _raw() -> str:
    return _SAMPLE.read_text(encoding="utf-8")


def _zip_bytes(xml: str, name: str = "BJNR000000000.xml") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
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
    def test_url_slug(self) -> None:
        assert gii_xml_url("ustg") == "https://www.gesetze-im-internet.de/ustg/xml.zip"

    def test_fetch_mit_injiziertem_opener(self) -> None:
        zip_data = _zip_bytes(_raw())
        aufgerufen: list[str] = []

        def _opener(url: str) -> Any:
            aufgerufen.append(url)
            return _FakeResponse(zip_data)

        out = fetch_gii("ustg", opener=_opener)
        assert out == zip_data
        assert aufgerufen == ["https://www.gesetze-im-internet.de/ustg/xml.zip"]


class TestZipExtraktion:
    def test_extrahiert_xml_aus_zip(self) -> None:
        xml = extract_gii_from_zip(_zip_bytes("<dokumente/>"))
        assert xml == "<dokumente/>"

    def test_zip_ohne_xml_fehler(self) -> None:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("readme.txt", "kein xml")
        with pytest.raises(ToolInputError, match="keine XML"):
            extract_gii_from_zip(buf.getvalue())


class TestNormalisierung:
    def test_erzeugt_normalisiertes_format(self) -> None:
        norm_xml = normalize_gii(_raw())
        root = ET.fromstring(norm_xml)
        normen = root.findall("norm")
        # § 19 + § 19a; die Gliederungs-Norm ohne §-enbez ist gedroppt
        assert len(normen) == 2
        enbez = [n.findtext("metadaten/enbez") for n in normen]
        assert enbez == ["§ 19", "§ 19a"]

    def test_absatz_erkennung(self) -> None:
        root = ET.fromstring(normalize_gii(_raw()))
        p19 = root.findall("norm")[0]
        absaetze = p19.findall("textdaten/text/absatz")
        assert [a.get("nr") for a in absaetze] == ["1", "2"]
        assert "25 000 Euro" in (absaetze[0].text or "")
        # § 19a: unnummeriert -> ein Absatz nr=1
        p19a = root.findall("norm")[1]
        a = p19a.findall("textdaten/text/absatz")
        assert [x.get("nr") for x in a] == ["1"]

    def test_doctype_wird_gestrippt(self) -> None:
        # Roh enthaelt <!DOCTYPE ...> - normalize darf nicht daran scheitern
        assert "DOCTYPE" not in normalize_gii(_raw())


class TestEndToEnd:
    def test_gii_zip_bis_chunks(self) -> None:
        # fetch(fake) -> extract -> normalize -> chunk, wie im Live-Ingest
        zip_data = _zip_bytes(_raw())
        raw = extract_gii_from_zip(zip_data)
        chunks = chunks_from_gii(
            raw, gesetz="UStG", gueltig_ab="2025-01-01", rechtsstand_abruf="2026-07-05",
            quelle_url="https://www.gesetze-im-internet.de/ustg/", domaene=("steuerrecht",),
        )
        assert [c.einheit for c in chunks] == ["§ 19", "§ 19a"]
        p19 = chunks[0]
        assert p19.chunk_id == "de-ustg-2025-01-01-p19"
        assert p19.ueberschrift == "Besteuerung der Kleinunternehmer"
        assert "25 000 Euro" in p19.text and "100 000 Euro" in p19.text
        assert p19.domaene == ("steuerrecht",)
        # Zitierkopf-Pflichtfelder vorhanden (KNOWLEDGE_ARCHITECTURE §6)
        assert "UStG" in p19.zitierkopf() and "gesetze-im-internet" in p19.zitierkopf()
