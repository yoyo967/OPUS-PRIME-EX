"""Ingest orchestration: chunk -> Verweisgraph -> persist -> coverage report.

The pipeline is real and tested against the fixtures. The one boundary that needs a
production adapter is FETCH+NORMALIZE: turning live gesetze-im-internet.de / EUR-Lex
XML into the normalized format the chunker consumes. Until those source adapters
exist, ingest runs over the checked-in normalized fixtures listed in the manifest.

# SPEC: CLAUDE.md §2 (scripts/ingest.py); KNOWLEDGE_ARCHITECTURE.md §3 (Snapshots),
# §5 (Verweisgraph beim Ingest), §7 (Coverage-Matrix je Domaene)
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from src.rag.chunker import Chunk, chunk_de_gesetz, chunk_eu_verordnung
from src.rag.persistence import save_corpus
from src.rag.verweisgraph import extrahiere_verweise
from src.shared.exceptions import ToolInputError

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_MANIFEST = _REPO_ROOT / "data" / "fixtures" / "ingest_manifest.yaml"
_DEFAULT_QUELLE = _REPO_ROOT / "data" / "fixtures"
_DEFAULT_OUT = _REPO_ROOT / "korpus" / "snapshot.jsonl"
_COVERAGE_MATRIX = _REPO_ROOT / "review" / "coverage_matrix.yaml"

# CELEX -> in der Coverage-Matrix / Normzitaten verwendete Kurzbezeichnungen.
_CELEX_ALIAS = {
    "32016R0679": ("DSGVO", "2016/679"),
    "32017R1001": ("UMV", "2017/1001"),
    "32024R1689": ("2024/1689", "AI Act"),
    "32023R2854": ("2023/2854", "Data Act"),
}
_NUM = re.compile(r"\d+[a-z]?")


@dataclass(frozen=True)
class IngestResult:
    anzahl_chunks: int
    anzahl_verweis_kanten: int
    snapshot_pfad: str


@dataclass(frozen=True)
class DomaeneCoverage:
    domaene: str
    indexed: int
    gesamt: int
    fehlende: tuple[str, ...] = field(default_factory=tuple)


def _chunks_aus_manifest(manifest_path: Path, quelle_dir: Path) -> list[Chunk]:
    manifest: dict[str, Any] = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    chunks: list[Chunk] = []
    for eintrag in manifest["dokumente"]:
        pfad = quelle_dir / str(eintrag["datei"])
        xml = pfad.read_text(encoding="utf-8")
        domaene = tuple(eintrag["domaene"])
        if eintrag["typ"] == "de_gesetz":
            chunks += chunk_de_gesetz(
                xml,
                gesetz=str(eintrag["gesetz"]),
                gueltig_ab=str(eintrag["gueltig_ab"]),
                rechtsstand_abruf=str(eintrag["rechtsstand_abruf"]),
                quelle_url=str(eintrag["quelle_url"]),
                domaene=domaene,
            )
        elif eintrag["typ"] == "eu_verordnung":
            chunks += chunk_eu_verordnung(
                xml,
                celex=str(eintrag["celex"]),
                gueltig_ab=str(eintrag["gueltig_ab"]),
                rechtsstand_abruf=str(eintrag["rechtsstand_abruf"]),
                quelle_url=str(eintrag["quelle_url"]),
                domaene=domaene,
            )
        else:
            raise ToolInputError(f"Unbekannter Manifest-Typ: {eintrag['typ']!r}")
    return chunks


def run_ingest(
    manifest_path: Path = _DEFAULT_MANIFEST,
    quelle_dir: Path = _DEFAULT_QUELLE,
    out_path: Path = _DEFAULT_OUT,
) -> tuple[IngestResult, list[Chunk]]:
    """Chunk the manifest, build the Verweisgraph, persist a snapshot."""
    chunks = _chunks_aus_manifest(manifest_path, quelle_dir)
    chunks = extrahiere_verweise(chunks)
    save_corpus(chunks, out_path)
    kanten = sum(len(c.verweist_auf) for c in chunks)
    return IngestResult(len(chunks), kanten, str(out_path)), chunks


def _norm_indexed(norm: str, chunks: list[Chunk]) -> bool:
    """Best-effort match of a Muss-Norm string against the indexed corpus."""
    norm_tokens = set(_NUM.findall(norm))
    for chunk in chunks:
        nummer_match = _NUM.search(chunk.einheit)
        if nummer_match is None:
            continue
        nummer = nummer_match.group(0)
        if nummer not in norm_tokens:
            continue
        if chunk.gesetz and chunk.gesetz in norm:
            return True
        if chunk.celex and any(alias in norm for alias in _CELEX_ALIAS.get(chunk.celex, ())):
            return True
    return False


def coverage_report(
    chunks: list[Chunk], matrix_path: Path = _COVERAGE_MATRIX
) -> list[DomaeneCoverage]:
    """Compare the indexed corpus against the Muss-Normen matrix per domain.

    # SPEC: KNOWLEDGE_ARCHITECTURE.md §7 (Coverage-Matrix; CI-Gate nach Live-Ingest)
    """
    matrix: dict[str, Any] = yaml.safe_load(matrix_path.read_text(encoding="utf-8"))
    berichte: list[DomaeneCoverage] = []
    for domaene, block in matrix.get("domaenen", {}).items():
        muss = [str(n["norm"]) for n in block.get("muss_normen", [])]
        fehlende = tuple(n for n in muss if not _norm_indexed(n, chunks))
        berichte.append(
            DomaeneCoverage(domaene, len(muss) - len(fehlende), len(muss), fehlende)
        )
    return berichte


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OPUS PRIME EX Korpus-Ingest")
    parser.add_argument("--manifest", type=Path, default=_DEFAULT_MANIFEST)
    parser.add_argument("--quelle", type=Path, default=_DEFAULT_QUELLE)
    parser.add_argument("--out", type=Path, default=_DEFAULT_OUT)
    parser.add_argument("--coverage", action="store_true", help="Coverage-Report ausgeben")
    args = parser.parse_args(argv)

    result, chunks = run_ingest(args.manifest, args.quelle, args.out)
    print(
        f"[ingest] {result.anzahl_chunks} Chunks, {result.anzahl_verweis_kanten} "
        f"Verweis-Kanten -> {result.snapshot_pfad}"
    )
    if args.coverage:
        gesamt_idx = 0
        gesamt = 0
        for bericht in coverage_report(chunks):
            gesamt_idx += bericht.indexed
            gesamt += bericht.gesamt
            print(f"[coverage] {bericht.domaene}: {bericht.indexed}/{bericht.gesamt} indexed")
        print(
            f"[coverage] GESAMT {gesamt_idx}/{gesamt} - Rest pending_ingest "
            f"(Live-Korpus-Fetch ausstehend; siehe src/rag/ingest.py Doc)"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
