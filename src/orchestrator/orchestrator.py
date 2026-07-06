"""Orchestrator: tool loop, guardrail pipeline, upward-only escalation.

The LLM sits behind the LLMClient protocol; production wiring to the Anthropic
API follows in the gateway milestone. All enforcement lives here, server-side -
never in the prompt alone.

# SPEC: AGENT_ARCHITECTURE.md §1 (Systemueberblick), §5 (Guardrail-Layer)
# SPEC: CLAUDE.md §3 (guardrail failures -> user-safe messages, no stack traces)
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Protocol

from src.guardrails.audit import create_audit_record
from src.guardrails.events import GuardrailEvent
from src.guardrails.post import (
    apply_disclaimer_g1,
    collect_allowed_numbers,
    stale_warnung_g6,
    validate_zahlen_g4,
    validate_zitate_g3,
)
from src.guardrails.pre import check_jurisdiktion_g7, check_pii_g5, check_scope_g2
from src.rag.chunker import Chunk
from src.router.router import Klassifikation, Route, route_for
from src.shared.texts import text as i18n_text
from src.tools.steuer_rechner import CalculationResult

# SPEC: KNOWLEDGE_ARCHITECTURE.md §4.6 / AGENT_ARCHITECTURE.md §5 G3 (max. 1 Retry)
MAX_KORREKTUR_TURNS = 1


class LLMClient(Protocol):
    """Model access behind an interface; tests use fakes, production the API."""

    def generate(
        self,
        route: Route,
        anfrage: str,
        chunks: Sequence[Chunk],
        korrektur_hinweis: str | None,
    ) -> str:
        """Produce an answer draft for the given route and retrieval context."""
        ...


RagSuche = Callable[[str, tuple[str, ...]], list[Chunk]]


@dataclass(frozen=True)
class Antwort:
    """Final response envelope incl. route, sources and guardrail events."""

    text: str
    route: Route
    risiko_score: int
    quellen_ids: tuple[str, ...]
    guardrail_events: tuple[GuardrailEvent, ...]
    audit_record: dict[str, object] = field(default_factory=dict)


def run(
    anfrage: str,
    klassifikation: Klassifikation,
    llm: LLMClient,
    rag_suche: RagSuche,
    tool_results: Sequence[CalculationResult] = (),
    user_id: str = "anonym",
    sprache: str = "de",
    jurisdiktion: str = "DE",
) -> Antwort:
    """Run one request through pre-guardrails, tool loop, model, post-guardrails."""
    events: list[GuardrailEvent] = []
    tools_benutzt: list[str] = []
    route, score = route_for(klassifikation)

    def _final(text_out: str, quellen: tuple[str, ...]) -> Antwort:
        record = create_audit_record(
            anfrage=anfrage,
            user_id=user_id,
            route=route.name,
            risiko_score=score,
            tools=tools_benutzt,
            quellen_ids=quellen,
            events=events,
        )
        return Antwort(
            text=text_out,
            route=route,
            risiko_score=score,
            quellen_ids=quellen,
            guardrail_events=tuple(events),
            audit_record=record,
        )

    # --- Pre-Guardrails -----------------------------------------------------
    g2 = check_scope_g2(anfrage)
    if g2 is not None:
        # SPEC: AGENT_ARCHITECTURE.md §5 G2 (hoefliche Ablehnung, Template-basiert)
        events.append(g2)
        ablehnung = i18n_text("ablehnung_vorbehaltene_leistung", sprache)
        text_out, g1 = apply_disclaimer_g1(
            ablehnung, i18n_text("pflicht_disclaimer", sprache)
        )
        events.append(g1)
        return _final(text_out, ())

    g5 = check_pii_g5(anfrage)
    if g5 is not None:
        events.append(g5)
    g7 = check_jurisdiktion_g7(jurisdiktion)
    if g7 is not None:
        events.append(g7)

    # --- Tool-Loop ------------------------------------------------------------
    # Pflicht-Tool bei jeder Normfrage: mindestens ein rag_suche-Aufruf, bevor
    # eine Antwort mit Normzitat freigegeben wird (SPEC: AGENT_ARCHITECTURE.md §3.1).
    chunks: list[Chunk] = []
    if not klassifikation.ist_smalltalk:
        chunks = rag_suche(anfrage, klassifikation.domaenen)
        tools_benutzt.append("rag_suche")
    tools_benutzt.extend(f"steuer_rechner:{r.art}" for r in tool_results)

    # --- Modell + Korrektur-Loop (G3/G4) --------------------------------------
    allowed = collect_allowed_numbers(anfrage, tool_results, chunks)
    korrektur_hinweis: str | None = None
    antwort_text = ""
    unbelegte: list[str] = []
    freie: list[str] = []
    for versuch in range(MAX_KORREKTUR_TURNS + 1):
        antwort_text = llm.generate(route, anfrage, chunks, korrektur_hinweis)
        unbelegte, g3 = validate_zitate_g3(antwort_text, chunks)
        freie, g4 = validate_zahlen_g4(antwort_text, allowed)
        if g3 is None and g4 is None:
            break
        if g3 is not None:
            events.append(g3)
        if g4 is not None:
            events.append(g4)
        if versuch < MAX_KORREKTUR_TURNS:
            probleme: list[str] = []
            if unbelegte:
                probleme.append(f"unbelegte Fundstellen: {', '.join(unbelegte)}")
            if freie:
                probleme.append(f"Zahlen ohne Tool-/Quellen-Beleg: {', '.join(freie)}")
            korrektur_hinweis = (
                "Korrigiere die Antwort. Entferne oder belege: " + "; ".join(probleme)
            )
            events.append(
                GuardrailEvent("G3" if unbelegte else "G4", "korrektur_turn")
            )

    # Nach dem Korrektur-Turn: G3 -> Unsicherheits-Kennzeichnung
    # (SPEC: KNOWLEDGE_ARCHITECTURE.md §4.6), G4 -> Antwort blockieren
    # (SPEC: AGENT_ARCHITECTURE.md §5 G4 "Block & Retry").
    if freie:
        antwort_text = i18n_text("ablehnung_zahlen_ohne_beleg", sprache)
        events.append(GuardrailEvent("G4", "blockiert"))
    elif unbelegte:
        antwort_text += (
            "\n\n[Unsicherheits-Kennzeichnung: Folgende Fundstellen konnten nicht "
            f"gegen die Wissensbasis validiert werden: {', '.join(sorted(set(unbelegte)))}]"
        )
        events.append(GuardrailEvent("G3", "unsicherheits_kennzeichnung"))

    # --- Post-Guardrails -------------------------------------------------------
    if g7 is not None:
        antwort_text = (
            "[Orientierende Einordnung ausserhalb DE/EU - keine belastbare "
            "Rechtsinformation; bitte lokale Beratung einschalten.]\n\n" + antwort_text
        )
    antwort_text, g6 = stale_warnung_g6(
        antwort_text, chunks, i18n_text("stale_warnung", sprache)
    )
    if g6 is not None:
        events.append(g6)
    if not klassifikation.ist_smalltalk:
        antwort_text, g1 = apply_disclaimer_g1(
            antwort_text, i18n_text("pflicht_disclaimer", sprache)
        )
        events.append(g1)

    return _final(antwort_text, tuple(c.chunk_id for c in chunks))
