"""Risk-based model routing: deterministic score, LLM only classifies features.

The Haiku classification (Route C) extracts features; the risk score is
computed deterministically from those features - never "felt" by the LLM.

# SPEC: AGENT_ARCHITECTURE.md §2 (Modell-Routing, risikobasiert; Routing-Regeln)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from src.shared.exceptions import ToolInputError


class Route(Enum):
    """Routing targets; order encodes escalation rank (higher = more capable)."""

    C_TRIAGE = 0
    A_STANDARD = 1
    B_KOMPLEX = 2


# SPEC: config/models.yaml routing.risiko_score_schwelle_route_b (Default gespiegelt)
DEFAULT_SCHWELLE_ROUTE_B = 60

# Deterministische Merkmals-Erkennung (SPEC: AGENT_ARCHITECTURE.md §2:
# "Betragsschwellen genannt? Betriebspruefung/Strafrecht-Keywords? mehrere
# Domaenen? Fristen mit Rechtsverlust?")
_BETRAG_PATTERN = re.compile(
    r"(\d{1,3}(?:[.\s]\d{3})+|\d+)(?:,\d+)?\s*(?:€|eur|euro)", re.IGNORECASE
)
_STRAFRECHT_KEYWORDS = (
    "betriebsprüfung",
    "betriebspruefung",
    "steuerhinterziehung",
    "strafverfahren",
    "steuerstrafrecht",
    "steuerfahndung",
    "bußgeld",
    "bussgeld",
    "durchsuchung",
)
_RECHTSVERLUST_KEYWORDS = (
    "frist läuft",
    "frist laeuft",
    "abmahnung",
    "einspruchsfrist",
    "widerspruchsfrist",
    "verjährung",
    "verjaehrung",
    "ausschlussfrist",
    "unterlassungserklärung",
    "unterlassungserklaerung",
    "rechtsverlust",
    "72 stunden",
    "72-stunden",
)
# SPEC: SYSTEM_PROMPT v1.2 ESKALATIONSLOGIK Stufe 3 (Bussgeld > 50.000 EUR)
_BETRAG_HOCH_SCHWELLE = 50_000


@dataclass(frozen=True)
class Risikosignale:
    """Deterministically extracted risk features of a query."""

    betrag_genannt: bool
    betrag_hoch: bool
    strafrecht_keywords: tuple[str, ...]
    rechtsverlust_keywords: tuple[str, ...]


@dataclass(frozen=True)
class Klassifikation:
    """Feature output of the Route-C classifier (Haiku) plus deterministic signals.

    # SPEC: AGENT_ARCHITECTURE.md §1 (Router: Domaene, Komplexitaet, Risiko, Zeitbezug)
    """

    domaenen: tuple[str, ...]
    ist_smalltalk: bool = False
    ist_definitionsfrage: bool = False
    gestaltungsanalyse: bool = False
    widerspruechliche_quellen: bool = False
    signale: Risikosignale = field(
        default_factory=lambda: Risikosignale(False, False, (), ())
    )


def extract_risikosignale(text: str) -> Risikosignale:
    """Deterministic regex/keyword extraction - reproducible, testable."""
    lowered = text.lower()
    betraege: list[int] = []
    for match in _BETRAG_PATTERN.finditer(text):
        ziffern = re.sub(r"[.\s]", "", match.group(1))
        betraege.append(int(ziffern))
    return Risikosignale(
        betrag_genannt=bool(betraege),
        betrag_hoch=any(b > _BETRAG_HOCH_SCHWELLE for b in betraege),
        strafrecht_keywords=tuple(k for k in _STRAFRECHT_KEYWORDS if k in lowered),
        rechtsverlust_keywords=tuple(k for k in _RECHTSVERLUST_KEYWORDS if k in lowered),
    )


def compute_risiko_score(klassifikation: Klassifikation) -> int:
    """Deterministic risk score 0-100 from classification features.

    Weights are implementation parameters (not statutes); they are calibrated
    via the eval harness (SPEC: AGENT_ARCHITECTURE.md §2 "Jede Antwort loggt
    Route + Score fuer das Eval-Harness").
    """
    signale = klassifikation.signale
    score = 0
    if signale.betrag_genannt:
        score += 10
    if signale.betrag_hoch:
        score += 20
    if signale.strafrecht_keywords:
        score += 40
    if signale.rechtsverlust_keywords:
        # Fristen mit Rechtsverlust sind Stufe-3-Kriterium (SYSTEM_PROMPT v1.2
        # ESKALATIONSLOGIK) -> hoeheres Gewicht als blosse Betragsnennung.
        score += 30
    if len(klassifikation.domaenen) >= 2:
        score += 20
    if klassifikation.gestaltungsanalyse:
        score += 25
    if klassifikation.widerspruechliche_quellen:
        score += 20
    return min(score, 100)


def route_for(
    klassifikation: Klassifikation, schwelle_route_b: int = DEFAULT_SCHWELLE_ROUTE_B
) -> tuple[Route, int]:
    """Map a classification to a route; returns (route, score) for the audit log.

    # SPEC: AGENT_ARCHITECTURE.md §2 (Route C: Smalltalk/Definition; Route B ab
    # Risiko HOCH bzw. domaenenuebergreifend/Gestaltungsanalyse; sonst Route A)
    """
    score = compute_risiko_score(klassifikation)
    if klassifikation.ist_smalltalk or (
        klassifikation.ist_definitionsfrage and score == 0
    ):
        return Route.C_TRIAGE, score
    if score >= schwelle_route_b:
        return Route.B_KOMPLEX, score
    if klassifikation.gestaltungsanalyse or klassifikation.widerspruechliche_quellen:
        # Domaenenuebergreifende Gestaltung ist Route-B-Ausloeser unabhaengig
        # vom Schwellwert (SPEC: AGENT_ARCHITECTURE.md §2 Route-B-Ausloeser).
        return Route.B_KOMPLEX, score
    return Route.A_STANDARD, score


def escalate(aktuell: Route, ziel: Route) -> Route:
    """Escalation within one request: upward always allowed, downward never.

    # SPEC: AGENT_ARCHITECTURE.md §2 ("Eskalation nach oben ist immer erlaubt,
    # Deeskalation nie innerhalb einer Anfrage")
    """
    if ziel.value < aktuell.value:
        raise ToolInputError(
            f"Deeskalation {aktuell.name} -> {ziel.name} ist verboten "
            f"(AGENT_ARCHITECTURE.md §2)."
        )
    return ziel
