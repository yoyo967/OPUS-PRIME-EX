"""Deterministic query classifier: domain detection + risk signals -> Klassifikation.

Production classification runs on the Haiku Route-C model (AGENT_ARCHITECTURE.md
§4.1). This deterministic classifier is the offline fallback used by the demo and
as a floor when the classification model is unavailable — keyword-based domain
detection plus the router's deterministic risk signals.

# SPEC: AGENT_ARCHITECTURE.md §1 (Router: Domaene/Komplexitaet/Risiko/Zeitbezug)
"""

from __future__ import annotations

import re

from src.router.router import Klassifikation, extract_risikosignale

# Kuratierte Schluesselwoerter je Domaene (bewusst konservativ; Haiku uebernimmt in
# Produktion die feinere Erkennung).
_DOMAENE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "steuerrecht": (
        "steuer", "umsatzsteuer", "ust", "gewerbesteuer", "gewst", "kleinunternehmer",
        "einkommensteuer", "körperschaftsteuer", "vorsteuer", "hebesatz", "eür",
        "betriebsausgabe", "abschreibung", "investitionsabzug",
    ),
    "gewerberecht": (
        "gewerbe", "gewerbeanmeldung", "gewo", "handelsregister", "kaufmann",
        "erlaubnispflicht", "gmbh", "gmbh & co", "kommanditgesellschaft",
    ),
    "finanzen": (
        "bilanz", "buchhaltung", "buchführung", "liquidität", "jahresabschluss",
        "controlling", "finanzierung", "kpi", "hgb-abschluss",
    ),
    "dsgvo": (
        "dsgvo", "datenschutz", "avv", "auftragsverarbeit", "personenbezogen",
        "betroffenenrecht", "drittland", "vvt", "dpia", "art. 28",
    ),
    "eu_ai_act": (
        "ai act", "ki-system", "hochrisiko", "künstliche intelligenz", "anhang iii",
        "ki-verordnung", "gpai", "ki-kompetenz",
    ),
    "data_act": (
        "data act", "datenzugang", "iot", "dateninhaber", "interoperabilität",
        "cloud-switching", "b2b-datenteilung",
    ),
    "markenrecht": (
        "marke", "markenrecht", "markeng", "widerspruch", "dpma", "euipo",
        "unionsmarke", "verwechslungsgefahr", "nizza", "löschungsantrag",
        "abmahnung", "schutzdauer",
    ),
}

_DEFINITIONS_PRAEFIXE = ("was ist", "was heißt", "was bedeutet", "was versteht man")
_GESTALTUNG_KEYWORDS = ("gestaltung", "optimier", "holding", "umstrukturier", "struktur")
_SMALLTALK = ("hallo", "guten morgen", "guten tag", "danke", "hi ", "servus")

# Zitat-basierte Domaenen-Erkennung: ein genanntes Gesetz/eine Verordnung ist ein
# starkes Domaenensignal (z. B. "§ 147 AO" -> steuerrecht), auch ohne Schluesselwort.
_GESETZ_RE = re.compile(
    r"\b(UStG|UStDV|EStG|KStG|GewStG|AO|GewO|HGB|GmbHG|MarkenG|BDSG|BetrVG)\b"
)
_GESETZ_DOMAENE = {
    "ustg": "steuerrecht", "ustdv": "steuerrecht", "estg": "steuerrecht",
    "kstg": "steuerrecht", "gewstg": "steuerrecht", "ao": "steuerrecht",
    "gewo": "gewerberecht", "hgb": "gewerberecht", "gmbhg": "gewerberecht",
    "markeng": "markenrecht", "bdsg": "dsgvo", "betrvg": "gewerberecht",
}
# Verordnungen / gaengige Kurzbezeichnungen -> Domaene (Teilstring-Match, lowercase).
_VO_DOMAENE = {
    "dsgvo": "dsgvo", "2016/679": "dsgvo",
    "umv": "markenrecht", "2017/1001": "markenrecht",
    "2024/1689": "eu_ai_act", "ai act": "eu_ai_act", "ki-verordnung": "eu_ai_act",
    "2023/2854": "data_act", "data act": "data_act",
}


def _domaenen_aus_zitaten(anfrage: str, lowered: str) -> set[str]:
    """Domains implied by an explicitly named statute or regulation."""
    treffer: set[str] = set()
    for match in _GESETZ_RE.finditer(anfrage):
        domaene = _GESETZ_DOMAENE.get(match.group(1).lower())
        if domaene:
            treffer.add(domaene)
    for schluessel, domaene in _VO_DOMAENE.items():
        if schluessel in lowered:
            treffer.add(domaene)
    return treffer


def classify(anfrage: str) -> Klassifikation:
    """Map a raw query to a Klassifikation for the router/orchestrator."""
    lowered = anfrage.lower()
    gefunden = {d for d, kws in _DOMAENE_KEYWORDS.items() if any(k in lowered for k in kws)}
    gefunden |= _domaenen_aus_zitaten(anfrage, lowered)
    domaenen = tuple(sorted(gefunden))
    ist_smalltalk = not domaenen and any(g in lowered for g in _SMALLTALK)
    ist_definitionsfrage = lowered.strip().startswith(_DEFINITIONS_PRAEFIXE)
    gestaltungsanalyse = any(g in lowered for g in _GESTALTUNG_KEYWORDS)
    return Klassifikation(
        domaenen=domaenen,
        ist_smalltalk=ist_smalltalk,
        ist_definitionsfrage=ist_definitionsfrage,
        gestaltungsanalyse=gestaltungsanalyse,
        signale=extract_risikosignale(anfrage),
    )
