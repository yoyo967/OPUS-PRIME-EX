"""Post-processors: G1 (Disclaimer), G3 (Zitat-Validator), G4 (Zahlen-Provenienz),
G6 (Stale-Warnung).

# SPEC: AGENT_ARCHITECTURE.md §5 (G1, G3, G4, G6)
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from decimal import Decimal, InvalidOperation

from src.guardrails.events import GuardrailEvent
from src.rag.chunker import Chunk
from src.tools.steuer_rechner import CalculationResult

# G3: deterministische Fundstellen-Extraktion. Zwei Muster: DE-Norm und EU-Artikel.
_DE_ZITAT = re.compile(
    r"§\s*(\d+[a-z]?)\s*(?:Abs\.\s*\d+\s*)?(?:S\.\s*\d+\s*)?"
    r"([A-ZÄÖÜ][A-Za-zÄÖÜäöüß]*G|AO|GewO|UStDV)\b"
)
_EU_ZITAT = re.compile(
    r"Art\.\s*(\d+[a-z]?)\s*(?:Abs\.\s*\d+\s*)?(?:lit\.\s*\w+\s*)?"
    r"(DSGVO|UMV|VO\s*\(EU\)\s*(\d{4}/\d+))"
)
# Kurzbezeichnung -> CELEX (SPEC: KNOWLEDGE_ARCHITECTURE.md §2; bei neuen Quellen
# in config/sources.yaml pflegen - hier nur der Aliasteil fuer den Validator).
_CELEX_ALIAS = {
    "DSGVO": "32016R0679",
    "UMV": "32017R1001",
    "2016/679": "32016R0679",
    "2017/1001": "32017R1001",
    "2024/1689": "32024R1689",
    "2023/2854": "32023R2854",
    "2021/914": "32021D0914",
    "608/2013": "32013R0608",
}

_BETRAG = re.compile(r"(\d{1,3}(?:[.\s]\d{3})+(?:,\d+)?|\d+(?:,\d+)?)\s*(?:€|EUR\b|Euro\b)")


def apply_disclaimer_g1(text: str, disclaimer: str) -> tuple[str, GuardrailEvent]:
    """G1: server-side disclaimer injection, independent of the LLM output.

    Prompt-injection-resistant by design: runs after the model, appends always
    (unless the exact wording is already present verbatim).
    # SPEC: AGENT_ARCHITECTURE.md §5 G1
    """
    if disclaimer in text:
        return text, GuardrailEvent("G1", "bereits_vorhanden")
    return f"{text.rstrip()}\n\n{disclaimer}", GuardrailEvent("G1", "disclaimer_angehaengt")


def _extract_zitate(text: str) -> list[tuple[str, str]]:
    """Return (einheit_nummer, quelle_token) pairs found in the answer text."""
    zitate: list[tuple[str, str]] = []
    for match in _DE_ZITAT.finditer(text):
        zitate.append((f"§ {match.group(1)}", match.group(2)))
    for match in _EU_ZITAT.finditer(text):
        token = match.group(3) or match.group(2)
        zitate.append((f"Art. {match.group(1)}", token))
    return zitate


def _zitat_belegt(nummer: str, quelle_token: str, chunks: Sequence[Chunk]) -> bool:
    celex = _CELEX_ALIAS.get(quelle_token)
    for chunk in chunks:
        einheit_basis = chunk.einheit.split(" Abs.")[0]
        if not (einheit_basis == nummer or chunk.einheit.startswith(nummer + " ")):
            continue
        if chunk.gesetz is not None and chunk.gesetz == quelle_token:
            return True
        if chunk.celex is not None and chunk.celex == celex:
            return True
    return False


def validate_zitate_g3(
    text: str, chunks: Sequence[Chunk]
) -> tuple[list[str], GuardrailEvent | None]:
    """G3: every citation in the output must exist in the delivered RAG chunks.

    Returns (unbelegte_zitate, event). Caller drives the 1-retry rule
    (SPEC: KNOWLEDGE_ARCHITECTURE.md §4.6; AGENT_ARCHITECTURE.md §5 G3).
    """
    unbelegt = [
        f"{nummer} {token}"
        for nummer, token in _extract_zitate(text)
        if not _zitat_belegt(nummer, token, chunks)
    ]
    if unbelegt:
        return unbelegt, GuardrailEvent(
            "G3", "unbelegte_zitate", detail="; ".join(sorted(set(unbelegt)))
        )
    return [], None


def _normalize_betrag(raw: str) -> Decimal | None:
    try:
        return Decimal(re.sub(r"[.\s]", "", raw).replace(",", "."))
    except InvalidOperation:
        return None


def collect_allowed_numbers(
    anfrage: str, tool_results: Iterable[CalculationResult], chunks: Iterable[Chunk]
) -> set[Decimal]:
    """Provenance whitelist: user-supplied figures, tool outputs, chunk texts."""
    allowed: set[Decimal] = set()
    for quelle in (anfrage, *(c.text for c in chunks)):
        for match in _BETRAG.finditer(quelle):
            wert = _normalize_betrag(match.group(1))
            if wert is not None:
                allowed.add(wert)
    for result in tool_results:
        for feld in (*result.ergebnis.values(), *(s.wert for s in result.rechenweg)):
            for zahl in re.findall(r"\d+(?:\.\d+)?", str(feld)):
                allowed.add(Decimal(zahl))
    return allowed


def validate_zahlen_g4(
    text: str, allowed: set[Decimal]
) -> tuple[list[str], GuardrailEvent | None]:
    """G4: every EUR amount in the output must stem from a tool/chunk/user input.

    # SPEC: AGENT_ARCHITECTURE.md §5 G4 (freie LLM-Zahlen mit Rechtsfolge ->
    # Block & Retry); PROJECT_INSTRUCTIONS.md §4
    """
    frei: list[str] = []
    for match in _BETRAG.finditer(text):
        wert = _normalize_betrag(match.group(1))
        if wert is not None and wert not in allowed:
            frei.append(match.group(0))
    if frei:
        return frei, GuardrailEvent("G4", "freie_zahlen", detail="; ".join(sorted(set(frei))))
    return [], None


def stale_warnung_g6(
    text: str, chunks: Sequence[Chunk], warnung: str
) -> tuple[str, GuardrailEvent | None]:
    """G6: visible staleness notice when any used source carries the stale flag.

    # SPEC: AGENT_ARCHITECTURE.md §5 G6; KNOWLEDGE_ARCHITECTURE.md §3
    """
    stale_ids = [c.chunk_id for c in chunks if c.stale]
    if not stale_ids:
        return text, None
    return (
        f"{text.rstrip()}\n\n{warnung}",
        GuardrailEvent("G6", "stale_warnung", detail=", ".join(stale_ids)),
    )
