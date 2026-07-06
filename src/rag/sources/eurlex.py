"""EUR-Lex source adapter: fetch Formex XML -> normalize -> chunks.

EUR-Lex publishes legal acts in Formex (XML). This adapter maps the Formex
structure to the normalized <verordnung> format the chunker consumes: recitals
(PREAMBLE/CONSID), articles (ARTICLE/TI.ART/STI.ART/P), annexes (ANNEX/DIVISION).
The fetch step is behind an injectable opener (testable offline).

CAVEAT (honest boundary): the exact Formex tag mapping is modeled on a Formex
subset and MUST be verified against a live EUR-Lex Formex download before
production use (spec/OPEN_QUESTIONS.md #11). CELEX is passed by the caller (the
chunker keys chunks by it), not read from the document.

# SPEC: KNOWLEDGE_ARCHITECTURE.md §2 Prio 1 (EUR-Lex, CELEX-Abruf), §5 (EU-VO:
# 1 Chunk = 1 Artikel; Erwaegungsgruende; Anhaenge je Nummer)
"""

from __future__ import annotations

import re
import urllib.request
import xml.etree.ElementTree as ET
from collections.abc import Callable
from typing import Any

from src.rag.chunker import Chunk, chunk_eu_verordnung

_DOCTYPE = re.compile(r"<!DOCTYPE[^>]*>", re.IGNORECASE)
_WS = re.compile(r"\s+")
_NUM = re.compile(r"(\d+[a-z]?)")
_ANHANG_NR = re.compile(r"([IVXLCDM]+|\d+)", re.IGNORECASE)


def eurlex_xml_url(celex: str) -> str:
    """Canonical EUR-Lex Formex-XML URL for a CELEX id."""
    return f"https://eur-lex.europa.eu/legal-content/DE/TXT/XML/?uri=CELEX:{celex}"


def _default_opener(url: str) -> Any:
    return urllib.request.urlopen(url)  # noqa: S310  # nur bekannte eur-lex-https-URLs


def fetch_eurlex(celex: str, opener: Callable[[str], Any] = _default_opener) -> str:
    """Download the Formex XML. Opener injectable (tests pass a fake).

    NETWORK BOUNDARY: the default opener hits eur-lex.europa.eu.
    """
    with opener(eurlex_xml_url(celex)) as resp:
        text: str = resp.read().decode("utf-8")
    return text


def _collapse(el: ET.Element | None) -> str:
    if el is None:
        return ""
    return _WS.sub(" ", "".join(el.itertext())).strip()


def _artikel_text(art: ET.Element) -> str:
    ps = [_collapse(p) for p in art.iter("P")]
    ps = [p for p in ps if p]
    if ps:
        return " ".join(ps)
    alineas = [_collapse(a) for a in art.iter("ALINEA")]
    return " ".join(a for a in alineas if a)


def normalize_eurlex(raw_xml: str) -> str:
    """Convert Formex-subset XML into the normalized <verordnung> for the chunker."""
    root = ET.fromstring(_DOCTYPE.sub("", raw_xml))
    out = ET.Element("verordnung")

    for i, consid in enumerate(root.iter("CONSID"), start=1):
        no_match = _NUM.search(consid.findtext("NO.P") or "")
        nr = no_match.group(1) if no_match else str(i)
        text = _collapse(consid.find("TXT"))
        if text:
            el = ET.SubElement(out, "erwaegungsgrund")
            el.set("nr", nr)
            el.text = text

    for art in root.iter("ARTICLE"):
        num_match = _NUM.search(art.findtext("TI.ART") or "")
        if num_match is None:
            continue
        el = ET.SubElement(out, "artikel")
        el.set("nr", num_match.group(1))
        ET.SubElement(el, "ueberschrift").text = (art.findtext("STI.ART") or "").strip()
        ET.SubElement(el, "text").text = _artikel_text(art)

    for annex in root.iter("ANNEX"):
        titel = _collapse(annex.find("TITLE"))
        nr_match = _ANHANG_NR.search(titel.replace("ANHANG", "").replace("Anhang", ""))
        anh = ET.SubElement(out, "anhang")
        anh.set("nr", nr_match.group(1) if nr_match else "1")
        ET.SubElement(anh, "ueberschrift").text = titel
        for div in annex.iter("DIVISION"):
            div_match = _NUM.search(div.findtext("NO.P") or "")
            if div_match is None:
                continue
            nummer = ET.SubElement(anh, "nummer")
            nummer.set("nr", div_match.group(1))
            nummer.text = _collapse(div.find("TXT")) or _collapse(div)

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
    """Full adapter path: raw Formex XML -> normalized -> chunked."""
    return chunk_eu_verordnung(
        normalize_eurlex(raw_xml),
        celex=celex,
        gueltig_ab=gueltig_ab,
        rechtsstand_abruf=rechtsstand_abruf,
        quelle_url=quelle_url,
        domaene=domaene,
        sprache=sprache,
    )
