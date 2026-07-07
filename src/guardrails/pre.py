"""Pre-processors: G2 (Scope-Filter), G5 (PII-Eingang), G7 (Jurisdiktions-Gate).

# SPEC: AGENT_ARCHITECTURE.md §5 (G2, G5, G7)
"""

from __future__ import annotations

import re

from src.guardrails.events import GuardrailEvent

# G2: Anfragen nach vorbehaltenen Leistungen (RDG/StBerG; v1.1 inkl. Markenrecht).
# SPEC: AGENT_ARCHITECTURE.md §5 G2; PROJECT_INSTRUCTIONS.md §5 Nr. 1-4
_G2_PATTERNS = (
    re.compile(r"reich\w*\s+.{0,40}?(ustva|voranmeldung|steuererkl)", re.IGNORECASE),
    re.compile(r"(erstell|mach)\w*\s+.{0,40}?steuererkl\w+\s+.{0,30}?(ein|fertig)", re.IGNORECASE),
    re.compile(r"vertritt?\w*\s+(mich|uns)", re.IGNORECASE),
    re.compile(r"(vertretung)\s+.{0,40}?(finanzamt|behörde|behoerde|gericht)", re.IGNORECASE),
    re.compile(r"melde\w*\s+.{0,40}?marke\s+.{0,60}?an", re.IGNORECASE),
    re.compile(
        r"(reich|leg)\w*\s+.{0,60}?(widerspruch|löschungsantrag|loeschungsantrag)"
        r"\s+.{0,30}?ein",
        re.IGNORECASE,
    ),
    re.compile(r"(übermittl|uebermittl|send)\w*\s+.{0,40}?(elster|dpma|euipo|wipo)", re.IGNORECASE),
)

# G5: Signalwoerter fuer besondere Kategorien (Art. 9 DSGVO).
# SPEC: AGENT_ARCHITECTURE.md §5 G5; PROJECT_INSTRUCTIONS.md §5 Nr. 7
_G5_ART9_KEYWORDS = (
    "gesundheit",
    "krankheit",
    "diagnose",
    "behinderung",
    "schwanger",
    "religion",
    "konfession",
    "gewerkschaft",
    "ethnisch",
    "sexuell",
    "biometrisch",
    "genetisch",
    "politische meinung",
    "politische überzeugung",
)

# G7: erlaubte Jurisdiktionen (SPEC: AGENT_ARCHITECTURE.md §5 G7;
# config/guardrails.yaml g7_jurisdiktions_gate.erlaubte_jurisdiktionen)
_G7_ERLAUBT = ("DE", "EU")


def check_scope_g2(anfrage: str) -> GuardrailEvent | None:
    """G2: detect requests for reserved services -> template refusal upstream."""
    for pattern in _G2_PATTERNS:
        if pattern.search(anfrage):
            return GuardrailEvent(
                guardrail_id="G2",
                aktion="blockiert",
                detail=f"Vorbehaltene Leistung erkannt (Muster: {pattern.pattern[:60]})",
            )
    return None


def check_pii_g5(anfrage: str) -> GuardrailEvent | None:
    """G5: detect Art.-9 signals -> data-minimization notice (modus 'hinweis').

    Technische Redaktion/Pseudonymisierung ist als Erweiterung vorgesehen
    (SPEC: spec/OPEN_QUESTIONS.md #3, P3-Arbeitsauftrag; config modus-Feld).
    """
    lowered = anfrage.lower()
    treffer = tuple(k for k in _G5_ART9_KEYWORDS if k in lowered)
    if treffer:
        return GuardrailEvent(
            guardrail_id="G5",
            aktion="hinweis",
            detail=f"Art.-9-Signalwoerter: {', '.join(treffer)}",
        )
    return None


def redigiere_pii_g5(anfrage: str) -> tuple[str, GuardrailEvent | None]:
    """G5 (Durchsetzung): redigiert Art.-9-Signalwoerter, bevor Text ins Modell geht.

    Ersetzt erkannte Signalwoerter durch einen Platzhalter, sodass besondere
    Kategorien personenbezogener Daten (Art. 9 DSGVO) nicht in Retrieval-/Modell-
    Kontext gelangen - Umsetzung des Designziels aus PROJECT_INSTRUCTIONS §5.7
    (nicht mehr nur hinweisgebend). Gibt (redigierter Text, Event|None) zurueck.

    # SPEC: AGENT_ARCHITECTURE.md §5 G5 (technische Redaktion); PROJECT_INSTRUCTIONS §5.7
    """
    lowered = anfrage.lower()
    treffer = [k for k in _G5_ART9_KEYWORDS if k in lowered]
    if not treffer:
        return anfrage, None
    redigiert = anfrage
    for keyword in treffer:
        redigiert = re.sub(
            re.escape(keyword), "[Art.-9-Daten redigiert]", redigiert, flags=re.IGNORECASE
        )
    event = GuardrailEvent(
        guardrail_id="G5",
        aktion="redigiert",
        detail=f"Art.-9-Signalwoerter redigiert: {', '.join(treffer)}",
    )
    return redigiert, event


def check_jurisdiktion_g7(jurisdiktion: str) -> GuardrailEvent | None:
    """G7: non-DE/EU questions -> orientation label + escalation recommendation."""
    if jurisdiktion.upper() not in _G7_ERLAUBT:
        return GuardrailEvent(
            guardrail_id="G7",
            aktion="orientierung",
            detail=f"Jurisdiktion ausserhalb DE/EU: {jurisdiktion}",
        )
    return None
