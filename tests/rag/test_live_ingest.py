"""Live-Ingest-Tests mit injiziertem Fetch (kein Netz).

# SPEC: KNOWLEDGE_ARCHITECTURE.md §2 Prio 1 (Live-Quellen), §5 (Verweisgraph)
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

import yaml

from src.rag.ingest import run_live_ingest
from src.rag.persistence import load_corpus

_GII_SAMPLE = (
    Path(__file__).resolve().parent.parent.parent
    / "data" / "fixtures" / "raw" / "gii_ustg_sample.xml"
)


def _zip_for(_slug: str) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("law.xml", _GII_SAMPLE.read_text(encoding="utf-8"))
    return buf.getvalue()


def _mini_config(tmp_path: Path, slugs: list[str]) -> Path:
    cfg = {
        "gii_gesetze": [
            {
                "slug": s, "gesetz": "UStG", "gueltig_ab": "2025-01-01",
                "domaene": ["steuerrecht"],
                "quelle_url": f"https://www.gesetze-im-internet.de/{s}/",
            }
            for s in slugs
        ]
    }
    pfad = tmp_path / "quellen.yaml"
    pfad.write_text(yaml.safe_dump(cfg), encoding="utf-8")
    return pfad


class TestRunLiveIngest:
    def test_fetch_wird_injiziert_und_chunks_persistiert(self, tmp_path: Path) -> None:
        out = tmp_path / "snap.jsonl"
        result, chunks, fehler = run_live_ingest(
            quellen_path=_mini_config(tmp_path, ["ustg_1980"]),
            out_path=out,
            fetch=_zip_for,
        )
        assert fehler == []
        assert result.anzahl_chunks == 2  # § 19 + § 19a aus dem Sample
        assert {c.einheit for c in chunks} == {"§ 19", "§ 19a"}
        assert load_corpus(out) == chunks

    def test_fehlende_quelle_stoppt_lauf_nicht(self, tmp_path: Path) -> None:
        def _fetch(slug: str) -> bytes:
            if slug == "kaputt":
                raise RuntimeError("HTTP 404")
            return _zip_for(slug)

        _result, chunks, fehler = run_live_ingest(
            quellen_path=_mini_config(tmp_path, ["ustg_1980", "kaputt"]),
            out_path=tmp_path / "snap.jsonl",
            fetch=_fetch,
        )
        assert chunks  # die gute Quelle ist trotzdem ingestiert
        assert len(fehler) == 1 and fehler[0][0] == "kaputt"


class TestBmfIngest:
    def _cfg(self, tmp_path: Path) -> Path:
        cfg = {
            "bmf_schreiben": [
                {
                    "kuerzel": "GoBD", "titel": "GoBD (Test)",
                    "gueltig_ab": "2019-11-28", "domaene": ["finanzen"],
                    "url": "https://bmf.example/gobd.pdf",
                }
            ]
        }
        pfad = tmp_path / "quellen.yaml"
        pfad.write_text(yaml.safe_dump(cfg), encoding="utf-8")
        return pfad

    def test_bmf_schreiben_wird_ingestiert(self, tmp_path: Path) -> None:
        _result, chunks, fehler = run_live_ingest(
            quellen_path=self._cfg(tmp_path), out_path=tmp_path / "s.jsonl",
            fetch_bmf_text=lambda _url: "Rz. 1 Erste Regel.\nRz. 2 Zweite Regel.",
        )
        assert fehler == []
        assert chunks and all(c.quelle_typ == "bmf" for c in chunks)
        assert chunks[0].gesetz == "GoBD"

    def test_bmf_fehlschlag_tolerant(self, tmp_path: Path) -> None:
        def _boom(_url: str) -> str:
            raise RuntimeError("HTTP 404")

        _result, chunks, fehler = run_live_ingest(
            quellen_path=self._cfg(tmp_path), out_path=tmp_path / "s.jsonl",
            fetch_bmf_text=_boom,
        )
        assert chunks == [] and len(fehler) == 1 and fehler[0][0] == "GoBD"
