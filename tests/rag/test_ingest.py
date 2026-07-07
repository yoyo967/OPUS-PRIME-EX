"""Ingest-pipeline tests: chunking, Verweisgraph, persistence, coverage.

# SPEC: KNOWLEDGE_ARCHITECTURE.md §3/§5/§7; CLAUDE.md §4.2
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from src.rag.chunker import Chunk
from src.rag.ingest import coverage_report, run_ingest
from src.rag.persistence import chunk_from_dict, chunk_to_dict, load_corpus, save_corpus
from src.rag.verweisgraph import extrahiere_verweise


def _norm(einheit: str, chunk_id: str, text: str) -> Chunk:
    return Chunk(
        chunk_id=chunk_id, quelle_typ="gesetz", jurisdiktion="DE", gesetz="UStG",
        celex=None, einheit=einheit, ueberschrift="Test", gueltig_ab="2025-01-01",
        gueltig_bis=None, rechtsstand_abruf="2026-07-05", quelle_url="https://x",
        text=text, hash="sha256:x", typ="norm", domaene=("steuerrecht",),
    )


class TestVerweisgraph:
    def test_intra_korpus_verweis_wird_kante(self) -> None:
        p19 = _norm("§ 19", "p19", "Naeheres regelt § 19a entsprechend.")
        p19a = _norm("§ 19a", "p19a", "EU-Regelung.")
        graph = extrahiere_verweise([p19, p19a])
        by_id = {c.chunk_id: c for c in graph}
        assert by_id["p19"].verweist_auf == ("p19a",)
        assert by_id["p19a"].verweist_auf == ()

    def test_verweis_auf_nicht_ingestierte_norm_erzeugt_keine_kante(self) -> None:
        p42 = _norm("§ 42", "p42", "gemaess § 41 Absatz 2")  # § 41 nicht im Korpus
        graph = extrahiere_verweise([p42])
        assert graph[0].verweist_auf == ()

    def test_kein_selbstverweis(self) -> None:
        p19 = _norm("§ 19", "p19", "siehe § 19 oben")
        graph = extrahiere_verweise([p19])
        assert graph[0].verweist_auf == ()


class TestPersistence:
    def test_roundtrip_erhaelt_alle_felder(self) -> None:
        chunk = replace(_norm("§ 19", "p19", "Text"), verweist_auf=("p19a",))
        wieder = chunk_from_dict(chunk_to_dict(chunk))
        assert wieder == chunk
        assert isinstance(wieder.domaene, tuple)
        assert isinstance(wieder.verweist_auf, tuple)

    def test_save_load_jsonl(self, tmp_path: Path) -> None:
        chunks = [_norm("§ 19", "p19", "A"), _norm("§ 19a", "p19a", "B")]
        pfad = tmp_path / "sub" / "snapshot.jsonl"
        save_corpus(chunks, pfad)
        assert load_corpus(pfad) == chunks


class TestRunIngest:
    def test_ingest_erzeugt_snapshot_und_chunks(self, tmp_path: Path) -> None:
        out = tmp_path / "snapshot.jsonl"
        result, chunks = run_ingest(out_path=out)
        # 6 Fixtures: UStG(§19,§19a)=2, MarkenG(§42)=1, AI-Act(2 recital+Art6+2 Anhang)=5,
        # DSGVO(Art28)=1, Data-Act(Art5)=1, UMV(Art46)=1 -> 11
        assert result.anzahl_chunks == 11
        assert len(chunks) == 11
        assert out.exists()
        assert load_corpus(out) == chunks

    def test_snapshot_ist_reproduzierbar(self, tmp_path: Path) -> None:
        r1, _ = run_ingest(out_path=tmp_path / "a.jsonl")
        r2, _ = run_ingest(out_path=tmp_path / "b.jsonl")
        assert (tmp_path / "a.jsonl").read_text(encoding="utf-8") == (
            tmp_path / "b.jsonl"
        ).read_text(encoding="utf-8")
        assert r1.anzahl_chunks == r2.anzahl_chunks


class TestCoverage:
    def test_report_markiert_indexierte_muss_normen(self, tmp_path: Path) -> None:
        _, chunks = run_ingest(out_path=tmp_path / "s.jsonl")
        berichte = {b.domaene: b for b in coverage_report(chunks)}
        # § 19 UStG ist ingestiert -> im steuerrecht-Bericht als indexed
        steuer = berichte["steuerrecht"]
        assert steuer.indexed >= 1
        assert "§ 19 UStG" not in steuer.fehlende
        # markenrecht: § 42 MarkenG ist ingestiert
        marken = berichte["markenrecht"]
        assert marken.indexed >= 1
        # Der Grossteil bleibt pending (nur 6 Fixtures) - ehrlich abgebildet
        assert steuer.gesamt > steuer.indexed

    def test_ganzgesetz_verweis_ohne_paragraf_zaehlt(self) -> None:
        # "UmwG (Grundzuege Verschmelzung)" nennt keine konkrete Einheit ->
        # muss zaehlen, sobald irgendein UmwG-Chunk vorliegt (Coverage-Matcher-Fix).
        umwg = replace(_norm("§ 1", "umwg1", "Verschmelzung."), gesetz="UmwG",
                       domaene=("gewerberecht",))
        berichte = {b.domaene: b for b in coverage_report([umwg])}
        gew = berichte["gewerberecht"]
        assert not any("UmwG" in f for f in gew.fehlende)
        # Kein False-Positive: ein nicht vorhandener Ganzverweis bleibt offen.
        finanzen = berichte["finanzen"]
        assert any("GoBD" in f for f in finanzen.fehlende)

    def test_alle_domaenen_im_report(self, tmp_path: Path) -> None:
        _, chunks = run_ingest(out_path=tmp_path / "s.jsonl")
        domaenen = {b.domaene for b in coverage_report(chunks)}
        assert domaenen == {
            "steuerrecht", "gewerberecht", "finanzen",
            "dsgvo", "eu_ai_act", "data_act", "markenrecht",
        }
