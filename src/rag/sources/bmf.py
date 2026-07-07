"""BMF-Schreiben (Verwaltungsauffassung) source adapter: text -> Randnummer-Chunks.

BMF-Schreiben (GoBD, AEAO, UStAE, ...) sind **Verwaltungsauffassung, kein Gesetz**.
Sie werden als Sekundaerquelle gefuehrt (quelle_typ="bmf"): im Retrieval unter Normen
priorisiert (_PRIO/_QUELLE_BONUS in retrieval.py) und im Zitierkopf klar als das
jeweilige Schreiben ausgewiesen. Der Zitat-Validator G3 prueft nur §/Artikel-Zitate
und greift daher bei BMF-Fundstellen bewusst nicht — sie sind keine Primaerzitate.

Dieser Modul-Teil ist der reine, offline testbare Kern: aus bereits extrahiertem
Text (die PDF-/HTML-Extraktion ist die Netz-/Format-Grenze, siehe fetch-Schicht)
werden Chunks nach Randnummern gebildet. Chunking-Vertrag laut Spec:

# SPEC: KNOWLEDGE_ARCHITECTURE.md §2 (BMF-Schreiben als Prio-Quelle),
# §5 (BMF/Leitlinien: Chunking nach Randnummern/Abschnitten, 300-800 Tokens,
# 15 % Overlap), §6 (quelle_typ "bmf"; Zitierkopf), §4.5 (Prioritaet Verwaltung).
"""

from __future__ import annotations

import hashlib
import re

from src.rag.chunker import Chunk, estimate_tokens
from src.shared.exceptions import ToolInputError

# SPEC: KNOWLEDGE_ARCHITECTURE.md §5 (300-800 Tokens je BMF-Chunk, 15 % Overlap).
MIN_TOKENS = 300
MAX_TOKENS = 800
OVERLAP_ANTEIL = 0.15

# Randnummer-Marker am Zeilenanfang: "Rz. 12", "Rn 12", "Randnummer 12".
_RANDNUMMER = re.compile(
    r"^\s*(?:Rz\.?|Rn\.?|Randnummer)\s*(\d+[a-z]?)\b",
    re.IGNORECASE | re.MULTILINE,
)
_WS = re.compile(r"\s+")


def _text_hash(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def segmente_nach_randnummer(raw_text: str) -> list[tuple[str, str]]:
    """Split BMF text into (randnummer, text) segments at the Rz.-marker lines.

    Text vor der ersten Randnummer (Titel/Praeambel) wird verworfen. Fehlen
    Randnummern ganz, entsteht ein einzelnes Segment ohne Nummer.
    """
    marker = list(_RANDNUMMER.finditer(raw_text))
    if not marker:
        rest = _WS.sub(" ", raw_text).strip()
        return [("", rest)] if rest else []
    segmente: list[tuple[str, str]] = []
    for i, treffer in enumerate(marker):
        start = treffer.end()
        ende = marker[i + 1].start() if i + 1 < len(marker) else len(raw_text)
        text = _WS.sub(" ", raw_text[start:ende]).strip()
        if text:
            segmente.append((treffer.group(1), text))
    return segmente


def _overlap_saat(segmente: list[tuple[str, str]], gesamt_tokens: int) -> list[tuple[str, str]]:
    """Suffix of a closed chunk to seed the next one (~15 % token overlap)."""
    ziel = OVERLAP_ANTEIL * gesamt_tokens
    saat: list[tuple[str, str]] = []
    akkumuliert = 0
    for segment in reversed(segmente):
        saat.insert(0, segment)
        akkumuliert += estimate_tokens(segment[1])
        if akkumuliert >= ziel:
            break
    return saat


def _einheit(segmente: list[tuple[str, str]]) -> str:
    """Render 'Rz. 5-9' (or 'Rz. 5', or 'Abschnitt' when unnumbered)."""
    nummern = [nr for nr, _ in segmente if nr]
    if not nummern:
        return "Abschnitt"
    if nummern[0] == nummern[-1]:
        return f"Rz. {nummern[0]}"
    return f"Rz. {nummern[0]}-{nummern[-1]}"


def chunks_from_bmf(
    raw_text: str,
    quelle_kuerzel: str,
    titel: str,
    gueltig_ab: str,
    rechtsstand_abruf: str,
    quelle_url: str,
    domaene: tuple[str, ...],
) -> list[Chunk]:
    """Turn extracted BMF text into Randnummer-grouped chunks (quelle_typ='bmf').

    quelle_kuerzel (z. B. "GoBD", "UStAE") landet im gesetz-Feld und damit im
    Zitierkopf; typ='verwaltungsanweisung' kennzeichnet die Sekundaerquelle.
    """
    segmente = segmente_nach_randnummer(raw_text)
    if not segmente:
        raise ToolInputError(f"BMF-Text ({quelle_kuerzel}) enthaelt keinen Inhalt.")

    gruppen: list[list[tuple[str, str]]] = []
    aktuell: list[tuple[str, str]] = []
    tokens = 0
    for segment in segmente:
        seg_tokens = estimate_tokens(segment[1])
        if aktuell and tokens + seg_tokens > MAX_TOKENS and tokens >= MIN_TOKENS:
            gruppen.append(aktuell)
            aktuell = _overlap_saat(aktuell, tokens)
            tokens = sum(estimate_tokens(s[1]) for s in aktuell)
        aktuell.append(segment)
        tokens += seg_tokens
    if aktuell:
        gruppen.append(aktuell)

    chunks: list[Chunk] = []
    for gruppe in gruppen:
        einheit = _einheit(gruppe)
        text = "\n".join(
            (f"Rz. {nr} {seg}" if nr else seg) for nr, seg in gruppe
        )
        key = einheit.replace("Rz. ", "rz").replace(" ", "").replace("-", "_").lower()
        chunks.append(
            Chunk(
                chunk_id=f"bmf-{quelle_kuerzel.lower()}-{gueltig_ab}-{key}",
                quelle_typ="bmf",
                jurisdiktion="DE",
                gesetz=quelle_kuerzel,
                celex=None,
                einheit=einheit,
                ueberschrift=titel,
                gueltig_ab=gueltig_ab,
                gueltig_bis=None,
                rechtsstand_abruf=rechtsstand_abruf,
                quelle_url=quelle_url,
                text=text,
                hash=_text_hash(text),
                typ="verwaltungsanweisung",
                domaene=domaene,
            )
        )
    return chunks
