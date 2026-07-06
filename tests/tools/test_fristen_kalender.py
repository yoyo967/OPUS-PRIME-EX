"""Golden tests for fristen_kalender.

# SPEC: CLAUDE.md §4.1 (weekend/holiday shifts per Bundesland (§ 108 AO),
# 72-h GDPR breach deadline across weekends) + v1.1 Markenfristen
"""

from datetime import date

import pytest

from src.shared.exceptions import ParameterNotFoundError, ToolInputError
from src.tools.fristen_kalender import berechne_frist, feiertage


class TestVerschiebungJeBundesland:
    def test_frist_auf_sonntag_verschiebt_auf_montag(self) -> None:
        # UStVA fuer Dezember 2026: 31.12.2026 + 10 Tage = 10.01.2027 (Sonntag)
        result = berechne_frist("ustva_abgabe", date(2026, 12, 31), bundesland="BE")
        assert result.fristende == "2027-01-11"
        assert result.verschoben_von == "2027-01-10"
        assert "§ 108" in result.rechenweg[-1]

    def test_feiertag_je_bundesland_bayern_vs_berlin(self) -> None:
        # Fristende 06.01.2027 (Mittwoch): Heilige Drei Koenige ist Feiertag in BY,
        # nicht in BE -> unterschiedliches Fristende je Bundesland (§ 108 Abs. 3 AO)
        bayern = berechne_frist("ustva_abgabe", date(2026, 12, 27), bundesland="BY")
        berlin = berechne_frist("ustva_abgabe", date(2026, 12, 27), bundesland="BE")
        assert bayern.fristende == "2027-01-07"
        assert bayern.verschoben_von == "2027-01-06"
        assert berlin.fristende == "2027-01-06"
        assert berlin.verschoben_von is None

    def test_werktag_ohne_verschiebung(self) -> None:
        # 31.05.2026 + 10 Tage = 10.06.2026 (Mittwoch, kein Feiertag)
        result = berechne_frist("ustva_abgabe", date(2026, 5, 31), bundesland="NW")
        assert result.fristende == "2026-06-10"
        assert result.verschoben_von is None


class TestDsgvo72h:
    def test_72h_frist_laeuft_uebers_wochenende_ohne_verschiebung(self) -> None:
        # Kenntnis Donnerstag 02.07.2026 -> Fristende Sonntag 05.07.2026, KEINE
        # Werktagsverschiebung (EU-Frist, § 108 AO nicht anwendbar)
        result = berechne_frist("dsgvo_meldung_72h", date(2026, 7, 2), bundesland="BE")
        assert result.fristende == "2026-07-05"
        assert date.fromisoformat(result.fristende).weekday() == 6  # Sonntag
        assert result.verschoben_von is None
        assert result.rechtsgrundlage == "Art. 33 Abs. 1 DSGVO"
        assert result.warnstufe == "HOCH"


class TestMarkenfristen:
    def test_widerspruch_de_drei_monate_ab_eintragung(self) -> None:
        # § 188 Abs. 2 BGB: 15.03.2026 + 3 Monate = 15.06.2026 (Montag)
        result = berechne_frist("widerspruch_marke_de", date(2026, 3, 15))
        assert result.fristende == "2026-06-15"
        assert result.rechtsgrundlage == "§ 42 Abs. 1 MarkenG"
        assert "EINTRAGUNG" in result.rechenweg[0]

    def test_widerspruch_de_monatsende_clamp_und_verschiebung(self) -> None:
        # 30.11.2026 + 3 Monate: 30.02. existiert nicht -> 28.02.2027 (§ 188 Abs. 3
        # BGB), das ist ein Sonntag -> § 108 AO -> Montag 01.03.2027
        result = berechne_frist("widerspruch_marke_de", date(2026, 11, 30))
        assert result.fristende == "2027-03-01"
        assert result.verschoben_von == "2027-02-28"

    def test_widerspruch_unionsmarke_konservativ_ohne_verschiebung(self) -> None:
        # Art. 46 UMV: ab Veroeffentlichung der ANMELDUNG; Ende Samstag bleibt
        # Samstag (konservative Berechnung, EUIPO-Kalender massgeblich)
        result = berechne_frist("widerspruch_unionsmarke", date(2027, 3, 12))
        assert result.fristende == "2027-06-12"
        assert date.fromisoformat(result.fristende).weekday() == 5  # Samstag
        assert "ANMELDUNG" in result.rechenweg[0]

    def test_schutzende_marke_zehn_jahre_ab_anmeldetag(self) -> None:
        result = berechne_frist("schutzende_marke_de", date(2026, 6, 15))
        assert result.fristende == "2036-06-15"
        assert "§ 47" in result.rechtsgrundlage
        assert "Nachfrist" in result.hinweis


class TestJahreserklaerung:
    def test_ohne_berater_ende_juli_folgejahr(self) -> None:
        result = berechne_frist(
            "jahreserklaerung", date(2025, 12, 31), bundesland="BE", mit_berater=False
        )
        assert result.fristende == "2026-07-31"

    def test_mit_berater_letzter_februartag_zweitfolgejahr_mit_verschiebung(self) -> None:
        # Steuerjahr 2025 -> 28.02.2027 (Sonntag) -> § 108 AO -> 01.03.2027
        result = berechne_frist(
            "jahreserklaerung", date(2025, 12, 31), bundesland="BE", mit_berater=True
        )
        assert result.fristende == "2027-03-01"
        assert result.verschoben_von == "2027-02-28"


class TestFeiertagsKalender:
    def test_bewegliche_feiertage_2026(self) -> None:
        by = feiertage(2026, "BY")
        assert date(2026, 4, 3) in by  # Karfreitag (Ostern 2026 = 05.04.)
        assert date(2026, 6, 4) in by  # Fronleichnam (Ostern + 60)
        assert date(2026, 6, 4) not in feiertage(2026, "BE")  # kein Fronleichnam in BE

    def test_buss_und_bettag_nur_sachsen(self) -> None:
        # Mittwoch vor dem 23.11.2026 = 18.11.2026
        assert date(2026, 11, 18) in feiertage(2026, "SN")
        assert date(2026, 11, 18) not in feiertage(2026, "BE")


class TestFehlerfaelle:
    def test_unbekannter_fristtyp(self) -> None:
        with pytest.raises(ParameterNotFoundError, match="fristtyp"):
            berechne_frist("mondlandung", date(2026, 1, 1))

    def test_unbekanntes_bundesland(self) -> None:
        with pytest.raises(ToolInputError, match="Bundesland"):
            berechne_frist("ustva_abgabe", date(2026, 1, 1), bundesland="XX")

    def test_ai_act_stichtag_fest(self) -> None:
        result = berechne_frist(
            "ai_act_hochrisiko_anhang3", date(2026, 1, 1), referenz_datum=date(2026, 1, 1)
        )
        assert result.fristende == "2026-08-02"
        assert result.rechtsgrundlage == "Art. 113 VO (EU) 2024/1689"
        assert result.warnstufe == "NIEDRIG"
