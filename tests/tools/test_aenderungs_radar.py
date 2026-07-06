"""Tests for aenderungs_radar (changelog filtering).

# SPEC: AGENT_ARCHITECTURE.md §3.5
"""

from datetime import date
from pathlib import Path

import pytest

from src.shared.exceptions import ToolInputError
from src.tools.aenderungs_radar import abfrage

FIXTURE = """
eintraege:
  - {datum: "2026-06-01", domaene: [steuerrecht], typ: neues_dokument,
     titel: "BMF-Schreiben X", quelle_id: "bmf-x"}
  - {datum: "2026-06-20", domaene: [markenrecht], typ: neue_fassung,
     titel: "MarkenG-Aenderung", quelle_id: "de-markeng"}
  - {datum: "2026-07-01", domaene: [dsgvo, eu_ai_act], typ: neues_dokument,
     titel: "EDSA-Leitlinie Y", quelle_id: "edsa-y"}
"""


@pytest.fixture
def changelog(tmp_path: Path) -> Path:
    pfad = tmp_path / "changelog.yaml"
    pfad.write_text(FIXTURE, encoding="utf-8")
    return pfad


class TestAbfrage:
    def test_filtert_nach_domaene_und_datum(self, changelog: Path) -> None:
        treffer = abfrage(("steuerrecht",), date(2026, 5, 1), changelog)
        assert [e.quelle_id for e in treffer] == ["bmf-x"]
        assert abfrage(("steuerrecht",), date(2026, 6, 15), changelog) == []

    def test_mehrere_domaenen_neueste_zuerst(self, changelog: Path) -> None:
        treffer = abfrage(("markenrecht", "dsgvo"), date(2026, 6, 1), changelog)
        assert [e.quelle_id for e in treffer] == ["edsa-y", "de-markeng"]

    def test_stichtag_inklusive(self, changelog: Path) -> None:
        treffer = abfrage(("markenrecht",), date(2026, 6, 20), changelog)
        assert len(treffer) == 1

    def test_ohne_domaene_fehler(self, changelog: Path) -> None:
        with pytest.raises(ToolInputError):
            abfrage((), date(2026, 1, 1), changelog)

    def test_fehlendes_changelog_leeres_ergebnis(self, tmp_path: Path) -> None:
        assert abfrage(("steuerrecht",), date(2026, 1, 1), tmp_path / "fehlt.yaml") == []

    def test_produktiv_changelog_ladbar(self) -> None:
        # Seed-Eintrag aus data/changelog/changelog.yaml
        treffer = abfrage(("markenrecht",), date(2026, 7, 1))
        assert any("Fixture-Basis" in e.titel for e in treffer)
