"""gesetze-im-internet.de (BMJ) source adapter: fetch ZIP -> normalize -> chunks.

The public corpus ships one ZIP per statute at
``https://www.gesetze-im-internet.de/{slug}/xml.zip`` containing a single XML in
the gii-norm DTD. This adapter turns that real format into the normalized XML the
chunker consumes. The only network step (fetch_gii) is behind an injectable opener
so the whole pipeline is testable offline.

Format handled (gii-norm.dtd, faithfully): a <dokumente> root of <norm> elements;
each carries metadaten/jurabk, metadaten/enbez ("§ 19"), metadaten/titel, and
textdaten/text/Content/<P> paragraphs. Structural norms (Gliederung, no §-enbez)
are skipped. Absatz numbers are read from a leading "(n)" in each <P>.

# SPEC: KNOWLEDGE_ARCHITECTURE.md §2 Prio 1 (gesetze-im-internet.de, XML je Gesetz),
# §5 (Deutsche Gesetze: 1 Chunk = 1 §)
"""

from __future__ import annotations

import io
import re
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Callable
from datetime import datetime
from typing import Any

from src.rag.chunker import Chunk, chunk_de_gesetz
from src.shared.exceptions import ToolInputError

_DOCTYPE = re.compile(r"<!DOCTYPE[^>]*>", re.IGNORECASE)
_ENBEZ_PARAGRAF = re.compile(r"^§\s*\d+[a-z]?")
_ABSATZ = re.compile(r"^\((\d+[a-z]?)\)\s*(.*)$", re.DOTALL)
_WS = re.compile(r"\s+")
# Root <dokumente builddate="YYYYMMDD">: der Stand/Build der Quelle bei gii.
_BUILDDATE = re.compile(r"<dokumente\b[^>]*\bbuilddate=\"(\d{8})\"")


def gii_xml_url(slug: str) -> str:
    """Canonical XML-ZIP URL for a statute slug (e.g. 'ustg', 'markeng')."""
    return f"https://www.gesetze-im-internet.de/{slug}/xml.zip"


def _default_opener(url: str) -> Any:
    return urllib.request.urlopen(url)  # noqa: S310  # nur bekannte gii-https-URLs


def fetch_gii(slug: str, opener: Callable[[str], Any] = _default_opener) -> bytes:
    """Download the statute ZIP. The opener is injectable (tests pass a fake).

    NETWORK BOUNDARY: the default opener hits gesetze-im-internet.de. Not exercised
    by unit tests; integration/live-ingest supplies the real opener.
    """
    with opener(gii_xml_url(slug)) as resp:
        data: bytes = resp.read()
    return data


def gii_builddate(raw_xml: str) -> str | None:
    """Stand/Build-Datum der Quelle aus dem Root <dokumente builddate="YYYYMMDD">.

    Dies ist der *Stand der Quelle* (wann gii die Datei zuletzt gebaut hat) und wird
    als ``rechtsstand_abruf`` verwendet. Es ist NICHT das Inkrafttretens-Datum der
    einzelnen Norm (``gueltig_ab``) — das liefert das gii-Basis-XML nicht verlaesslich
    je Paragraf. Bei fehlendem/ungueltigem Datum: None (Aufrufer nutzt Fallback).
    """
    match = _BUILDDATE.search(raw_xml)
    if match is None:
        return None
    try:
        return datetime.strptime(match.group(1), "%Y%m%d").date().isoformat()
    except ValueError:
        return None


def extract_gii_from_zip(data: bytes) -> str:
    """Return the single XML document contained in a gii ZIP."""
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        xml_namen = [n for n in zf.namelist() if n.lower().endswith(".xml")]
        if not xml_namen:
            raise ToolInputError("gii-ZIP enthaelt keine XML-Datei.")
        return zf.read(xml_namen[0]).decode("utf-8")


def _absaetze(content: ET.Element) -> list[tuple[str, str]]:
    """Split <Content> into (nummer, text) Absatz pairs from leading '(n)'."""
    absaetze: list[list[str]] = []
    for p in content.findall("P"):
        txt = _WS.sub(" ", "".join(p.itertext())).strip()
        if not txt:
            continue
        match = _ABSATZ.match(txt)
        if match:
            absaetze.append([match.group(1), match.group(2).strip()])
        elif absaetze:
            absaetze[-1][1] += " " + txt
        else:
            absaetze.append(["1", txt])
    return [(nr, text) for nr, text in absaetze]


def normalize_gii(raw_xml: str) -> str:
    """Convert real gii XML into the normalized <dokumente> the chunker consumes.

    Structural norms without a §-enbez are dropped; DOCTYPE is stripped.
    """
    root = ET.fromstring(_DOCTYPE.sub("", raw_xml))
    dokumente = ET.Element("dokumente")
    for norm in root.iter("norm"):
        enbez = (norm.findtext("metadaten/enbez") or "").strip()
        titel = norm.findtext("metadaten/titel")
        content = norm.find("textdaten/text/Content")
        if not _ENBEZ_PARAGRAF.match(enbez) or titel is None or content is None:
            continue
        absaetze = _absaetze(content)
        if not absaetze:
            continue
        jurabk = (norm.findtext("metadaten/jurabk") or "").strip()

        n_el = ET.SubElement(dokumente, "norm")
        meta = ET.SubElement(n_el, "metadaten")
        ET.SubElement(meta, "jurabk").text = jurabk
        ET.SubElement(meta, "enbez").text = enbez
        ET.SubElement(meta, "titel").text = titel.strip()
        textdaten = ET.SubElement(n_el, "textdaten")
        text_el = ET.SubElement(textdaten, "text")
        for nr, absatz_text in absaetze:
            abs_el = ET.SubElement(text_el, "absatz")
            abs_el.set("nr", nr)
            abs_el.text = absatz_text
    return ET.tostring(dokumente, encoding="unicode")


def chunks_from_gii(
    raw_xml: str,
    gesetz: str,
    gueltig_ab: str,
    rechtsstand_abruf: str,
    quelle_url: str,
    domaene: tuple[str, ...],
) -> list[Chunk]:
    """Full adapter path: raw gii XML -> normalized -> chunked.

    ``rechtsstand_abruf`` wird bevorzugt aus dem echten Quell-``builddate`` gesetzt
    (Stand der gii-Datei); der uebergebene Wert dient nur als Fallback. So spiegelt
    G6 (Stale-Warnung) den tatsaechlichen Quellenstand statt des Ingest-Laufdatums.
    """
    stand = gii_builddate(raw_xml) or rechtsstand_abruf
    return chunk_de_gesetz(
        normalize_gii(raw_xml),
        gesetz=gesetz,
        gueltig_ab=gueltig_ab,
        rechtsstand_abruf=stand,
        quelle_url=quelle_url,
        domaene=domaene,
    )
