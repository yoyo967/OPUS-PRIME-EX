"""BrainStore — Datei-Store des Second Brain (Markdown + YAML-Frontmatter).

raw/ ist append-only (immutable Quellen); wiki/ wird agenten-gepflegt (Writes review-gated,
Phase B2). IDs sind relative Pfade ab dem Brain-Root (z. B. "raw/2026-07-07_notiz.md").

# SPEC: opus-deck/spec/SECOND_BRAIN.md §2 (Schichten), §6 (git-native)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from src.shared.exceptions import ToolInputError

_FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.DOTALL)
_SLUG = re.compile(r"[^a-z0-9]+")


def _slugify(text: str) -> str:
    slug = _SLUG.sub("-", text.lower()).strip("-")
    return slug[:60] or "notiz"


@dataclass(frozen=True)
class BrainDoc:
    """Ein Dokument im Gehirn (raw oder wiki)."""

    id: str  # relativer Pfad ab Brain-Root, z. B. "raw/2026-07-07_notiz.md"
    schicht: str  # "raw" | "wiki"
    titel: str
    text: str
    meta: dict[str, Any] = field(default_factory=dict)


class BrainStore:
    """Markdown-basierter Store ueber ein brain/-Verzeichnis (raw/ + wiki/ + BRAIN.md)."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.raw_dir = root / "raw"
        self.wiki_dir = root / "wiki"
        self.schema_pfad = root / "BRAIN.md"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.wiki_dir.mkdir(parents=True, exist_ok=True)

    # --- Lesen ---------------------------------------------------------------
    def _parse(self, pfad: Path) -> BrainDoc:
        roh = pfad.read_text(encoding="utf-8")
        match = _FRONTMATTER.match(roh)
        if match:
            meta_raw = yaml.safe_load(match.group(1)) or {}
            meta = meta_raw if isinstance(meta_raw, dict) else {}
            text = match.group(2).strip()
        else:
            meta, text = {}, roh.strip()
        rel = pfad.relative_to(self.root).as_posix()
        schicht = "wiki" if rel.startswith("wiki/") else "raw"
        titel = str(meta.get("titel") or pfad.stem)
        return BrainDoc(id=rel, schicht=schicht, titel=titel, text=text, meta=meta)

    def read(self, doc_id: str) -> BrainDoc:
        pfad = (self.root / doc_id).resolve()
        if self.root.resolve() not in pfad.parents or not pfad.is_file():
            raise ToolInputError(f"Dokument nicht gefunden: {doc_id!r}")
        return self._parse(pfad)

    def liste(self, schicht: str | None = None) -> list[BrainDoc]:
        docs: list[BrainDoc] = []
        bereiche = [self.raw_dir, self.wiki_dir]
        if schicht == "raw":
            bereiche = [self.raw_dir]
        elif schicht == "wiki":
            bereiche = [self.wiki_dir]
        for d in bereiche:
            for pfad in sorted(d.glob("*.md")):
                docs.append(self._parse(pfad))
        return docs

    def alle(self) -> list[BrainDoc]:
        """Alle Dokumente (raw + wiki) — Basis fuer die Indexierung."""
        return self.liste(None)

    def schema(self) -> str:
        return self.schema_pfad.read_text(encoding="utf-8") if self.schema_pfad.exists() else ""

    # --- Schreiben (raw: append-only) ----------------------------------------
    def add_raw(
        self, titel: str, inhalt: str, tags: list[str] | None = None,
        quelle: str | None = None,
    ) -> BrainDoc:
        """Rohquelle ablegen (append-only, immutable). Gibt das erzeugte BrainDoc zurueck."""
        if not inhalt.strip():
            raise ToolInputError("Leerer Inhalt kann nicht abgelegt werden.")
        basis = f"{date.today().isoformat()}_{_slugify(titel)}"
        pfad = self.raw_dir / f"{basis}.md"
        n = 2
        while pfad.exists():  # nie ueberschreiben (append-only)
            pfad = self.raw_dir / f"{basis}-{n}.md"
            n += 1
        meta: dict[str, Any] = {"titel": titel, "erstellt": date.today().isoformat()}
        if tags:
            meta["tags"] = tags
        if quelle:
            meta["quelle"] = quelle
        vorne = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False).strip()
        pfad.write_text(f"---\n{vorne}\n---\n{inhalt.strip()}\n", encoding="utf-8")
        return self._parse(pfad)
