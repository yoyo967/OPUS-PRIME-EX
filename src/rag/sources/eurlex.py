"""EUR-Lex source adapter: fetch Formex-4 ZIP (CELLAR) -> normalize -> chunks.

The machine-readable act is the Formex-4 XML, retrieved from CELLAR via content
negotiation (NOT the /TXT/XML/ endpoint, which returns only the NOTICE metadata).
Real structure (verified 2026-07-06 against CELEX 32016R0679):
  ROOT <ACT> · <ARTICLE>/<TI.ART>/<STI.ART> · <CONSID>/<NP>/<NO.P>+<TXT> ·
  <PARAG>/<ALINEA>/<P>/<ITEM>/<LIST> · <ANNEX>/<DIVISION>.
Parsing is namespace-robust (localnames) and uses descendant search for recitals
(NO.P/TXT sit under an intermediate NP). Annex handling is best-effort.

The fetch step is behind an injectable opener (testable offline).

# SPEC: KNOWLEDGE_ARCHITECTURE.md §2 Prio 1 (EUR-Lex, CELEX-Abruf), §5 (EU-VO:
# 1 Chunk = 1 Artikel; Erwaegungsgruende; Anhaenge je Nummer)
"""

from __future__ import annotations

import io
import re
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Callable
from typing import Any

from src.rag.chunker import Chunk, chunk_eu_verordnung
from src.shared.exceptions import ToolInputError

_DOCTYPE = re.compile(r"<!DOCTYPE[^>]*>", re.IGNORECASE)
_WS = re.compile(r"\s+")
_NUM = re.compile(r"(\d+[a-z]?)")
_ANHANG_NR = re.compile(r"([IVXLCDM]+|\d+)", re.IGNORECASE)

# CELLAR content negotiation: Formex-4 ZIP, deutsche Sprachfassung.
_FMX_HEADERS = {
    "User-Agent": "Mozilla/5.0 OPUS-PRIME-EX/1.0",
    "Accept": "application/zip;mtype=fmx4",
    "Accept-Language": "deu",
}


def eurlex_formex_url(celex: str) -> str:
    """CELLAR resource URL for a CELEX id (content-negotiated to Formex-4)."""
    return f"http://publications.europa.eu/resource/celex/{celex}"


def _default_opener(request: urllib.request.Request) -> Any:
    return urllib.request.urlopen(request, timeout=60)


def fetch_eurlex(
    celex: str, opener: Callable[[urllib.request.Request], Any] = _default_opener
) -> bytes:
    """Download the Formex-4 ZIP for a CELEX id. Opener injectable (tests fake it).

    NETWORK BOUNDARY: the default opener hits publications.europa.eu (CELLAR).
    """
    request = urllib.request.Request(eurlex_formex_url(celex), headers=_FMX_HEADERS)
    with opener(request) as resp:
        data: bytes = resp.read()
    return data


def extract_formex_from_zip(data: bytes) -> str:
    """Return the main Formex act XML from a CELLAR ZIP (largest non-.doc .xml)."""
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        xmls = [
            n for n in zf.namelist()
            if n.lower().endswith(".xml") and not n.lower().endswith(".doc.xml")
        ]
        if not xmls:
            xmls = [n for n in zf.namelist() if n.lower().endswith(".xml")]
        if not xmls:
            raise ToolInputError("EUR-Lex-ZIP enthaelt keine XML-Datei.")
        main = max(xmls, key=lambda n: zf.getinfo(n).file_size)
        return zf.read(main).decode("utf-8", "replace")


def _strip_ns(root: ET.Element) -> ET.Element:
    for el in root.iter():
        if isinstance(el.tag, str) and "}" in el.tag:
            el.tag = el.tag.split("}")[-1]
    return root


def _collapse(el: ET.Element | None) -> str:
    if el is None:
        return ""
    return _WS.sub(" ", "".join(el.itertext())).strip()


def _artikel_text(art: ET.Element) -> str:
    """Full article body: all non-title children (PARAG/ALINEA/P/ITEM/LIST)."""
    parts = [
        _collapse(child) for child in list(art) if child.tag not in ("TI.ART", "STI.ART")
    ]
    return " ".join(p for p in parts if p)


def normalize_eurlex(raw_xml: str) -> str:
    """Convert real Formex-4 XML into the normalized <verordnung> for the chunker."""
    root = _strip_ns(ET.fromstring(_DOCTYPE.sub("", raw_xml)))
    out = ET.Element("verordnung")

    for i, consid in enumerate(root.iter("CONSID"), start=1):
        no = consid.find(".//NO.P")
        nr_match = _NUM.search(no.text or "") if (no is not None and no.text) else None
        nr = nr_match.group(1) if nr_match else str(i)
        txt = consid.find(".//TXT")
        text = _collapse(txt) if txt is not None else _collapse(consid)
        if text:
            el = ET.SubElement(out, "erwaegungsgrund")
            el.set("nr", nr)
            el.text = text

    for art in root.iter("ARTICLE"):
        num_match = _NUM.search(_collapse(art.find("TI.ART")))
        if num_match is None:
            continue
        el = ET.SubElement(out, "artikel")
        el.set("nr", num_match.group(1))
        ET.SubElement(el, "ueberschrift").text = _collapse(art.find("STI.ART"))
        ET.SubElement(el, "text").text = _artikel_text(art)

    for annex in root.iter("ANNEX"):
        titel = _collapse(annex.find("TITLE"))
        nr_match = _ANHANG_NR.search(re.sub(r"(?i)anhang", "", titel))
        anh = ET.SubElement(out, "anhang")
        anh.set("nr", nr_match.group(1) if nr_match else "1")
        ET.SubElement(anh, "ueberschrift").text = titel
        for div in annex.iter("DIVISION"):
            div_match = _NUM.search(_collapse(div.find(".//NO.P")))
            if div_match is None:
                continue
            nummer = ET.SubElement(anh, "nummer")
            nummer.set("nr", div_match.group(1))
            txt = div.find(".//TXT")
            nummer.text = _collapse(txt) if txt is not None else _collapse(div)

    return ET.tostring(out, encoding="unicode")


def chunks_from_eurlex(
    raw_xml: str,
    celex: str,
    gueltig_ab: str,
    rechtsstand_abruf: str,
    quelle_url: str,
    domaene: tuple[str, ...],
    sprache: str = "de",
) -> list[Chunk]:
    """Adapter path from an already-extracted Formex XML: normalize -> chunk."""
    return chunk_eu_verordnung(
        normalize_eurlex(raw_xml),
        celex=celex,
        gueltig_ab=gueltig_ab,
        rechtsstand_abruf=rechtsstand_abruf,
        quelle_url=quelle_url,
        domaene=domaene,
        sprache=sprache,
    )
