"""Tests for the deterministic query classifier.

# SPEC: AGENT_ARCHITECTURE.md §1/§4.1 (Domaenenerkennung, Risikosignale)
"""

from __future__ import annotations

from src.router.classifier import classify
from src.router.router import Route, route_for


class TestDomaenenerkennung:
    def test_steuerfrage(self) -> None:
        k = classify("Muss ich als Kleinunternehmer Umsatzsteuer ausweisen?")
        assert "steuerrecht" in k.domaenen

    def test_markenfrage(self) -> None:
        k = classify("Wie lange ist die Widerspruchsfrist gegen eine Marke beim DPMA?")
        assert "markenrecht" in k.domaenen

    def test_mehrere_domaenen(self) -> None:
        k = classify("Steuerliche und markenrechtliche Folgen der Holding-Gründung?")
        assert "steuerrecht" in k.domaenen and "markenrecht" in k.domaenen

    def test_unbekannte_domaene_leer(self) -> None:
        k = classify("Wie wird das Wetter morgen?")
        assert k.domaenen == ()


class TestFlags:
    def test_definitionsfrage(self) -> None:
        assert classify("Was heißt OSS?").ist_definitionsfrage

    def test_smalltalk(self) -> None:
        k = classify("Hallo, guten Morgen!")
        assert k.ist_smalltalk and k.domaenen == ()

    def test_gestaltungsanalyse(self) -> None:
        assert classify("Holding-Struktur steuerlich optimieren?").gestaltungsanalyse


class TestRoutingIntegration:
    def test_smalltalk_route_c(self) -> None:
        assert route_for(classify("Hallo!"))[0] is Route.C_TRIAGE

    def test_gestaltung_route_b(self) -> None:
        # Gestaltungsanalyse erzwingt Route B (AGENT_ARCHITECTURE §2)
        route, _ = route_for(classify("Holding-Struktur optimieren, 250.000 € Gewinn?"))
        assert route is Route.B_KOMPLEX

    def test_einfache_steuerfrage_route_a(self) -> None:
        route, _ = route_for(classify("Wie hoch ist der Umsatzsteuer-Regelsatz?"))
        assert route is Route.A_STANDARD
