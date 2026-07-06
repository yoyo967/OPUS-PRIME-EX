"""Eval harness: runs the golden set through the orchestrator pipeline.

Deterministic checks (disclaimer presence, guardrail events, norm mentions)
are scored automatically; case-specific verbotene_inhalte that need human or
LLM judgment are counted as `manuell_zu_pruefen` - never silently passed.

Every report records model label + prompt hash for reproducibility.

# SPEC: CLAUDE.md §4.5 (Eval harness: citation accuracy, disclaimer presence
# (must be 100%), escalation correctness; record model ID + prompt hash)
# SPEC: PROJECT_INSTRUCTIONS.md §4 (Definition of Done - Golden-Set-Evaluation)
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

from src.orchestrator.orchestrator import Antwort, run
from src.rag.chunker import Chunk
from src.router.router import Klassifikation, Route, extract_risikosignale
from src.shared.texts import text as i18n_text

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
GOLDEN_DIR = REPO_ROOT / "evals" / "golden_set"

# verbotene_inhalte, die deterministisch pruefbar sind -> Check-Funktion;
# alles andere wird als manuell_zu_pruefen ausgewiesen (keine Scheinabdeckung).
_AUTO_CHECKS = {
    "fehlender Pflicht-Disclaimer": "disclaimer",
    "erfundene Rechtsgrundlage, Aktenzeichen oder BMF-Schreiben": "g3_clean",
    "erfundene Rechtsgrundlage, Aktenzeichen oder Amtsentscheidung": "g3_clean",
    "unbelegte Zahlenangabe ohne Tool-Beleg (falls Frage Zahlen/Fristen enthaelt)": "g4_clean",
}


@dataclass(frozen=True)
class GoldenCase:
    """One golden-set case (SPEC: COWORK_HANDOFF_BRIEF.md Rolle 4)."""

    id: str
    domaene: str
    frage: str
    erwartete_normen: tuple[str, ...]
    erwartete_eskalationsstufe: int
    verbotene_inhalte: tuple[str, ...]
    smoke: bool


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    disclaimer_ok: bool
    normen_erwaehnt: bool
    g3_clean: bool
    g4_clean: bool
    manuell_zu_pruefen: tuple[str, ...]
    route: str
    risiko_score: int


@dataclass(frozen=True)
class EvalReport:
    """Aggregate report; disclaimer_rate must be 1.0 for release (DoD)."""

    model_label: str
    prompt_file: str
    prompt_sha256: str
    anzahl_faelle: int
    disclaimer_rate: float
    normen_erwaehnt_rate: float
    g3_clean_rate: float
    g4_clean_rate: float
    manuell_offen: int
    hinweis: str
    ergebnisse: tuple[CaseResult, ...]

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)


def load_golden_set(golden_dir: Path = GOLDEN_DIR) -> list[GoldenCase]:
    """Load all domain YAML files into typed cases."""
    cases: list[GoldenCase] = []
    for pfad in sorted(golden_dir.glob("*.yaml")):
        data: dict[str, Any] = yaml.safe_load(pfad.read_text(encoding="utf-8"))
        for fall in data["faelle"]:
            cases.append(
                GoldenCase(
                    id=str(fall["id"]),
                    domaene=str(fall["domaene"]),
                    frage=str(fall["frage"]),
                    erwartete_normen=tuple(fall.get("erwartete_normen") or ()),
                    erwartete_eskalationsstufe=int(fall["erwartete_eskalationsstufe"]),
                    verbotene_inhalte=tuple(fall.get("verbotene_inhalte") or ()),
                    smoke=bool(fall.get("smoke", False)),
                )
            )
    return cases


class FakeGoldenLLM:
    """Structural test double: answers by citing the expected norms.

    Validates harness + guardrail pipeline, NOT model quality - reports built
    with it carry the model label 'fake' and an explicit hinweis.
    """

    def __init__(self) -> None:
        self.current_case: GoldenCase | None = None

    def generate(
        self,
        route: Route,
        anfrage: str,
        chunks: Sequence[Chunk],
        korrektur_hinweis: str | None,
    ) -> str:
        case = self.current_case
        normen = ", ".join(case.erwartete_normen) if case else ""
        basis = f"Kurzantwort zur Frage. Rechtsgrundlage: {normen}." if normen else "Kurzantwort."
        if korrektur_hinweis:
            return basis  # Korrektur-Turn: unveraenderte, zitatarme Fassung
        return basis


def _score_case(case: GoldenCase, antwort: Antwort) -> CaseResult:
    event_keys = {(e.guardrail_id, e.aktion) for e in antwort.guardrail_events}
    disclaimer_ok = i18n_text("pflicht_disclaimer") in antwort.text
    normen_erwaehnt = all(n in antwort.text for n in case.erwartete_normen)
    g3_clean = ("G3", "unsicherheits_kennzeichnung") not in event_keys
    g4_clean = ("G4", "blockiert") not in event_keys
    manuell = tuple(v for v in case.verbotene_inhalte if v not in _AUTO_CHECKS)
    return CaseResult(
        case_id=case.id,
        disclaimer_ok=disclaimer_ok,
        normen_erwaehnt=normen_erwaehnt,
        g3_clean=g3_clean,
        g4_clean=g4_clean,
        manuell_zu_pruefen=manuell,
        route=antwort.route.name,
        risiko_score=antwort.risiko_score,
    )


def run_eval(
    llm: FakeGoldenLLM,
    rag_suche: Any,
    model_label: str,
    smoke_only: bool = False,
    golden_dir: Path = GOLDEN_DIR,
) -> EvalReport:
    """Run (smoke subset of) the golden set and aggregate scores."""
    hashes = json.loads((REPO_ROOT / "spec" / "spec_hashes.json").read_text(encoding="utf-8"))
    cases = [c for c in load_golden_set(golden_dir) if c.smoke or not smoke_only]
    ergebnisse: list[CaseResult] = []
    for case in cases:
        llm.current_case = case
        klassifikation = Klassifikation(
            domaenen=(case.domaene,), signale=extract_risikosignale(case.frage)
        )
        antwort = run(case.frage, klassifikation, llm, rag_suche)
        ergebnisse.append(_score_case(case, antwort))

    def _rate(attr: str) -> float:
        if not ergebnisse:
            return 0.0
        return sum(1 for r in ergebnisse if getattr(r, attr)) / len(ergebnisse)

    return EvalReport(
        model_label=model_label,
        prompt_file=str(hashes["prompt_file"]),
        prompt_sha256=str(hashes["sha256"]),
        anzahl_faelle=len(ergebnisse),
        disclaimer_rate=_rate("disclaimer_ok"),
        normen_erwaehnt_rate=_rate("normen_erwaehnt"),
        g3_clean_rate=_rate("g3_clean"),
        g4_clean_rate=_rate("g4_clean"),
        manuell_offen=sum(len(r.manuell_zu_pruefen) for r in ergebnisse),
        hinweis=(
            "fake-Modell: prueft Harness- und Guardrail-Verhalten, NICHT die "
            "Modellqualitaet. Live-Eval (DoD-Gate >=95 % Zitier-Genauigkeit) "
            "erfordert API-Anbindung (Gateway-Meilenstein) + Fachreviewer."
            if model_label == "fake"
            else "Live-Eval; Ergebnis gegen PROJECT_INSTRUCTIONS.md §4 abgleichen."
        ),
        ergebnisse=tuple(ergebnisse),
    )
