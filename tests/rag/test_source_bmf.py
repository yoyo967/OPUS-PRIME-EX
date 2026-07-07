"""BMF-Schreiben adapter tests: extracted text -> Randnummer-Chunks (offline).

# SPEC: KNOWLEDGE_ARCHITECTURE.md §5 (BMF: Chunking nach Randnummern, 300-800
# Tokens, 15 % Overlap), §6 (quelle_typ 'bmf'; Zitierkopf aus gesetz-Feld)
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from src.rag.sources.bmf import (
    MAX_TOKENS,
    chunks_from_bmf,
    segmente_nach_randnummer,
)
from src.shared.exceptions import ToolInputError

_SAMPLE = (
    Path(__file__).resolve().parent.parent.parent
    / "data" / "fixtures" / "raw" / "bmf_gobd_sample.txt"
)


def _raw() -> str:
    return _SAMPLE.read_text(encoding="utf-8")


def _chunks() -> list:
    return chunks_from_bmf(
        _raw(), quelle_kuerzel="GoBD", titel="GoBD (Muster)",
        gueltig_ab="2019-11-28", rechtsstand_abruf="2026-07-07",
        quelle_url="https://www.bundesfinanzministerium.de/gobd", domaene=("finanzen",),
    )


class TestSegmentierung:
    def test_segmente_nach_randnummer(self) -> None:
        segmente = segmente_nach_randnummer(_raw())
        # Praeambel vor Rz. 1 wird verworfen; 6 Randnummern erkannt
        assert [nr for nr, _ in segmente] == ["1", "2", "3", "4", "5", "6"]
        assert "Buchfuehrung" in segmente[0][1]

    def test_ohne_randnummer_ein_segment(self) -> None:
        segmente = segmente_nach_randnummer("Fliesstext ohne jede Randnummer.")
        assert len(segmente) == 1 and segmente[0][0] == ""

    def test_leerer_text_keine_segmente(self) -> None:
        assert segmente_nach_randnummer("   \n  ") == []


class TestChunking:
    def test_bmf_metadaten_und_quelle_typ(self) -> None:
        chunks = _chunks()
        assert chunks, "mindestens ein Chunk"
        c = chunks[0]
        assert c.quelle_typ == "bmf"
        assert c.typ == "verwaltungsanweisung"
        assert c.gesetz == "GoBD"  # Zitierkopf-Basis
        assert c.celex is None
        assert c.jurisdiktion == "DE"
        assert c.einheit.startswith("Rz. ")

    def test_zitierkopf_ohne_celex_none(self) -> None:
        # Regression: gesetz-Feld traegt das BMF-Kuerzel -> kein "CELEX None"
        kopf = _chunks()[0].zitierkopf()
        assert "GoBD" in kopf and "CELEX None" not in kopf

    def test_chunks_halten_token_obergrenze(self) -> None:
        from src.rag.chunker import estimate_tokens
        for c in _chunks():
            assert estimate_tokens(c.text) <= MAX_TOKENS + 200  # +Overlap-Toleranz

    def test_randnummern_bleiben_im_text(self) -> None:
        # Die Rz.-Nummern muessen im Chunk-Text erhalten bleiben (Zitierbarkeit)
        text = "\n".join(c.text for c in _chunks())
        assert "Rz. 1" in text and "Rz. 6" in text

    def test_grosser_text_mehrere_chunks_mit_overlap(self) -> None:
        # 20 Randnummern a ~60 Woerter -> ueber MAX_TOKENS -> mehrere Chunks
        text = "\n".join(f"Rz. {i} " + "Wort " * 60 for i in range(1, 21))
        chunks = chunks_from_bmf(
            text, quelle_kuerzel="UStAE", titel="UStAE (Muster)",
            gueltig_ab="2024-01-01", rechtsstand_abruf="2026-07-07",
            quelle_url="https://x", domaene=("steuerrecht",),
        )
        assert len(chunks) >= 2

        def rz_set(c: object) -> set[str]:
            return set(re.findall(r"Rz\. (\d+)", c.text))  # type: ignore[attr-defined]

        # 15 % Overlap: benachbarte Chunks teilen mindestens eine Randnummer
        assert rz_set(chunks[0]) & rz_set(chunks[1])
        # Fortschritt: jeder Chunk bringt neue Randnummern (keine Endlosschleife)
        assert rz_set(chunks[1]) - rz_set(chunks[0])

    def test_leerer_input_fehler(self) -> None:
        with pytest.raises(ToolInputError, match="keinen Inhalt"):
            chunks_from_bmf(
                "   ", quelle_kuerzel="GoBD", titel="x", gueltig_ab="2019-01-01",
                rechtsstand_abruf="2026-07-07", quelle_url="https://x",
                domaene=("finanzen",),
            )
