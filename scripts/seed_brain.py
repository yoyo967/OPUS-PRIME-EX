"""Seed-Gehirn fuer die Cloud-Demo: NICHT-persoenliche Projekt-Wissenskarten.

Der Live-Snapshot des persoenlichen Gehirns (brain/raw|wiki) ist gitignored und wandert NIE in
die Cloud. Damit die Brain-Suche in der Demo trotzdem etwas findet, backt der Dockerfile diese
committeten, unkritischen Projekt-Karten via BrainStore (Format garantiert) in brain/raw.

Nutzung:  python scripts/seed_brain.py <brain-root>   (Default: ./brain)
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

from src.brain.store import BrainStore  # noqa: E402

# (Titel, Inhalt, Tags) — bewusst Projekt-Doku, nichts Persoenliches/Sensibles.
SEED: list[tuple[str, str, list[str]]] = [
    (
        "OPUS/Agenticum - Systemueberblick",
        "Agenticum (agenticum.xyz) = Systems-Architect-Build-Studio. OPUS-System: OPUS PRIME EX "
        "(Rechts-/Steuer-Assistent, spec-driven, Guardrails G1-G8, deterministic-first), OPUS "
        "DECK (VS-Code-artige Multi-Agent-Workbench, Theia + ACP + MCP), OPUS FLOW (geplant), "
        "Second Brain (Karpathy-Muster, MCP). GCP-first, EU-first (europe-west3), DSGVO.",
        ["ueberblick", "opus", "agenticum"],
    ),
    (
        "Masterplan & Bau-Sequenz",
        "Bau-Sequenz (Keystone): 1) ACP/MCP-Backbone, 2) Second Brain (B0-B3 fertig), 3) Providers "
        "(Gemini/Vertex-EU + Cloud-GPU-Gemma), 4) GCP-Deploy (Backend + Workbench live), 5) OPUS "
        "FLOW. Danach Auth-Haertung (IAP/Proxy). Grundsatz: 'alles, aber eins nach dem anderen, "
        "baue stabil.' SSoT: opus-deck/docs/MASTERPLAN.md.",
        ["masterplan", "bau-sequenz", "roadmap"],
    ),
    (
        "A5-Compliance-Stand & Gaps",
        "BSI A5 (KI-Pruefrahmen, Community Draft 06.07.2026, OSCAL, EU AI Act + CRA) als "
        "Governance-Linse. Mapping: opus-deck/spec/A5_COMPLIANCE.md. Erfuellt u.a.: Guardrails, "
        "EU-first/"
        "DSGVO, Perfect-Twin-Specs, Vier-Gates-CI, RA/StB-Sign-off, Rollen-Matrix, Incident-"
        "Runbook. Offene Gaps: Threat-Model, IAP/Auth-Haertung, Model Cards, Bias/Robustheit, "
        "Risikoregister, OSCAL-CI. Ehrlich: Draft-Ausrichtung, keine Zertifizierung.",
        ["a5", "compliance", "gaps", "governance"],
    ),
    (
        "Non-Negotiables",
        "GCP-first, EU-first (europe-west3), DSGVO; kein Tracking ohne Consent; Secrets nur im "
        "Secret Manager. Deterministic-first: Modell erfindet keine Zahlen/Zitate, Guardrails "
        "blocken Unbelegtes. Review-Gate: Agenten schlagen vor, Menschen entscheiden. Vier Gates "
        "gruen vor Merge. Ehrlich vor Ueber-Behauptung.",
        ["non-negotiables", "prinzipien"],
    ),
    (
        "Aktueller Cloud-Stand",
        "OPUS PRIME EX Backend live auf Cloud Run (europe-west3): Gemini/Vertex-EU antwortet durch "
        "die volle Guardrail-Pipeline; Anthropic erst mit Guthaben. OPUS DECK Workbench live mit "
        "Agent- + Second-Brain-Panel. Naechste Bau-Stufe: Auth-Haertung (Single-Origin-Proxy, "
        "Backend privat). Runbook: docs/deploy_cloud_run.md.",
        ["stand", "cloud", "naechste-schritte"],
    ),
]


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else _ROOT / "brain"
    store = BrainStore(root)
    vorhanden = {d.titel for d in store.alle() if d.schicht == "raw"}
    n = 0
    for titel, inhalt, tags in SEED:
        if titel in vorhanden:
            continue
        store.add_raw(titel, inhalt, tags=tags)
        n += 1
    print(f"[seed_brain] {n} Karten in {root}/raw geschrieben ({len(SEED) - n} schon vorhanden).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
