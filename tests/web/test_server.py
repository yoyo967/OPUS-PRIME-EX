"""Tests fuer die Web-UI-Kernlogik (verarbeite_frage), ohne HTTP-Server.

# SPEC: AGENT_ARCHITECTURE.md §8 A2 (Referenz-Web-UI)
"""

from __future__ import annotations

from collections.abc import Sequence

import pytest

from apps.web.server import _fehlertext, _resolve_bind, verarbeite_frage
from src.rag.chunker import Chunk
from src.rag.store import InMemoryVectorStore


def _store() -> InMemoryVectorStore:
    chunk = Chunk(
        chunk_id="de-ustg-2025-01-01-p19", quelle_typ="gesetz", jurisdiktion="DE",
        gesetz="UStG", celex=None, einheit="§ 19",
        ueberschrift="Besteuerung der Kleinunternehmer", gueltig_ab="2025-01-01",
        gueltig_bis=None, rechtsstand_abruf="2026-07-05",
        quelle_url="https://www.gesetze-im-internet.de/ustg/__19.html",
        text="Steuer Kalenderjahr Euro Kleinunternehmer 25 000 100 000.",
        hash="sha256:x", typ="norm", domaene=("steuerrecht",),
    )
    return InMemoryVectorStore([chunk])


class _FakeLLM:
    def generate(
        self, route: object, anfrage: str, chunks: Sequence[Chunk],
        korrektur_hinweis: str | None,
    ) -> str:
        return "Nach § 19 UStG gilt die Kleinunternehmerregelung."


class TestVerarbeiteFrage:
    def test_mit_llm_liefert_antwort_und_pipeline(self) -> None:
        out = verarbeite_frage(
            "Muss ich als Kleinunternehmer Umsatzsteuer im Kalenderjahr ausweisen?",
            _store(), _FakeLLM(),
        )
        assert "steuerrecht" in out["domaenen"]
        assert out["route"] == "A_STANDARD"
        assert "Sonnet" in out["modell"]
        assert out["antwort"] and "§ 19 UStG" in out["antwort"]
        assert out["fehler"] is None
        # G1-Disclaimer serverseitig angehaengt
        assert any(g.startswith("G1:") for g in out["guardrails"])

    def test_ohne_llm_zeigt_pipeline_und_hinweis(self) -> None:
        out = verarbeite_frage(
            "Muss ich als Kleinunternehmer Steuer im Kalenderjahr zahlen (Euro)?",
            _store(), None,
        )
        assert out["antwort"] is None
        assert "Kein API-Key" in out["fehler"]
        # Retrieval laeuft trotzdem -> Quelle sichtbar
        assert "de-ustg-2025-01-01-p19" in out["quellen"]

    def test_g2_scope_frage_wird_abgefangen(self) -> None:
        out = verarbeite_frage("Reiche meine Umsatzsteuer-Voranmeldung ein.", _store(), _FakeLLM())
        assert any(g.startswith("G2:") for g in out["guardrails"])


class TestFehlertext:
    def test_guthaben(self) -> None:
        assert "Guthaben" in _fehlertext(Exception("Your credit balance is too low"))

    def test_auth(self) -> None:
        assert "ungueltig" in _fehlertext(Exception("authentication_error: invalid x-api-key"))

    def test_generisch(self) -> None:
        assert "nicht moeglich" in _fehlertext(RuntimeError("boom"))


class TestResolveBind:
    """Bind: lokal 127.0.0.1 (DSGVO/Least-Privilege), Cloud Run (PORT gesetzt) 0.0.0.0:$PORT."""

    def test_lokal_ohne_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("PORT", raising=False)
        monkeypatch.delenv("HOST", raising=False)
        assert _resolve_bind() == ("127.0.0.1", 8848)

    def test_cloud_run_port_bindet_alle_interfaces(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PORT", "8080")
        monkeypatch.delenv("HOST", raising=False)
        assert _resolve_bind() == ("0.0.0.0", 8080)

    def test_host_override_gewinnt(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PORT", "8080")
        monkeypatch.setenv("HOST", "127.0.0.1")
        assert _resolve_bind() == ("127.0.0.1", 8080)
