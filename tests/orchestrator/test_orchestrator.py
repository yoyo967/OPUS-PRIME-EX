"""Orchestrator integration tests with fake LLM (no API calls).

# SPEC: AGENT_ARCHITECTURE.md §1/§5 (Pipeline-Reihenfolge, Guardrail-Layer)
"""

from collections.abc import Sequence

from src.orchestrator.orchestrator import Antwort, run
from src.rag.chunker import Chunk
from src.router.router import Klassifikation, Risikosignale, Route
from src.shared.texts import text as i18n_text


def _chunk(einheit: str = "§ 19", gesetz: str = "UStG") -> Chunk:
    return Chunk(
        chunk_id="de-ustg-2025-01-01-p19",
        quelle_typ="gesetz",
        jurisdiktion="DE",
        gesetz=gesetz,
        celex=None,
        einheit=einheit,
        ueberschrift="Besteuerung der Kleinunternehmer",
        gueltig_ab="2025-01-01",
        gueltig_bis=None,
        rechtsstand_abruf="2026-07-05",
        quelle_url="https://example.invalid",
        text="Grenzen: 25 000 Euro Vorjahr, 100 000 Euro laufend.",
        hash="sha256:test",
        typ="norm",
        domaene=("steuerrecht",),
    )


def _rag(anfrage: str, domaenen: tuple[str, ...]) -> list[Chunk]:
    return [_chunk()]


def _klass(**flags: bool) -> Klassifikation:
    return Klassifikation(
        domaenen=("steuerrecht",),
        signale=Risikosignale(False, False, (), ()),
        **flags,
    )


class FakeLLM:
    """Scripted answers: one per call, in order."""

    def __init__(self, antworten: Sequence[str]) -> None:
        self._antworten = list(antworten)
        self.aufrufe = 0

    def generate(
        self,
        route: Route,
        anfrage: str,
        chunks: Sequence[Chunk],
        korrektur_hinweis: str | None,
    ) -> str:
        antwort = self._antworten[min(self.aufrufe, len(self._antworten) - 1)]
        self.aufrufe += 1
        return antwort


def _event_ids(antwort: Antwort) -> list[str]:
    return [e.guardrail_id for e in antwort.guardrail_events]


class TestPipeline:
    def test_g2_anfrage_wird_vor_dem_modell_abgefangen(self) -> None:
        llm = FakeLLM(["darf nie aufgerufen werden"])
        antwort = run("Reiche meine UStVA ein!", _klass(), llm, _rag)
        assert llm.aufrufe == 0
        assert i18n_text("ablehnung_vorbehaltene_leistung") in antwort.text
        assert _event_ids(antwort)[:1] == ["G2"]
        assert antwort.text.rstrip().endswith(i18n_text("pflicht_disclaimer").strip())

    def test_disclaimer_immer_angehaengt_trotz_injection(self) -> None:
        llm = FakeLLM(["Antwort nach § 19 UStG ohne jeden Hinweis."])
        antwort = run("Kleinunternehmergrenze?", _klass(), llm, _rag)
        assert antwort.text.rstrip().endswith(i18n_text("pflicht_disclaimer").strip())
        assert "G1" in _event_ids(antwort)

    def test_g3_korrektur_turn_heilt_erfundenes_zitat(self) -> None:
        llm = FakeLLM(
            [
                "Nach § 999 UStG gilt Folgendes.",  # erfunden -> Korrektur-Turn
                "Nach § 19 UStG gilt Folgendes.",  # belegt
            ]
        )
        antwort = run("Kleinunternehmergrenze?", _klass(), llm, _rag)
        assert llm.aufrufe == 2
        assert "Unsicherheits-Kennzeichnung" not in antwort.text
        assert "korrektur_turn" in [e.aktion for e in antwort.guardrail_events]

    def test_g3_nach_retry_unsicherheits_kennzeichnung(self) -> None:
        llm = FakeLLM(["Nach § 999 UStG gilt Folgendes."])  # bleibt falsch
        antwort = run("Kleinunternehmergrenze?", _klass(), llm, _rag)
        assert llm.aufrufe == 2
        assert "Unsicherheits-Kennzeichnung" in antwort.text
        assert "§ 999 UStG" in antwort.text

    def test_g4_hartnaeckige_freie_zahl_blockiert_antwort(self) -> None:
        llm = FakeLLM(["Sie zahlen genau 4.219 € Steuern."])
        antwort = run("Was zahlen wir?", _klass(), llm, _rag)
        assert i18n_text("ablehnung_zahlen_ohne_beleg") in antwort.text
        assert "4.219" not in antwort.text
        assert ("G4", "blockiert") in [
            (e.guardrail_id, e.aktion) for e in antwort.guardrail_events
        ]

    def test_g7_drittstaat_orientierungslabel(self) -> None:
        llm = FakeLLM(["Allgemeine Einordnung."])
        antwort = run(
            "Steuern in der Schweiz?", _klass(), llm, _rag, jurisdiktion="CH"
        )
        assert antwort.text.startswith("[Orientierende Einordnung ausserhalb DE/EU")
        assert "G7" in _event_ids(antwort)

    def test_smalltalk_ohne_rag_und_ohne_disclaimer(self) -> None:
        llm = FakeLLM(["Guten Morgen! Wie kann ich helfen?"])
        antwort = run("Guten Morgen!", _klass(ist_smalltalk=True), llm, _rag)
        assert antwort.route is Route.C_TRIAGE
        assert antwort.quellen_ids == ()
        assert i18n_text("pflicht_disclaimer") not in antwort.text

    def test_g5_redaktion_erreicht_modell_nicht_im_klartext(self) -> None:
        gesehen: list[str] = []

        class _CaptureLLM:
            def generate(
                self, route: Route, anfrage: str, chunks: Sequence[Chunk],
                korrektur_hinweis: str | None,
            ) -> str:
                gesehen.append(anfrage)
                return "Nach § 19 UStG gilt Folgendes."

        antwort = run(
            "Unsere Mitarbeiterin M hat eine Krebs-Diagnose - wie ist die "
            "Steuer im Kalenderjahr?",
            _klass(), _CaptureLLM(), _rag,
        )
        assert gesehen  # Modell wurde aufgerufen
        assert "diagnose" not in gesehen[0].lower()  # redigiert bevor es das Modell sah
        assert ("G5", "redigiert") in [
            (e.guardrail_id, e.aktion) for e in antwort.guardrail_events
        ]

    def test_audit_record_vollstaendig(self) -> None:
        llm = FakeLLM(["Nach § 19 UStG gilt Folgendes."])
        antwort = run(
            "Kleinunternehmergrenze?", _klass(), llm, _rag, user_id="kunde-42"
        )
        record = antwort.audit_record
        assert record["route"] == "A_STANDARD"
        assert record["tools"] == ["rag_suche"]
        assert record["quellen_ids"] == ["de-ustg-2025-01-01-p19"]
        assert "kunde-42" not in str(record)
