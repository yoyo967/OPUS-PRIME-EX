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

import hashlib
import io
import re
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from collections.abc import Callable
from typing import Any

from src.rag.chunker import (
    MAX_TOKENS_PER_CHUNK,
    Chunk,
    chunk_eu_verordnung,
    estimate_tokens,
)
from src.shared.exceptions import ToolInputError

_DOCTYPE = re.compile(r"<!DOCTYPE[^>]*>", re.IGNORECASE)
_WS = re.compile(r"\s+")
_NUM = re.compile(r"(\d+[a-z]?)")
_ANHANG_NR = re.compile(r"([IVXLCDM]+|\d+)", re.IGNORECASE)
# SCC-Anhang (32021D0914): Standardvertragsklauseln als GR.SEQ mit TITLE "Klausel N";
# Klausel 8/9/10 zerfallen in MODUL-Untergruppen.
# Kein \b nach der Nummer: Titel wie "Klausel 1Zweck..." haben keine Wortgrenze
# zwischen Ziffer und Name. KEIN IGNORECASE bei der Nummer, sonst frisst [a-z]? den
# Grossbuchstaben des Namens ("1Z" statt "1"). Titel beginnen konsistent mit "Klausel".
_KLAUSEL_TITLE = re.compile(r"^Klausel\s+(\d+[a-z]?)\s*(.*)", re.DOTALL)
_MODUL_TITLE = re.compile(r"^(MODUL\s+\w+)", re.IGNORECASE)
# Unterklausel innerhalb eines Moduls: "8.1. Zweckbindung".
_SUBKLAUSEL_TITLE = re.compile(r"^(\d+\.\d+[a-z]?)\.?\s*(.*)", re.DOTALL)

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


def _gruppen_titel(gr: ET.Element) -> str:
    return _collapse(gr.find("TITLE"))


def _gruppen_koerper(gr: ET.Element) -> str:
    """Full text of a GR.SEQ minus its own TITLE prefix."""
    voll = _collapse(gr)
    titel = _gruppen_titel(gr)
    return voll[len(titel):].strip() if voll.startswith(titel) else voll


def chunks_from_scc(
    raw_xml: str,
    celex: str,
    gueltig_ab: str,
    rechtsstand_abruf: str,
    quelle_url: str,
    domaene: tuple[str, ...],
    sprache: str = "de",
) -> list[Chunk]:
    """Parse the SCC decision annex (32021D0914): 1 Chunk = 1 Klausel.

    Der Verordnungs-Parser greift hier nicht (kein ARTICLE/CONSID; die
    Standardvertragsklauseln sind GR.SEQ-Gruppen mit TITLE "Klausel N"). Klausel 8/9/10
    zerfallen in MODUL-Untergruppen (Verantwortlicher->Verantwortlicher etc.) -> je Modul
    ein Chunk; grosse Module (>1.200 Tokens) werden zusaetzlich auf Unterklausel-Ebene
    (8.1, 8.2, ...) gesplittet, damit ein Chunk eine feine, kohaerente Einheit bleibt.
    """
    root = _strip_ns(ET.fromstring(_DOCTYPE.sub("", raw_xml)))
    einheiten: list[tuple[str, str, str]] = []  # (einheit, ueberschrift, text)
    for gr in root.iter("GR.SEQ"):
        match = _KLAUSEL_TITLE.match(_gruppen_titel(gr))
        if not match:
            continue
        nr, name = match.group(1), match.group(2).strip()
        module = [g for g in gr.iter("GR.SEQ") if _MODUL_TITLE.match(_gruppen_titel(g))]
        if not module:
            einheiten.append((f"Klausel {nr}", name, _gruppen_koerper(gr)))
            continue
        for mo in module:
            label = _MODUL_TITLE.match(_gruppen_titel(mo))
            assert label is not None
            mlabel = label.group(1).title()
            koerper = _gruppen_koerper(mo)
            subs = [g for g in mo.iter("GR.SEQ") if _SUBKLAUSEL_TITLE.match(_gruppen_titel(g))]
            # Grosse Module (>1.200 Tokens) auf Unterklausel-Ebene splitten (analog
            # KNOWLEDGE_ARCHITECTURE §5 Absatz-Split); kleine Module bleiben ganz.
            if subs and estimate_tokens(koerper) > MAX_TOKENS_PER_CHUNK:
                for sub in subs:
                    sm = _SUBKLAUSEL_TITLE.match(_gruppen_titel(sub))
                    assert sm is not None
                    einheiten.append(
                        (f"Klausel {nr} ({mlabel}) {sm.group(1)}",
                         sm.group(2).strip(), _gruppen_koerper(sub))
                    )
            else:
                einheiten.append((f"Klausel {nr} ({mlabel})", name, koerper))

    chunks: list[Chunk] = []
    for einheit, ueberschrift, text in einheiten:
        if not text:
            continue
        key = re.sub(r"[^a-z0-9]+", "", einheit.lower())
        chunks.append(
            Chunk(
                chunk_id=f"eu-{celex.lower()}-{gueltig_ab}-{key}",
                quelle_typ="eu_verordnung",
                jurisdiktion="EU",
                gesetz=None,
                celex=celex,
                einheit=einheit,
                ueberschrift=ueberschrift,
                gueltig_ab=gueltig_ab,
                gueltig_bis=None,
                rechtsstand_abruf=rechtsstand_abruf,
                quelle_url=quelle_url,
                text=text,
                hash="sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest(),
                typ="norm",
                domaene=domaene,
                sprache=sprache,
            )
        )
    if not chunks:
        raise ToolInputError(f"SCC-Parser fand keine Klauseln ({celex}).")
    return chunks
