"""Deterministic deadline calculation (AO/BGB rules, per-Bundesland holidays).

# SPEC: AGENT_ARCHITECTURE.md §3.3 (fristen_kalender)
# SPEC: CLAUDE.md §3 (Determinism first), §4.1 (weekend/holiday shifts per
# Bundesland gem. § 108 AO; 72-h GDPR deadline across weekends)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from src.shared.exceptions import ParameterNotFoundError, ToolInputError

_PARAMS_PATH = Path(__file__).parent / "params" / "fristen_params.yaml"

_BUNDESLAENDER = frozenset(
    "BW BY BE BB HB HH HE MV NI NW RP SL SN ST SH TH".split()
)


@dataclass(frozen=True)
class FristResult:
    """Output per spec: Fristende + Rechtsgrundlage + Warnstufe (+ Rechenweg)."""

    fristtyp: str
    fristende: str  # ISO-Datum
    rechtsgrundlage: str
    warnstufe: str  # HOCH | MITTEL | NIEDRIG
    verschoben_von: str | None
    hinweis: str
    rechenweg: tuple[str, ...]


@lru_cache(maxsize=1)
def _load_params() -> dict[str, Any]:
    with _PARAMS_PATH.open(encoding="utf-8") as handle:
        loaded: dict[str, Any] = yaml.safe_load(handle)
    return loaded


def _ostersonntag(jahr: int) -> date:
    """Gauss/Anonymous Gregorian algorithm for Easter Sunday (deterministic)."""
    a = jahr % 19
    b, c = divmod(jahr, 100)
    d, e = divmod(b, 4)
    g = (8 * b + 13) // 25
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    laenge = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 19 * laenge) // 433
    monat = (h + laenge - 7 * m + 90) // 25
    tag = (h + laenge - 7 * m + 33 * monat + 19) % 32
    return date(jahr, monat, tag)


def _gilt(laender: object, bundesland: str) -> bool:
    return laender == "alle" or (isinstance(laender, list) and bundesland in laender)


@lru_cache(maxsize=64)
def feiertage(jahr: int, bundesland: str) -> frozenset[date]:
    """Gesetzliche Feiertage eines Jahres fuer ein Bundesland (aus Parametertabelle)."""
    if bundesland not in _BUNDESLAENDER:
        raise ToolInputError(f"Unbekanntes Bundesland-Kuerzel: {bundesland!r}")
    params = _load_params()
    tage: set[date] = set()
    for eintrag in params["feiertage_fix"]:
        if _gilt(eintrag["laender"], bundesland):
            tage.add(date(jahr, int(eintrag["monat"]), int(eintrag["tag"])))
    ostern = _ostersonntag(jahr)
    for eintrag in params["feiertage_oster_offset"]:
        if _gilt(eintrag["laender"], bundesland):
            tage.add(ostern + timedelta(days=int(eintrag["offset"])))
    if bundesland in params.get("buss_und_bettag_laender", []):
        # Mittwoch vor dem 23.11. (Tag vor Totensonntag-Logik, deterministisch)
        tag = date(jahr, 11, 22)
        while tag.weekday() != 2:  # 2 = Mittwoch
            tag -= timedelta(days=1)
        tage.add(tag)
    return frozenset(tage)


def _ist_werktag(tag: date, bundesland: str) -> bool:
    return tag.weekday() < 5 and tag not in feiertage(tag.year, bundesland)


def _verschiebe_108_ao(tag: date, bundesland: str) -> date:
    """§ 108 Abs. 3 AO: Ende an Sa/So/Feiertag -> naechster Werktag."""
    while not _ist_werktag(tag, bundesland):
        tag += timedelta(days=1)
    return tag


def _add_months(start: date, monate: int) -> date:
    """§ 188 Abs. 2, 3 BGB: gleicher Kalendertag; fehlt er, letzter Tag des Monats."""
    monat_index = start.month - 1 + monate
    jahr = start.year + monat_index // 12
    monat = monat_index % 12 + 1
    # letzter Tag des Zielmonats
    naechster = date(jahr + monat // 12, monat % 12 + 1, 1)
    letzter_tag = (naechster - timedelta(days=1)).day
    return date(jahr, monat, min(start.day, letzter_tag))


def _warnstufe(fristende: date, referenz: date) -> str:
    verbleibend = (fristende - referenz).days
    if verbleibend <= 14:
        return "HOCH"
    if verbleibend <= 60:
        return "MITTEL"
    return "NIEDRIG"


def berechne_frist(
    fristtyp: str,
    ausloese_datum: date,
    bundesland: str = "BE",
    mit_berater: bool = False,
    referenz_datum: date | None = None,
) -> FristResult:
    """Compute a deadline; input mirrors the tool schema.

    # SPEC: AGENT_ARCHITECTURE.md §3.3 (Input: fristtyp, ausloese_datum,
    # bundesland, mit_berater; Output: Fristende, Rechtsgrundlage, Warnstufe)
    """
    if bundesland not in _BUNDESLAENDER:
        raise ToolInputError(f"Unbekanntes Bundesland-Kuerzel: {bundesland!r}")
    typen: dict[str, Any] = _load_params()["fristtypen"]
    if fristtyp not in typen:
        raise ParameterNotFoundError(
            f"Unbekannter fristtyp {fristtyp!r}. Verfuegbar: {', '.join(sorted(typen))}."
        )
    regel = typen[fristtyp]
    rechenweg: list[str] = [f"Ausloeser: {regel.get('ausloeser', 'Ereignis')} am {ausloese_datum}"]

    einheit = str(regel["einheit"])
    if einheit == "tage":
        ende = ausloese_datum + timedelta(days=int(regel["dauer"]))
        rechenweg.append(f"+ {regel['dauer']} Tage -> {ende}")
    elif einheit == "monate":
        ende = _add_months(ausloese_datum, int(regel["dauer"]))
        rechenweg.append(f"+ {regel['dauer']} Monate (§ 188 Abs. 2, 3 BGB) -> {ende}")
    elif einheit == "jahre":
        ende = _add_months(ausloese_datum, 12 * int(regel["dauer"]))
        rechenweg.append(f"+ {regel['dauer']} Jahre -> {ende}")
    elif einheit == "fest":
        ende = date.fromisoformat(str(regel["datum"]))
        rechenweg.append(f"Gesetzlicher Stichtag: {ende}")
    elif einheit == "speziell" and fristtyp == "jahreserklaerung":
        # SPEC: AGENT_ARCHITECTURE.md §3.3 (Jahreserklaerungen mit/ohne Berater)
        steuerjahr = ausloese_datum.year
        if mit_berater:
            # § 149 Abs. 3 AO: letzter Februartag des Zweitfolgejahres
            ende = date(steuerjahr + 2, 3, 1) - timedelta(days=1)
            rechenweg.append(f"Mit Berater (§ 149 Abs. 3 AO): {ende}")
        else:
            ende = date(steuerjahr + 1, 7, 31)
            rechenweg.append(f"Ohne Berater (§ 149 Abs. 2 AO): {ende}")
    else:
        raise ParameterNotFoundError(f"Unbekannte Fristeinheit {einheit!r} fuer {fristtyp!r}.")

    verschoben_von: str | None = None
    if bool(regel["verschiebung_108_ao"]):
        verschoben = _verschiebe_108_ao(ende, bundesland)
        if verschoben != ende:
            verschoben_von = ende.isoformat()
            rechenweg.append(
                f"§ 108 Abs. 3 AO: {ende} ist Sa/So/Feiertag ({bundesland}) -> {verschoben}"
            )
            ende = verschoben
    else:
        rechenweg.append("Keine Werktagsverschiebung (siehe Rechtsgrundlage/Hinweis).")

    referenz = referenz_datum if referenz_datum is not None else ausloese_datum
    return FristResult(
        fristtyp=fristtyp,
        fristende=ende.isoformat(),
        rechtsgrundlage=str(regel["rechtsgrundlage"]),
        warnstufe=_warnstufe(ende, referenz),
        verschoben_von=verschoben_von,
        hinweis=str(regel.get("hinweis", "")),
        rechenweg=tuple(rechenweg),
    )
