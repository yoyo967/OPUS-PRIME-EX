"""Launcher fuer den Second-Brain-MCP-Server (stdio).

Nutzung:  python scripts/brain_serve.py    (braucht das Extra: pip install ".[mcp]")
Exponiert das geteilte Gehirn (brain_search/read/list/add_raw) fuer beliebige MCP-Clients.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.brain.server import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
