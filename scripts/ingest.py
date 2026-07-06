"""CLI launcher for the corpus ingest: `python scripts/ingest.py [--coverage]`.

# SPEC: CLAUDE.md §2 (scripts/ingest.py)
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.rag.ingest import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
