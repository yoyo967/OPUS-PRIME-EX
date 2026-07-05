"""Golden-calculation tests for steuer_rechner.

# SPEC: CLAUDE.md §4.1 (golden calculations incl. edge cases: Hebesatz 200 minimum,
# § 35 EStG cap, Kleinunternehmer boundary at exactly 25,000 / 100,000 EUR)
"""

from decimal import Decimal

import pytest

from src.shared.exceptions import ParameterNotFoundError, ToolInputError
from src.tools.steuer_rechner import (
    calculate,
    calculate_euer_ueberschlag,
    calculate_gewst,
    calculate_kst,
    calculate_ust,
    check_kleinunternehmer,
)


class TestGewst:
    def test_golden_einzelunternehmen_hebesatz_410(self) -> None:
        # Spec-Beispiel: {art: gewst, gewinn: 120000, hebesatz: 410, rechtsjahr: 2026}
        # 120000 -> Freibetrag 24500 -> 95500 x 3,5 % = 3342,50 -> x 410 % = 13704,25
        result = calculate_gewst(Decimal("120000"), 410, 2026, "einzelunternehmen")
        assert result.ergebnis["messbetrag"] == "3342.50"
        assert result.ergebnis["gewst"] == "13704.25"
        # § 35 cap: min(4 x 3342,50 = 13370,00; 13704,25) = 13370,00
        assert result.ergebnis["est_anrechnung_max"] == "13370.00"
        assert any("§ 35" in q for q in result.parameter_quellen)

    def test_golden_kapitalgesellschaft_kein_freibetrag(self) -> None:
        # 120000 x 3,5 % = 4200 -> x 410 % = 17220; keine § 35-Anrechnung fuer KapG
        result = calculate_gewst(Decimal("120000"), 410, 2026, "kapitalgesellschaft")
        assert result.ergebnis["messbetrag"] == "4200.00"
        assert result.ergebnis["gewst"] == "17220.00"
        assert "est_anrechnung_max" not in result.ergebnis

    def test_hebesatz_200_minimum_akzeptiert(self) -> None:
        result = calculate_gewst(Decimal("100000"), 200, 2026, "kapitalgesellschaft")
        assert result.ergebnis["gewst"] == "7000.00"

    def test_hebesatz_unter_200_abgelehnt(self) -> None:
        with pytest.raises(ToolInputError, match="Mindesthebesatz"):
            calculate_gewst(Decimal("100000"), 199, 2026, "kapitalgesellschaft")

    def test_paragraf_35_cap_bei_niedrigem_hebesatz(self) -> None:
        # Hebesatz 300 < Faktor 400 -> Anrechnung = tatsaechliche GewSt (Cap greift)
        result = calculate_gewst(Decimal("124500"), 300, 2026, "einzelunternehmen")
        assert result.ergebnis["gewst"] == "10500.00"
        assert result.ergebnis["est_anrechnung_max"] == "10500.00"

    def test_abrundung_auf_volle_100_euro(self) -> None:
        # § 11 Abs. 1 S. 3 GewStG: erst abrunden, dann Freibetrag
        result = calculate_gewst(Decimal("120057"), 410, 2026, "einzelunternehmen")
        assert result.ergebnis["messbetrag"] == "3342.50"

    def test_negativer_gewinn_abgelehnt(self) -> None:
        with pytest.raises(ToolInputError, match="Verlustfall"):
            calculate_gewst(Decimal("-1"), 410, 2026, "einzelunternehmen")


class TestKleinunternehmer:
    def test_boundary_exakt_25000_und_100000_erfuellt(self) -> None:
        # SPEC: CLAUDE.md §4.1 (boundary at exactly 25,000 / 100,000)
        result = check_kleinunternehmer(Decimal("25000"), Decimal("100000"), 2026)
        assert result.ergebnis["kriterien_erfuellt"] == "ja"

    def test_vorjahr_einen_cent_ueber_grenze(self) -> None:
        result = check_kleinunternehmer(Decimal("25000.01"), Decimal("60000"), 2026)
        assert result.ergebnis["kriterien_erfuellt"] == "nein"

    def test_laufend_einen_cent_ueber_grenze(self) -> None:
        result = check_kleinunternehmer(Decimal("22000"), Decimal("100000.01"), 2026)
        assert result.ergebnis["kriterien_erfuellt"] == "nein"

    def test_spec_beispiel_22000_60000(self) -> None:
        # Golden-Set-Fall steuerrecht-01 / Few-Shot Beispiel 1
        result = check_kleinunternehmer(Decimal("22000"), Decimal("60000"), 2026)
        assert result.ergebnis["kriterien_erfuellt"] == "ja"
        assert "§ 19" in result.parameter_quellen[0]

    def test_rechtsjahr_vor_parametertabelle_schlaegt_fehl(self) -> None:
        # 2024 liegt vor gueltig_ab 2025-01-01 -> kein Fallback auf erfundene Werte
        with pytest.raises(ParameterNotFoundError):
            check_kleinunternehmer(Decimal("20000"), Decimal("50000"), 2024)


class TestUst:
    def test_regelsteuersatz_19_prozent(self) -> None:
        result = calculate_ust(Decimal("1000"), "regelsteuersatz", 2026)
        assert result.ergebnis["ust"] == "190.00"
        assert result.ergebnis["brutto"] == "1190.00"

    def test_ermaessigt_7_prozent(self) -> None:
        result = calculate_ust(Decimal("1000"), "ermaessigt", 2026)
        assert result.ergebnis["ust"] == "70.00"

    def test_oss_unbekannter_mitgliedstaat_kein_fallback(self) -> None:
        # Nicht verifizierte OSS-Saetze existieren bewusst nicht in der Tabelle
        with pytest.raises(ParameterNotFoundError):
            calculate_ust(Decimal("1000"), "regelsteuersatz", 2026, mitgliedstaat="FR")


class TestKst:
    def test_kst_15_prozent_plus_soli(self) -> None:
        result = calculate_kst(Decimal("100000"), 2026)
        assert result.ergebnis["kst"] == "15000.00"
        assert result.ergebnis["soli"] == "825.00"
        assert result.ergebnis["gesamt"] == "15825.00"


class TestEuer:
    def test_ueberschlag(self) -> None:
        result = calculate_euer_ueberschlag(Decimal("80000"), Decimal("35000"), 2026)
        assert result.ergebnis["gewinn"] == "45000"


class TestDispatcher:
    def test_gewst_dispatch_spec_beispiel(self) -> None:
        result = calculate(
            {"art": "gewst", "gewinn": 120000, "hebesatz": 410, "rechtsjahr": 2026}
        )
        assert result.art == "gewst"
        assert result.ergebnis["gewst"] == "13704.25"

    def test_unbekannte_art_abgelehnt(self) -> None:
        with pytest.raises(ToolInputError, match="Unbekannte Berechnungsart"):
            calculate({"art": "vermoegenssteuer", "rechtsjahr": 2026})

    def test_fehlendes_rechtsjahr_abgelehnt(self) -> None:
        with pytest.raises(ToolInputError, match="rechtsjahr"):
            calculate({"art": "gewst", "gewinn": 100, "hebesatz": 400})

    def test_rechenweg_und_quellen_immer_vorhanden(self) -> None:
        # SPEC: AGENT_ARCHITECTURE.md §3.2 (Ergebnis + Rechenweg + Quellen-Referenz)
        result = calculate({"art": "kst", "zu_versteuerndes_einkommen": 50000, "rechtsjahr": 2026})
        assert len(result.rechenweg) >= 1
        assert len(result.parameter_quellen) >= 1
