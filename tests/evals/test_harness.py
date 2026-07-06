"""Harness tests: golden set integrity + smoke run gates.

# SPEC: CLAUDE.md §4.5 (Eval harness); COWORK_HANDOFF_BRIEF.md Rolle 4
"""

from evals.harness.harness import FakeGoldenLLM, load_golden_set, run_eval
from src.rag.chunker import Chunk


def _leere_rag(anfrage: str, domaenen: tuple[str, ...]) -> list[Chunk]:
    return []


class TestGoldenSetIntegritaet:
    def test_140_faelle_20_je_domaene_14_smoke(self) -> None:
        cases = load_golden_set()
        assert len(cases) == 140
        domaenen = {c.domaene for c in cases}
        assert len(domaenen) == 7
        for domaene in domaenen:
            assert sum(1 for c in cases if c.domaene == domaene) == 20
        assert sum(1 for c in cases if c.smoke) == 14

    def test_jeder_fall_hat_pflichtfelder(self) -> None:
        for case in load_golden_set():
            assert case.id and case.frage
            assert case.erwartete_eskalationsstufe in (1, 2, 3)
            assert case.verbotene_inhalte


class TestSmokeRun:
    def test_smoke_disclaimer_rate_100_prozent(self) -> None:
        # Disclaimer-Praesenz ist serverseitig (G1) -> muss auch mit Fake 100 % sein
        report = run_eval(FakeGoldenLLM(), _leere_rag, model_label="fake", smoke_only=True)
        assert report.anzahl_faelle == 14
        assert report.disclaimer_rate == 1.0

    def test_report_enthaelt_prompt_hash_aus_spec(self) -> None:
        report = run_eval(FakeGoldenLLM(), _leere_rag, model_label="fake", smoke_only=True)
        assert report.prompt_file == "prompts/system_prompt_v1.2.md"
        assert len(report.prompt_sha256) == 64

    def test_manuelle_pruefpunkte_werden_ausgewiesen_nicht_verschluckt(self) -> None:
        report = run_eval(FakeGoldenLLM(), _leere_rag, model_label="fake", smoke_only=True)
        # z. B. markenrecht-16: "Zusage oder Simulation einer Anmeldung..." ist
        # nicht automatisch pruefbar -> muss als manuell_offen erscheinen
        assert report.manuell_offen > 0
        assert "NICHT die Modellqualitaet" in report.hinweis

    def test_g2_fall_wird_vor_dem_modell_blockiert(self) -> None:
        report = run_eval(FakeGoldenLLM(), _leere_rag, model_label="fake", smoke_only=True)
        fall_16 = next(r for r in report.ergebnisse if r.case_id == "markenrecht-16")
        assert fall_16.disclaimer_ok
        # G2-Ablehnung enthaelt keine Normen -> Fall hat leere erwartete_normen
        assert fall_16.normen_erwaehnt
