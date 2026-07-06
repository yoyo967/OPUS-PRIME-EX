"""Changelog query over the knowledge-base for proactive change alerts.

The changelog is written by the ingest pipeline (Aktualitaets-Monitor,
KNOWLEDGE_ARCHITECTURE.md §3); this tool only reads and filters it.

# SPEC: AGENT_ARCHITECTURE.md §3.5 (aenderungs_radar)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from src.shared.exceptions import ToolInputError

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_CHANGELOG = REPO_ROOT / "data" / "changelog" / "changelog.yaml"


@dataclass(frozen=True)
class ChangelogEintrag:
    """One knowledge-base change (new BMF letter, amended norm, new act)."""

    datum: str  # ISO
    domaene: tuple[str, ...]
    typ: str  # neue_fassung | neues_dokument | aufgehoben | stale
    titel: str
    quelle_id: str
    detail: str = ""


def _parse(raw: dict[str, Any]) -> ChangelogEintrag:
    return ChangelogEintrag(
        datum=str(raw["datum"]),
        domaene=tuple(raw["domaene"]),
        typ=str(raw["typ"]),
        titel=str(raw["titel"]),
        quelle_id=str(raw["quelle_id"]),
        detail=str(raw.get("detail", "")),
    )


def abfrage(
    domaenen: tuple[str, ...],
    seit_datum: date,
    changelog_pfad: Path = DEFAULT_CHANGELOG,
) -> list[ChangelogEintrag]:
    """Return changelog entries matching any of the domains since the date.

    # SPEC: AGENT_ARCHITECTURE.md §3.5 (Input: domaene[], seit_datum)
    """
    if not domaenen:
        raise ToolInputError("Mindestens eine Domaene angeben.")
    if not changelog_pfad.exists():
        # Kein Changelog = noch kein Ingest-Lauf; leeres Ergebnis ist korrekt,
        # aber der Aufrufer soll das unterscheiden koennen.
        return []
    data: dict[str, Any] = yaml.safe_load(changelog_pfad.read_text(encoding="utf-8")) or {}
    eintraege = [_parse(raw) for raw in data.get("eintraege", [])]
    return sorted(
        (
            e
            for e in eintraege
            if date.fromisoformat(e.datum) >= seit_datum
            and any(d in e.domaene for d in domaenen)
        ),
        key=lambda e: e.datum,
        reverse=True,
    )
