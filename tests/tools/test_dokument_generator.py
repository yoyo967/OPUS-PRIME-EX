"""Tests for dokument_generator: ENTWURF header, disclaimer, filing block.

# SPEC: AGENT_ARCHITECTURE.md §3.4 (Regel: ENTWURF-Kopfzeile + Disclaimer;
# Einreichungsdokumente gesperrt)
"""

import pytest

from src.shared.exceptions import ParameterNotFoundError, ToolInputError
from src.shared.texts import text as i18n_text
from src.tools.dokument_generator import generate


class TestEntwuerfe:
    def test_avv_checkliste_mit_kopfzeile_und_disclaimer(self) -> None:
        dokument = generate("avv_checkliste")
        markdown = dokument.als_markdown()
        assert markdown.startswith(f"> **{i18n_text('entwurf_kopfzeile')}**")
        assert i18n_text("pflicht_disclaimer") in markdown
        assert "Art. 28 Abs. 3 DSGVO" in markdown
        # Pflichtinhalte lit. a-h vollstaendig (Legal-Review #7 bestaetigt)
        for lit in "abcdefgh":
            assert f"lit. {lit}:" in markdown

    def test_markenanmeldung_vorbereitung_ohne_einreichung(self) -> None:
        dokument = generate("markenanmeldung_vorbereitung")
        markdown = dokument.als_markdown()
        assert "keine Einreichung" in dokument.titel
        assert "KEINE Vollstaendigkeitsgarantie" in markdown
        assert "Nizza" in markdown

    def test_alle_template_typen_generierbar(self) -> None:
        for typ in (
            "avv_checkliste",
            "vvt_eintrag",
            "dpia_geruest",
            "gewerbeanmeldung_checkliste",
            "ai_act_gap_liste",
            "beratervorbereitung_dossier",
            "markenanmeldung_vorbereitung",
        ):
            dokument = generate(typ)
            assert dokument.abschnitte
            assert dokument.kopfzeile == i18n_text("entwurf_kopfzeile")


class TestSperren:
    @pytest.mark.parametrize(
        "gesperrt",
        [
            "steuererklaerung",
            "ust_voranmeldung",
            "markenanmeldung_einreichung",
            "widerspruch_einreichung",
            "elster_uebermittlung",
        ],
    )
    def test_einreichungsdokumente_gesperrt(self, gesperrt: str) -> None:
        with pytest.raises(ToolInputError, match="gesperrt"):
            generate(gesperrt)

    def test_unbekannter_typ(self) -> None:
        with pytest.raises(ParameterNotFoundError, match="Unbekannter Dokumenttyp"):
            generate("kaffeebestellung")
