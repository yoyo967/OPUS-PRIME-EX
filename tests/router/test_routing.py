"""Routing tests: labeled query set -> expected route; no de-escalation.

# SPEC: CLAUDE.md §4.4 (Routing tests: labeled query set -> expected route;
# upward escalation allowed, downward forbidden)
"""

import pytest

from src.router.router import (
    Klassifikation,
    Route,
    compute_risiko_score,
    escalate,
    extract_risikosignale,
    route_for,
)
from src.shared.exceptions import ToolInputError


def _klassifiziere(text: str, domaenen: tuple[str, ...], **flags: bool) -> Klassifikation:
    return Klassifikation(
        domaenen=domaenen, signale=extract_risikosignale(text), **flags
    )


class TestGelabelteQueries:
    """Gelabelte Beispiele aus AGENT_ARCHITECTURE.md §2 (Beispiele je Route)."""

    def test_definitionsfrage_route_c(self) -> None:
        k = _klassifiziere("Was heißt OSS?", ("steuerrecht",), ist_definitionsfrage=True)
        route, score = route_for(k)
        assert route is Route.C_TRIAGE
        assert score == 0

    def test_smalltalk_route_c(self) -> None:
        k = _klassifiziere("Guten Morgen!", (), ist_smalltalk=True)
        assert route_for(k)[0] is Route.C_TRIAGE

    def test_kleinunternehmergrenze_route_a(self) -> None:
        k = _klassifiziere(
            "Umsatz letztes Jahr 22.000 €, dieses Jahr 60.000 € – Kleinunternehmer?",
            ("steuerrecht",),
        )
        route, score = route_for(k)
        assert route is Route.A_STANDARD
        assert 0 < score < 60

    def test_avv_pflichtinhalte_route_a(self) -> None:
        k = _klassifiziere("Welche Pflichtinhalte hat ein AVV?", ("dsgvo",))
        assert route_for(k)[0] is Route.A_STANDARD

    def test_schutzdauer_marke_route_a(self) -> None:
        # v1.1-Beispiel aus AGENT_ARCHITECTURE.md §2: Schutzdauer einer Marke = Route A
        k = _klassifiziere("Wie lange gilt eine deutsche Marke?", ("markenrecht",))
        assert route_for(k)[0] is Route.A_STANDARD

    def test_betriebspruefung_mit_hohem_betrag_route_b(self) -> None:
        k = _klassifiziere(
            "Betriebsprüfung angekündigt, es geht um 250.000 € Nachzahlung.",
            ("steuerrecht",),
        )
        route, score = route_for(k)
        assert route is Route.B_KOMPLEX
        assert score >= 60

    def test_holding_gestaltung_mehrere_domaenen_route_b(self) -> None:
        k = _klassifiziere(
            "Holding-Struktur UG zu GmbH steueroptimal gestalten?",
            ("steuerrecht", "gewerberecht"),
            gestaltungsanalyse=True,
        )
        assert route_for(k)[0] is Route.B_KOMPLEX

    def test_markenabmahnung_mit_frist_route_b(self) -> None:
        # SPEC: AGENT_ARCHITECTURE.md §2 v1.1 (markenrechtliche Kollisionslage/
        # Abmahnung = Route-B-Beispiel); Abmahnung + Bussgeld-/Betragssignal
        k = _klassifiziere(
            "Abmahnung wegen Markenverletzung erhalten, Streitwert 100.000 €, "
            "Unterlassungserklärung bis Freitag gefordert.",
            ("markenrecht",),
        )
        route, score = route_for(k)
        assert route is Route.B_KOMPLEX
        assert score >= 60

    def test_gestaltungsanalyse_erzwingt_route_b_auch_unter_schwelle(self) -> None:
        k = _klassifiziere("Gestaltung pruefen", ("steuerrecht",), gestaltungsanalyse=True)
        assert compute_risiko_score(k) < 60
        assert route_for(k)[0] is Route.B_KOMPLEX


class TestRisikosignale:
    def test_betragserkennung_mit_tausenderpunkt(self) -> None:
        signale = extract_risikosignale("Es geht um 250.000 € Umsatz.")
        assert signale.betrag_genannt and signale.betrag_hoch

    def test_betrag_unter_schwelle_nicht_hoch(self) -> None:
        signale = extract_risikosignale("Rechnung über 1.200 EUR")
        assert signale.betrag_genannt and not signale.betrag_hoch

    def test_strafrecht_keywords(self) -> None:
        signale = extract_risikosignale("Uns droht ein Verfahren wegen Steuerhinterziehung.")
        assert "steuerhinterziehung" in signale.strafrecht_keywords

    def test_score_gedeckelt_bei_100(self) -> None:
        k = _klassifiziere(
            "Betriebsprüfung, Steuerhinterziehung, Abmahnung, Frist läuft, 900.000 €",
            ("steuerrecht", "markenrecht"),
            gestaltungsanalyse=True,
            widerspruechliche_quellen=True,
        )
        assert compute_risiko_score(k) == 100


class TestEskalation:
    def test_eskalation_nach_oben_erlaubt(self) -> None:
        assert escalate(Route.A_STANDARD, Route.B_KOMPLEX) is Route.B_KOMPLEX
        assert escalate(Route.C_TRIAGE, Route.A_STANDARD) is Route.A_STANDARD

    def test_gleiche_route_erlaubt(self) -> None:
        assert escalate(Route.B_KOMPLEX, Route.B_KOMPLEX) is Route.B_KOMPLEX

    def test_deeskalation_verboten(self) -> None:
        with pytest.raises(ToolInputError, match="Deeskalation"):
            escalate(Route.B_KOMPLEX, Route.A_STANDARD)
        with pytest.raises(ToolInputError, match="Deeskalation"):
            escalate(Route.A_STANDARD, Route.C_TRIAGE)
