"""OPUS PRIME EX als MCP-Server (optionales Extra [mcp]).

Exponiert geteilte Faehigkeiten fuer beliebige MCP-Clients (Claude Code, OPUS DECK,
weitere Agenten) ueber den offiziellen MCP-Standard (stdio-Transport). Das SDK wird
lazy importiert; nur das Ausfuehren des Servers braucht `pip install ".[mcp]"`.

Start:  python scripts/mcp_serve.py   (oder Konsolen-Skript opus-prime-ex-mcp)

# SPEC/ADR: opus-deck ADR-0002 (ACP/MCP-Rueckgrat), ADR-0005 (Second Brain als MCP-Server)
"""

from __future__ import annotations

from typing import Any

from src.mcp_server.tools import suche_rechtsquellen
from src.rag.store import InMemoryVectorStore


def _build_store() -> InMemoryVectorStore:
    # Bevorzugt den Live-Snapshot (echte Gesetze), sonst Fixtures — wie die Web-UI.
    from apps.web.server import build_store

    return build_store()


def build_server(store: InMemoryVectorStore | None = None) -> Any:
    """Construct the FastMCP server with the shared tools registered.

    Requires the optional 'mcp' extra. Returns a FastMCP instance (Any, damit das
    Modul ohne das SDK importiert/typgeprueft werden kann).
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:  # optionales Extra [mcp]
        raise RuntimeError(
            'Der MCP-Server benoetigt das Extra "mcp" (pip install ".[mcp]").'
        ) from exc

    server = FastMCP("opus-prime-ex")
    aktiver_store = store if store is not None else _build_store()

    @server.tool()
    def ping() -> str:
        """Health check des OPUS-PRIME-EX-MCP-Servers."""
        return "opus-prime-ex mcp ok"

    @server.tool()
    def rechtsquellen_suche(query: str, k: int = 5) -> list[dict[str, Any]]:
        """Suche relevante deutsche/EU-Rechtsquellen (Gesetze/EU-Verordnungen) zur Anfrage."""
        return suche_rechtsquellen(query, aktiver_store, k)

    return server


def main() -> int:
    """Run the MCP server over stdio."""
    build_server().run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
