"""Deterministic tax calculations for OPUS PRIME EX.

All computations with legal effect are pure functions over versioned parameter
tables. The LLM never does math; it only relays results from this module.

# SPEC: AGENT_ARCHITECTURE.md §3.2 (steuer_rechner)
# SPEC: CLAUDE.md §3 (Determinism first; table-driven parameters under src/tools/params/)
# SPEC: PROJECT_INSTRUCTIONS.md §4 (Zahlenwerke ausschliesslich durch deterministische Tools)
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import yaml

from src.shared.exceptions import ParameterNotFoundError, ToolInputError

_PARAMS_PATH = Path(__file__).parent / "params" / "steuer_params.yaml"

Rechtsform = Literal["einzelunternehmen", "personengesellschaft", "kapitalgesellschaft"]
UstSatzTyp = Literal["regelsteuersatz", "ermaessigt"]

_CENT = Decimal("0.01")


@dataclass(frozen=True)
class RechenSchritt:
    """One step of the auditable calculation path (Rechenweg)."""

    beschreibung: str
    wert: str


@dataclass(frozen=True)
class CalculationResult:
    """Result envelope per spec: Ergebnis + Rechenweg + Parameter mit Quellen-Referenz.

    # SPEC: AGENT_ARCHITECTURE.md §3.2 (Output: Ergebnis + Rechenweg + verwendete
    # Parameter mit Quellen-Referenz)
    """

    art: str
    rechtsjahr: int
    ergebnis: Mapping[str, str]
    rechenweg: tuple[RechenSchritt, ...]
    parameter_quellen: tuple[str, ...] = field(default_factory=tuple)


@lru_cache(maxsize=1)
def _load_params() -> dict[str, Any]:
    with _PARAMS_PATH.open(encoding="utf-8") as handle:
        loaded: dict[str, Any] = yaml.safe_load(handle)
    return loaded


def _select_param(gruppe: str, rechtsjahr: int, **filter_felder: str) -> dict[str, Any]:
    """Select the parameter row valid for the given rechtsjahr (gueltig_ab/gueltig_bis).

    # SPEC: CLAUDE.md §3 (versioned like statutes: gueltig_ab/gueltig_bis)
    """
    stichtag = date(rechtsjahr, 1, 1)
    rows: list[dict[str, Any]] = _load_params().get(gruppe, [])
    for row in rows:
        gueltig_ab = date.fromisoformat(str(row["gueltig_ab"]))
        gueltig_bis_raw = row.get("gueltig_bis")
        gueltig_bis = (
            date.fromisoformat(str(gueltig_bis_raw)) if gueltig_bis_raw else date.max
        )
        if not gueltig_ab <= stichtag <= gueltig_bis:
            continue
        if any(str(row.get(feld)) != wert for feld, wert in filter_felder.items()):
            continue
        return row
    filter_info = f" ({filter_felder})" if filter_felder else ""
    raise ParameterNotFoundError(
        f"Keine versionierte Parametertabelle fuer '{gruppe}'{filter_info} "
        f"im Rechtsjahr {rechtsjahr}. Kein Fallback auf unverifizierte Werte "
        f"(spec/OPEN_QUESTIONS.md-Prinzip)."
    )


def _as_decimal(wert: object, feldname: str) -> Decimal:
    if isinstance(wert, bool) or wert is None:
        raise ToolInputError(f"Feld '{feldname}' muss eine Zahl sein, erhalten: {wert!r}")
    try:
        return Decimal(str(wert))
    except ArithmeticError as exc:
        raise ToolInputError(f"Feld '{feldname}' ist keine gueltige Zahl: {wert!r}") from exc


def calculate_gewst(
    gewinn: Decimal, hebesatz: int, rechtsjahr: int, rechtsform: Rechtsform
) -> CalculationResult:
    """Gewerbesteuer: Messbetrag x Hebesatz plus § 35 EStG-Anrechnungspotenzial.

    # SPEC: AGENT_ARCHITECTURE.md §3.2 (GewSt: Messbetrag x Hebesatz, § 35 EStG-Anrechnung)
    """
    params = _select_param("gewst", rechtsjahr)
    anrechnung = _select_param("est_35_anrechnung", rechtsjahr)
    quellen = [str(params["quelle"])]

    mindest_hebesatz = int(params["mindest_hebesatz"])
    if hebesatz < mindest_hebesatz:
        raise ToolInputError(
            f"Hebesatz {hebesatz} % unterschreitet den gesetzlichen Mindesthebesatz "
            f"von {mindest_hebesatz} % (§ 16 Abs. 4 S. 2 GewStG)."
        )
    if gewinn < 0:
        raise ToolInputError("Negativer Gewerbeertrag: keine GewSt-Berechnung (Verlustfall).")

    rundung = Decimal(int(params["rundung_gewerbeertrag"]))
    ertrag_gerundet = (gewinn / rundung).to_integral_value(rounding=ROUND_DOWN) * rundung
    schritte = [
        RechenSchritt(
            "Gewerbeertrag auf volle 100 EUR abgerundet (§ 11 Abs. 1 S. 3 GewStG)",
            f"{ertrag_gerundet} EUR",
        )
    ]

    freibetrag = (
        Decimal(str(params["freibetrag_natuerliche_personen"]))
        if rechtsform in ("einzelunternehmen", "personengesellschaft")
        else Decimal("0")
    )
    bemessung = max(Decimal("0"), ertrag_gerundet - freibetrag)
    schritte.append(
        RechenSchritt(
            f"Freibetrag ({rechtsform}: {freibetrag} EUR, § 11 Abs. 1 S. 3 GewStG) abgezogen",
            f"{bemessung} EUR",
        )
    )

    messzahl = Decimal(str(params["messzahl"]))
    messbetrag = (bemessung * messzahl).quantize(_CENT, rounding=ROUND_HALF_UP)
    schritte.append(
        RechenSchritt(f"Steuermessbetrag: {bemessung} EUR x {messzahl}", f"{messbetrag} EUR")
    )

    gewst = (messbetrag * Decimal(hebesatz) / Decimal(100)).quantize(
        _CENT, rounding=ROUND_HALF_UP
    )
    schritte.append(
        RechenSchritt(f"GewSt: Messbetrag x Hebesatz {hebesatz} %", f"{gewst} EUR")
    )

    ergebnis: dict[str, str] = {
        "messbetrag": str(messbetrag),
        "gewst": str(gewst),
    }
    if rechtsform in ("einzelunternehmen", "personengesellschaft"):
        faktor = Decimal(str(anrechnung["faktor"]))
        # § 35 EStG: das faktor-fache des Messbetrags, gedeckelt auf die
        # tatsaechlich zu zahlende GewSt (SPEC: CLAUDE.md §4.1 "§ 35 EStG cap").
        anrechnung_max = min(
            (messbetrag * faktor).quantize(_CENT, rounding=ROUND_HALF_UP), gewst
        )
        ergebnis["est_anrechnung_max"] = str(anrechnung_max)
        schritte.append(
            RechenSchritt(
                f"§ 35 EStG Anrechnungspotenzial: min({faktor} x Messbetrag; GewSt)",
                f"{anrechnung_max} EUR",
            )
        )
        quellen.append(str(anrechnung["quelle"]))

    return CalculationResult(
        art="gewst",
        rechtsjahr=rechtsjahr,
        ergebnis=ergebnis,
        rechenweg=tuple(schritte),
        parameter_quellen=tuple(quellen),
    )


def check_kleinunternehmer(
    umsatz_vorjahr: Decimal, umsatz_laufend: Decimal, rechtsjahr: int
) -> CalculationResult:
    """Kleinunternehmer-Grenzpruefung nach § 19 UStG (Netto-Gesamtumsatz).

    Grenzwerte gelten als eingehalten, solange sie nicht UEBERSCHRITTEN werden
    (exakt 25.000 / 100.000 EUR ist zulaessig).

    # SPEC: AGENT_ARCHITECTURE.md §3.2 (Kleinunternehmer-Grenzpruefung)
    # SPEC: CLAUDE.md §4.1 (Kleinunternehmer boundary at exactly 25,000 / 100,000)
    """
    if umsatz_vorjahr < 0 or umsatz_laufend < 0:
        raise ToolInputError("Umsaetze duerfen nicht negativ sein.")
    params = _select_param("kleinunternehmer_grenzen", rechtsjahr)
    grenze_vorjahr = Decimal(str(params["grenze_vorjahr"]))
    grenze_laufend = Decimal(str(params["grenze_laufend"]))

    vorjahr_ok = umsatz_vorjahr <= grenze_vorjahr
    laufend_ok = umsatz_laufend <= grenze_laufend
    erfuellt = vorjahr_ok and laufend_ok

    schritte = (
        RechenSchritt(
            f"Vorjahresumsatz {umsatz_vorjahr} EUR <= Grenze {grenze_vorjahr} EUR",
            "erfuellt" if vorjahr_ok else "ueberschritten",
        ),
        RechenSchritt(
            f"Laufender Umsatz {umsatz_laufend} EUR <= Grenze {grenze_laufend} EUR",
            "erfuellt" if laufend_ok else "ueberschritten",
        ),
    )
    return CalculationResult(
        art="kleinunternehmer",
        rechtsjahr=rechtsjahr,
        ergebnis={
            "kriterien_erfuellt": "ja" if erfuellt else "nein",
            "grenze_vorjahr": str(grenze_vorjahr),
            "grenze_laufend": str(grenze_laufend),
            "hinweis": (
                "Bei Ueberschreiten der laufenden Grenze entfaellt die Regelung ab dem "
                "Umsatz, mit dem die Grenze ueberschritten wird."
            ),
        },
        rechenweg=schritte,
        parameter_quellen=(str(params["quelle"]),),
    )


def calculate_ust(
    netto: Decimal, satz_typ: UstSatzTyp, rechtsjahr: int, mitgliedstaat: str = "DE"
) -> CalculationResult:
    """Umsatzsteuer auf einen Nettobetrag (national bzw. OSS-Satz aus Tabelle).

    # SPEC: AGENT_ARCHITECTURE.md §3.2 (USt Regelsteuersatz/ermaessigt, OSS-Saetze
    # je Mitgliedstaat aus Tabelle)
    """
    if netto < 0:
        raise ToolInputError("Nettobetrag darf nicht negativ sein.")
    gruppe = "ust_saetze" if mitgliedstaat == "DE" else "oss_saetze"
    filter_felder = {} if mitgliedstaat == "DE" else {"mitgliedstaat": mitgliedstaat}
    params = _select_param(gruppe, rechtsjahr, **filter_felder)
    satz = Decimal(str(params[satz_typ]))
    ust = (netto * satz).quantize(_CENT, rounding=ROUND_HALF_UP)
    return CalculationResult(
        art="ust",
        rechtsjahr=rechtsjahr,
        ergebnis={"ust": str(ust), "brutto": str(netto + ust), "satz": str(satz)},
        rechenweg=(
            RechenSchritt(
                f"USt ({mitgliedstaat}, {satz_typ}): {netto} EUR x {satz}", f"{ust} EUR"
            ),
        ),
        parameter_quellen=(str(params["quelle"]),),
    )


def calculate_kst(zu_versteuerndes_einkommen: Decimal, rechtsjahr: int) -> CalculationResult:
    """Koerperschaftsteuer inkl. Solidaritaetszuschlag.

    # SPEC: AGENT_ARCHITECTURE.md §3.2 (KSt inkl. Soli)
    """
    if zu_versteuerndes_einkommen < 0:
        raise ToolInputError("Negatives zu versteuerndes Einkommen: keine KSt (Verlustfall).")
    params = _select_param("kst", rechtsjahr)
    satz = Decimal(str(params["satz"]))
    soli_satz = Decimal(str(params["soli_satz"]))
    kst = (zu_versteuerndes_einkommen * satz).quantize(_CENT, rounding=ROUND_HALF_UP)
    soli = (kst * soli_satz).quantize(_CENT, rounding=ROUND_HALF_UP)
    return CalculationResult(
        art="kst",
        rechtsjahr=rechtsjahr,
        ergebnis={"kst": str(kst), "soli": str(soli), "gesamt": str(kst + soli)},
        rechenweg=(
            RechenSchritt(f"KSt: {zu_versteuerndes_einkommen} EUR x {satz}", f"{kst} EUR"),
            RechenSchritt(f"Soli: {kst} EUR x {soli_satz}", f"{soli} EUR"),
        ),
        parameter_quellen=(str(params["quelle"]),),
    )


def calculate_euer_ueberschlag(
    einnahmen: Decimal, ausgaben: Decimal, rechtsjahr: int
) -> CalculationResult:
    """EUeR-Ueberschlag: Betriebseinnahmen minus Betriebsausgaben (§ 4 Abs. 3 EStG).

    # SPEC: AGENT_ARCHITECTURE.md §3.2 (EUeR-Ueberschlag)
    """
    if einnahmen < 0 or ausgaben < 0:
        raise ToolInputError("Einnahmen und Ausgaben duerfen nicht negativ sein.")
    gewinn = einnahmen - ausgaben
    return CalculationResult(
        art="euer",
        rechtsjahr=rechtsjahr,
        ergebnis={"gewinn": str(gewinn)},
        rechenweg=(
            RechenSchritt(f"Einnahmen {einnahmen} EUR - Ausgaben {ausgaben} EUR", f"{gewinn} EUR"),
        ),
        parameter_quellen=("§ 4 Abs. 3 EStG (Ueberschlag, keine steuerliche Wuerdigung)",),
    )


def calculate(anfrage: Mapping[str, object]) -> CalculationResult:
    """Dispatch entry point matching the tool schema input.

    # SPEC: AGENT_ARCHITECTURE.md §3.2 (Input: typisiertes Berechnungsobjekt,
    # z. B. {art: "gewst", gewinn: 120000, hebesatz: 410, rechtsjahr: 2026})
    """
    art = anfrage.get("art")
    rechtsjahr_raw = anfrage.get("rechtsjahr")
    if not isinstance(rechtsjahr_raw, int):
        raise ToolInputError("Feld 'rechtsjahr' (int) ist Pflicht.")
    rechtsjahr = rechtsjahr_raw

    if art == "gewst":
        rechtsform = str(anfrage.get("rechtsform", "einzelunternehmen"))
        if rechtsform not in ("einzelunternehmen", "personengesellschaft", "kapitalgesellschaft"):
            raise ToolInputError(f"Unbekannte Rechtsform: {rechtsform!r}")
        hebesatz_raw = anfrage.get("hebesatz")
        if not isinstance(hebesatz_raw, int):
            raise ToolInputError("Feld 'hebesatz' (int, in Prozent) ist Pflicht.")
        return calculate_gewst(
            gewinn=_as_decimal(anfrage.get("gewinn"), "gewinn"),
            hebesatz=hebesatz_raw,
            rechtsjahr=rechtsjahr,
            rechtsform=rechtsform,  # type: ignore[arg-type]
        )
    if art == "kleinunternehmer":
        return check_kleinunternehmer(
            umsatz_vorjahr=_as_decimal(anfrage.get("umsatz_vorjahr"), "umsatz_vorjahr"),
            umsatz_laufend=_as_decimal(anfrage.get("umsatz_laufend"), "umsatz_laufend"),
            rechtsjahr=rechtsjahr,
        )
    if art == "ust":
        satz_typ = str(anfrage.get("satz_typ", "regelsteuersatz"))
        if satz_typ not in ("regelsteuersatz", "ermaessigt"):
            raise ToolInputError(f"Unbekannter satz_typ: {satz_typ!r}")
        return calculate_ust(
            netto=_as_decimal(anfrage.get("netto"), "netto"),
            satz_typ=satz_typ,  # type: ignore[arg-type]
            rechtsjahr=rechtsjahr,
            mitgliedstaat=str(anfrage.get("mitgliedstaat", "DE")),
        )
    if art == "kst":
        return calculate_kst(
            zu_versteuerndes_einkommen=_as_decimal(
                anfrage.get("zu_versteuerndes_einkommen"), "zu_versteuerndes_einkommen"
            ),
            rechtsjahr=rechtsjahr,
        )
    if art == "euer":
        return calculate_euer_ueberschlag(
            einnahmen=_as_decimal(anfrage.get("einnahmen"), "einnahmen"),
            ausgaben=_as_decimal(anfrage.get("ausgaben"), "ausgaben"),
            rechtsjahr=rechtsjahr,
        )
    raise ToolInputError(f"Unbekannte Berechnungsart: {art!r}")
