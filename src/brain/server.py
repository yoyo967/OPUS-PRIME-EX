"""Second Brain als MCP-Server (`second-brain`, stdio; optionales Extra [mcp]).

Exponiert das geteilte Gehirn fuer BELIEBIGE MCP-Clients (OPUS PRIME EX, Flow Studio,
Claude Code, OPUS DECK) — ein Gehirn, viele Agenten. Tools: brain_search, brain_read,
brain_list, brain_add_raw. Wiki-Write (propose_wiki, review-gated) folgt in B2.

Start:  python scripts/brain_serve.py   (Konsolen-Skript: second-brain-mcp)

# SPEC: opus-deck/spec/SECOND_BRAIN.md §3 (MCP-Tool-Oberflaeche); ADR-0005
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from src.brain.retrieval import brain_search as _brain_search
from src.brain.retrieval import build_brain_index
from src.brain.store import BrainStore

_DEFAULT_ROOT = Path(__file__).resolve().parent.parent.parent / "brain"


def build_server(root: Path | None = None) -> Any:
    """Construct the FastMCP 'second-brain' server. Requires the optional 'mcp' extra.

    Root-Reihenfolge: explizites Argument > BRAIN_ROOT-Env > Default brain/.
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:  # optionales Extra [mcp]
        raise RuntimeError(
            'Der Second-Brain-MCP-Server benoetigt das Extra "mcp" (pip install ".[mcp]").'
        ) from exc

    aktive_root = root or Path(os.environ.get("BRAIN_ROOT") or _DEFAULT_ROOT)
    store = BrainStore(aktive_root)
    zustand: dict[str, Any] = {"index": build_brain_index(store.alle())}

    def _reindex() -> None:
        zustand["index"] = build_brain_index(store.alle())

    server = FastMCP("second-brain")

    @server.tool()
    def brain_search(query: str, k: int = 5) -> list[dict[str, Any]]:
        """Suche im Second Brain (raw + wiki), Hybrid-Retrieval."""
        return _brain_search(zustand["index"], query, k)

    @server.tool()
    def brain_read(doc_id: str) -> dict[str, Any]:
        """Ein Brain-Dokument lesen (id = relativer Pfad, z. B. 'raw/2026-07-07_notiz.md')."""
        d = store.read(doc_id)
        return {"id": d.id, "schicht": d.schicht, "titel": d.titel, "text": d.text, "meta": d.meta}

    @server.tool()
    def brain_list(schicht: str | None = None) -> list[dict[str, Any]]:
        """Dokumente auflisten (schicht: 'raw' | 'wiki' | None fuer beide)."""
        return [{"id": d.id, "schicht": d.schicht, "titel": d.titel} for d in store.liste(schicht)]

    @server.tool()
    def brain_add_raw(titel: str, inhalt: str, tags: list[str] | None = None) -> dict[str, Any]:
        """Rohquelle ins Gehirn legen (append-only). Reindiziert danach."""
        d = store.add_raw(titel, inhalt, tags)
        _reindex()
        return {"id": d.id, "titel": d.titel}

    return server


def main() -> int:
    build_server().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
