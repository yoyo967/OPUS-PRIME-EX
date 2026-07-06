"""Populate the Verweisgraph (verweist_auf edges) across a chunk corpus.

The chunker leaves verweist_auf empty; this ingest step scans each chunk's text
for norm references (§ …, Artikel …) and adds an edge when the referenced norm is
present in the same statute/regulation. Only intra-corpus edges are created — a
reference to a norm not yet ingested produces no dangling edge.

# SPEC: KNOWLEDGE_ARCHITECTURE.md §5 (Verweisgraph: Normverweise per Regex in eine
# Kanten-Tabelle, speist Struktur-Expansion §4.3)
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import replace

from src.rag.chunker import Chunk

_DE_REF = re.compile(r"§\s*(\d+[a-z]?)")
_EU_REF = re.compile(r"Art(?:ikel|\.)\s*(\d+[a-z]?)")


def _basis_einheit(einheit: str) -> str:
    """'§ 19 Abs. 1' -> '§ 19'; 'Art. 46' -> 'Art. 46'."""
    return einheit.split(" Abs.")[0]


def extrahiere_verweise(chunks: Sequence[Chunk]) -> list[Chunk]:
    """Return the chunks with verweist_auf populated from intra-corpus references."""
    # (scope, basis-einheit) -> chunk_id; base-§ chunk wins over its Absatz-splits.
    index: dict[tuple[str, str], str] = {}
    for chunk in chunks:
        scope = chunk.gesetz or chunk.celex or ""
        basis = _basis_einheit(chunk.einheit)
        key = (scope, basis)
        if key not in index or chunk.einheit == basis:
            index[key] = chunk.chunk_id

    ergebnis: list[Chunk] = []
    for chunk in chunks:
        scope = chunk.gesetz or chunk.celex or ""
        ziele: set[str] = set()
        muster = _DE_REF if chunk.gesetz else _EU_REF
        praefix = "§ " if chunk.gesetz else "Art. "
        for match in muster.finditer(chunk.text):
            ziel = index.get((scope, f"{praefix}{match.group(1)}"))
            if ziel is not None and ziel != chunk.chunk_id:
                ziele.add(ziel)
        ergebnis.append(replace(chunk, verweist_auf=tuple(sorted(ziele))))
    return ergebnis
