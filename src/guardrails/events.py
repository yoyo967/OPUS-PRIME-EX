"""Guardrail event record shared by all G1-G8 processors.

# SPEC: AGENT_ARCHITECTURE.md §5 (Guardrails & Compliance-Checks)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GuardrailEvent:
    """One guardrail decision, logged into the audit trail (G8)."""

    guardrail_id: str  # "G1".."G8"
    aktion: str  # z. B. "disclaimer_angehaengt", "blockiert", "hinweis"
    detail: str = ""
