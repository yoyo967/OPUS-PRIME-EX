"""Second Brain B0/B1 Tests: Store (Markdown+Frontmatter, append-only) + Retrieval.

# SPEC: opus-deck/spec/SECOND_BRAIN.md §2/§4
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.brain.retrieval import brain_search, build_brain_index
from src.brain.store import BrainStore
from src.shared.exceptions import ToolInputError


class TestBrainStore:
    def test_add_raw_und_read(self, tmp_path: Path) -> None:
        store = BrainStore(tmp_path)
        doc = store.add_raw(
            "Kleinunternehmer Notiz", "Grenze 25.000 Euro Vorjahr.", tags=["steuer"]
        )
        assert doc.schicht == "raw" and doc.id.startswith("raw/")
        wieder = store.read(doc.id)
        assert wieder.titel == "Kleinunternehmer Notiz"
        assert "25.000 Euro" in wieder.text
        assert wieder.meta.get("tags") == ["steuer"]

    def test_append_only_ueberschreibt_nicht(self, tmp_path: Path) -> None:
        store = BrainStore(tmp_path)
        a = store.add_raw("Selbe Notiz", "Inhalt A")
        b = store.add_raw("Selbe Notiz", "Inhalt B")
        assert a.id != b.id  # zweite Datei mit Suffix, nichts ueberschrieben
        assert len(store.liste("raw")) == 2

    def test_list_trennt_schichten(self, tmp_path: Path) -> None:
        store = BrainStore(tmp_path)
        store.add_raw("N", "x")
        assert len(store.liste("raw")) == 1
        assert store.liste("wiki") == []

    def test_leerer_inhalt_fehler(self, tmp_path: Path) -> None:
        with pytest.raises(ToolInputError, match="Leerer Inhalt"):
            BrainStore(tmp_path).add_raw("t", "   ")

    def test_unbekanntes_dokument_fehler(self, tmp_path: Path) -> None:
        with pytest.raises(ToolInputError, match="nicht gefunden"):
            BrainStore(tmp_path).read("raw/gibt-es-nicht.md")


class TestWikiReview:
    def test_propose_schreibt_nicht_ins_wiki(self, tmp_path: Path) -> None:
        store = BrainStore(tmp_path)
        p = store.propose_wiki("Kleinunternehmer", "# Kleinunternehmer\nGrenze 25.000 Euro.")
        assert p.id and p.ziel == "wiki/kleinunternehmer.md"
        assert store.liste("wiki") == []  # Wiki bleibt unveraendert (nur Vorschlag)
        assert len(store.list_proposals()) == 1

    def test_read_proposal_hat_diff(self, tmp_path: Path) -> None:
        store = BrainStore(tmp_path)
        pid = store.propose_wiki("Thema", "Neue Zeile").id
        p = store.read_proposal(pid)
        assert "Neue Zeile" in p.inhalt
        assert "+Neue Zeile" in p.diff  # unified diff gegen leere aktuelle Seite

    def test_approve_uebernimmt_ins_wiki(self, tmp_path: Path) -> None:
        store = BrainStore(tmp_path)
        pid = store.propose_wiki("Kleinunternehmer", "Grenze 25.000 Euro.", quellen=["raw/x.md"]).id
        doc = store.approve_proposal(pid)
        assert doc.schicht == "wiki" and doc.id == "wiki/kleinunternehmer.md"
        assert "25.000 Euro" in store.read(doc.id).text
        assert store.read(doc.id).meta.get("quellen") == ["raw/x.md"]
        assert store.list_proposals() == []  # Vorschlag nach Freigabe entfernt

    def test_reject_verwirft(self, tmp_path: Path) -> None:
        store = BrainStore(tmp_path)
        pid = store.propose_wiki("T", "x").id
        store.reject_proposal(pid)
        assert store.list_proposals() == [] and store.liste("wiki") == []

    def test_leerer_vorschlag_fehler(self, tmp_path: Path) -> None:
        with pytest.raises(ToolInputError, match="Leerer Wiki-Vorschlag"):
            BrainStore(tmp_path).propose_wiki("t", "   ")

    def test_approvte_seite_ist_durchsuchbar(self, tmp_path: Path) -> None:
        store = BrainStore(tmp_path)
        store.approve_proposal(store.propose_wiki("Kleinunternehmer", "Umsatzsteuer Grenze").id)
        index = build_brain_index(store.alle())
        treffer = brain_search(index, "Kleinunternehmer Umsatzsteuer", k=3)
        assert treffer and treffer[0]["schicht"] == "wiki"


class TestBrainRetrieval:
    def test_search_findet_relevantes_dokument(self, tmp_path: Path) -> None:
        store = BrainStore(tmp_path)
        store.add_raw("Kleinunternehmer", "Umsatzsteuer Grenze fuer Kleinunternehmer.")
        store.add_raw("Urlaub", "Notizen zur Reiseplanung nach Italien.")
        index = build_brain_index(store.alle())
        treffer = brain_search(index, "Kleinunternehmer Umsatzsteuer", k=5)
        assert treffer, "mindestens ein Treffer"
        top = treffer[0]
        assert set(top) >= {"id", "titel", "schicht", "auszug", "score"}
        assert "Kleinunternehmer" in top["titel"]
        assert top["schicht"] == "raw"

    def test_search_k_begrenzt(self, tmp_path: Path) -> None:
        store = BrainStore(tmp_path)
        store.add_raw("A", "gemeinsames wort alpha")
        store.add_raw("B", "gemeinsames wort beta")
        index = build_brain_index(store.alle())
        assert len(brain_search(index, "gemeinsames wort", k=1)) <= 1
