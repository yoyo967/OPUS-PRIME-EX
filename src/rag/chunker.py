"""Chunking for legal texts: the atomic unit is the paragraph/article.

Fixed-size chunking is unsuitable for statutes; boundaries follow the legal
structure. Input is the normalized XML format produced by the fetch layer
(scripts/ingest.py, later milestone); fixtures under data/fixtures/ pin this
contract.

# SPEC: KNOWLEDGE_ARCHITECTURE.md §5 (Chunking-Strategie fuer Rechtstexte)
# SPEC: KNOWLEDGE_ARCHITECTURE.md §6 (Metadaten-Schema pro Chunk)
"""

from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field

from src.shared.exceptions import ToolInputError

# SPEC: KNOWLEDGE_ARCHITECTURE.md §5 (Split ab 1.200 Tokens auf Absatz-Ebene)
MAX_TOKENS_PER_CHUNK = 1200
# SPEC: KNOWLEDGE_ARCHITECTURE.md §5 (Erwaegungsgruende in 5er-Gruppen)
RECITAL_GROUP_SIZE = 5


def estimate_tokens(text: str) -> int:
    """Heuristic token estimate (words x 1.35).

    Deterministic and dependency-free; replaced by the real tokenizer when the
    embedding pipeline lands (later milestone). Only used for split decisions,
    never for legal content.
    """
    return int(len(text.split()) * 1.35)


@dataclass(frozen=True)
class Chunk:
    """One retrievable unit with full Zitierkopf metadata.

    # SPEC: KNOWLEDGE_ARCHITECTURE.md §6 (Zitierkopf = gesetz + einheit +
    # ueberschrift + gueltig_ab + quelle_url)
    """

    chunk_id: str
    quelle_typ: str
    jurisdiktion: str
    gesetz: str | None
    celex: str | None
    einheit: str
    ueberschrift: str
    gueltig_ab: str
    gueltig_bis: str | None
    rechtsstand_abruf: str
    quelle_url: str
    text: str
    hash: str
    typ: str  # norm | recital | anhang
    domaene: tuple[str, ...]
    sprache: str = "de"
    parent_id: str | None = None
    # Verweisgraph-Kanten (SPEC: KNOWLEDGE_ARCHITECTURE.md §5) folgen mit dem
    # Ingest-Meilenstein (Regex + LLM-Extraktion); bis dahin leer.
    verweist_auf: tuple[str, ...] = field(default_factory=tuple)
    stale: bool = False

    def zitierkopf(self) -> str:
        """Render the citation header used in the prompt context."""
        basis = self.gesetz or f"CELEX {self.celex}"
        return (
            f"{basis} {self.einheit} – {self.ueberschrift} "
            f"(gültig ab {self.gueltig_ab}, {self.quelle_url})"
        )


def _text_hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _norm_key(einheit: str) -> str:
    """'§ 19' -> 'p19', '§ 19a' -> 'p19a', 'Art. 6' -> 'art6'."""
    cleaned = einheit.replace("§", "p").replace("Art.", "art").replace(" ", "").lower()
    return cleaned


def chunk_de_gesetz(
    xml_text: str,
    gesetz: str,
    gueltig_ab: str,
    rechtsstand_abruf: str,
    quelle_url: str,
    domaene: tuple[str, ...],
) -> list[Chunk]:
    """Chunk a German statute: 1 chunk = 1 § (incl. amtliche Ueberschrift).

    Exceeds a § MAX_TOKENS_PER_CHUNK, it is split at Absatz level with a shared
    Zitierkopf and parent_id.

    # SPEC: KNOWLEDGE_ARCHITECTURE.md §5 (Deutsche Gesetze: 1 Chunk = 1 §)
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ToolInputError(f"Ungueltiges Gesetzes-XML ({gesetz}): {exc}") from exc

    chunks: list[Chunk] = []
    for norm in root.iter("norm"):
        enbez = norm.findtext("metadaten/enbez")
        titel = norm.findtext("metadaten/titel")
        if not enbez or titel is None:
            continue
        absaetze = [
            (absatz.get("nr", str(i + 1)), "".join(absatz.itertext()).strip())
            for i, absatz in enumerate(norm.findall("textdaten/text/absatz"))
        ]
        volltext = "\n".join(f"({nr}) {text}" for nr, text in absaetze)
        basis_id = f"de-{gesetz.lower()}-{gueltig_ab}-{_norm_key(enbez)}"

        def _build(
            chunk_id: str,
            einheit: str,
            text: str,
            parent_id: str | None,
            ueberschrift: str = str(titel),
        ) -> Chunk:
            return Chunk(
                chunk_id=chunk_id,
                quelle_typ="gesetz",
                jurisdiktion="DE",
                gesetz=gesetz,
                celex=None,
                einheit=einheit,
                ueberschrift=ueberschrift,
                gueltig_ab=gueltig_ab,
                gueltig_bis=None,
                rechtsstand_abruf=rechtsstand_abruf,
                quelle_url=quelle_url,
                text=text,
                hash=_text_hash(text),
                typ="norm",
                domaene=domaene,
                parent_id=parent_id,
            )

        if estimate_tokens(volltext) > MAX_TOKENS_PER_CHUNK and len(absaetze) > 1:
            for nr, text in absaetze:
                chunks.append(
                    _build(f"{basis_id}-abs{nr}", f"{enbez} Abs. {nr}", text, basis_id)
                )
        else:
            chunks.append(_build(basis_id, str(enbez), volltext, None))
    return chunks


def chunk_eu_verordnung(
    xml_text: str,
    celex: str,
    gueltig_ab: str,
    rechtsstand_abruf: str,
    quelle_url: str,
    domaene: tuple[str, ...],
    sprache: str = "de",
) -> list[Chunk]:
    """Chunk an EU regulation: 1 chunk = 1 article; recitals in groups of 5
    (typ 'recital', lower retrieval weight); annexes per number.

    # SPEC: KNOWLEDGE_ARCHITECTURE.md §5 (EU-Verordnungen)
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ToolInputError(f"Ungueltiges Verordnungs-XML ({celex}): {exc}") from exc

    def _build(
        chunk_id: str, einheit: str, ueberschrift: str, text: str, typ: str
    ) -> Chunk:
        return Chunk(
            chunk_id=chunk_id,
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
            hash=_text_hash(text),
            typ=typ,
            domaene=domaene,
            sprache=sprache,
        )

    chunks: list[Chunk] = []
    basis = f"eu-{celex.lower()}-{gueltig_ab}"

    recitals = [
        (rec.get("nr", str(i + 1)), "".join(rec.itertext()).strip())
        for i, rec in enumerate(root.findall("erwaegungsgrund"))
    ]
    for start in range(0, len(recitals), RECITAL_GROUP_SIZE):
        gruppe = recitals[start : start + RECITAL_GROUP_SIZE]
        erster, letzter = gruppe[0][0], gruppe[-1][0]
        text = "\n".join(f"({nr}) {t}" for nr, t in gruppe)
        chunks.append(
            _build(
                f"{basis}-rec{erster}-{letzter}",
                f"Erwägungsgründe {erster}–{letzter}",
                "Erwägungsgründe",
                text,
                "recital",
            )
        )

    for artikel in root.findall("artikel"):
        nr = artikel.get("nr", "")
        ueberschrift = artikel.findtext("ueberschrift", default="")
        text = (artikel.findtext("text") or "").strip()
        chunks.append(
            _build(f"{basis}-art{nr.lower()}", f"Art. {nr}", ueberschrift, text, "norm")
        )

    # SPEC: KNOWLEDGE_ARCHITECTURE.md §5 (Anhang III Nr. 4 AI Act = eigener Chunk)
    for anhang in root.findall("anhang"):
        anhang_nr = anhang.get("nr", "")
        for nummer in anhang.findall("nummer"):
            sub_nr = nummer.get("nr", "")
            text = "".join(nummer.itertext()).strip()
            chunks.append(
                _build(
                    f"{basis}-anh{anhang_nr.lower()}-nr{sub_nr}",
                    f"Anhang {anhang_nr} Nr. {sub_nr}",
                    anhang.findtext("ueberschrift", default=f"Anhang {anhang_nr}"),
                    text,
                    "anhang",
                )
            )
    return chunks
