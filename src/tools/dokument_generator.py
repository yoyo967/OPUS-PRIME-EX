"""Template-driven document drafts; filing documents are hard-blocked.

# SPEC: AGENT_ARCHITECTURE.md §3.4 (dokument_generator)
# SPEC: AGENT_ARCHITECTURE.md §4 (P2: Entwuerfe ohne Freigabe, immer als ENTWURF
# markiert; P4: Behoerdenuebermittlung technisch nicht vorhanden)
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from src.shared.exceptions import ParameterNotFoundError, ToolInputError
from src.shared.texts import text as i18n_text

_TEMPLATES_PATH = Path(__file__).parent / "params" / "dokument_templates.yaml"


@dataclass(frozen=True)
class Dokument:
    """Draft document: ENTWURF header + content + mandatory disclaimer."""

    dokument_typ: str
    titel: str
    kopfzeile: str
    rechtsgrundlagen: tuple[str, ...]
    abschnitte: tuple[str, ...]
    disclaimer: str

    def als_markdown(self) -> str:
        zeilen = [f"> **{self.kopfzeile}**", "", f"# {self.titel}", ""]
        if self.rechtsgrundlagen:
            zeilen.append(f"Rechtsgrundlagen: {'; '.join(self.rechtsgrundlagen)}")
            zeilen.append("")
        zeilen.extend(f"- [ ] {punkt}" for punkt in self.abschnitte)
        zeilen.extend(["", f"*{self.disclaimer}*"])
        return "\n".join(zeilen)


@lru_cache(maxsize=1)
def _load_templates() -> dict[str, Any]:
    with _TEMPLATES_PATH.open(encoding="utf-8") as handle:
        loaded: dict[str, Any] = yaml.safe_load(handle)
    return loaded


def generate(dokument_typ: str, sprache: str = "de") -> Dokument:
    """Generate a draft document from the template table.

    Raises ToolInputError for blocked filing documents (reserved services).
    """
    templates = _load_templates()
    if dokument_typ in templates.get("gesperrt", []):
        # SPEC: AGENT_ARCHITECTURE.md §3.4 Regel (Einreichungsdokumente gesperrt);
        # PROJECT_INSTRUCTIONS.md §5 Nr. 2/4
        raise ToolInputError(
            f"Dokumenttyp {dokument_typ!r} ist gesperrt: Erstellung/Einreichung ist "
            f"zugelassenen Berufstraegern vorbehalten (RDG/StBerG; DPMA/EUIPO/WIPO-"
            f"Sperre). Verfuegbar ist z. B. ein Vorbereitungs-Dossier."
        )
    dokumente: dict[str, Any] = templates["dokumente"]
    if dokument_typ not in dokumente:
        raise ParameterNotFoundError(
            f"Unbekannter Dokumenttyp {dokument_typ!r}. "
            f"Verfuegbar: {', '.join(sorted(dokumente))}."
        )
    vorlage = dokumente[dokument_typ]
    return Dokument(
        dokument_typ=dokument_typ,
        titel=str(vorlage["titel"]),
        kopfzeile=i18n_text("entwurf_kopfzeile", sprache),
        rechtsgrundlagen=tuple(vorlage.get("rechtsgrundlagen") or ()),
        abschnitte=tuple(vorlage["abschnitte"]),
        disclaimer=i18n_text("pflicht_disclaimer", sprache),
    )
