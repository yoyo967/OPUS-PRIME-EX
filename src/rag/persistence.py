"""Serialize a chunk corpus to/from a JSONL snapshot.

The snapshot is the immutable, reproducible corpus artifact (KNOWLEDGE_ARCHITECTURE
§3). It lives under korpus/ (gitignored, reproducible via scripts/ingest.py).

# SPEC: KNOWLEDGE_ARCHITECTURE.md §3 (unveraenderliche Snapshot-Objekte)
"""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from src.rag.chunker import Chunk


def chunk_to_dict(chunk: Chunk) -> dict[str, object]:
    return asdict(chunk)


def chunk_from_dict(data: dict[str, object]) -> Chunk:
    """Reconstruct a Chunk; JSON lists are coerced back to the tuple fields."""
    felder = dict(data)
    felder["domaene"] = tuple(felder.get("domaene", []))  # type: ignore[arg-type]
    felder["verweist_auf"] = tuple(felder.get("verweist_auf", []))  # type: ignore[arg-type]
    return Chunk(**felder)  # type: ignore[arg-type]


def save_corpus(chunks: list[Chunk], path: Path) -> None:
    """Write one JSON object per line."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            handle.write(json.dumps(chunk_to_dict(chunk), ensure_ascii=False))
            handle.write("\n")


def load_corpus(path: Path) -> list[Chunk]:
    """Read a JSONL snapshot back into chunks."""
    chunks: list[Chunk] = []
    with path.open(encoding="utf-8") as handle:
        for zeile in handle:
            zeile = zeile.strip()
            if zeile:
                chunks.append(chunk_from_dict(json.loads(zeile)))
    return chunks
