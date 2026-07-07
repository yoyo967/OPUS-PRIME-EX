"""Launcher fuer den OPUS-PRIME-EX-MCP-Server (stdio).

Nutzung:  python scripts/mcp_serve.py    (braucht das Extra: pip install ".[mcp]")
Der Server exponiert geteilte Faehigkeiten (u. a. rechtsquellen_suche) fuer beliebige
MCP-Clients (Claude Code, OPUS DECK, weitere Agenten).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.mcp_server.server import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
