"""Runnable end-to-end demo: eine echte Frage durch die volle Pipeline.

Laedt den Fixture-Korpus (BM25-Retrieval), verdrahtet den ECHTEN Anthropic-Client
und laesst eine Frage durch Router -> Retrieval -> Modell -> Guardrails laufen.

Voraussetzung: ANTHROPIC_API_KEY in .env (oder Umgebung). Solange kein Live-Korpus
ingestiert ist, retrievt die Demo BM25-only ueber die eingecheckten Fixtures.

Nutzung:
    python scripts/demo.py "Muss ich als Kleinunternehmer Umsatzsteuer ausweisen?"

# SPEC: AGENT_ARCHITECTURE.md §1 (Systemueberblick, End-to-End-Pfad)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

_DEFAULT_FRAGE = "Muss ich als Kleinunternehmer Umsatzsteuer ausweisen?"


def _load_env(pfad: Path) -> None:
    """Minimaler .env-Loader (keine Zusatz-Dependency)."""
    if not pfad.exists():
        return
    for zeile in pfad.read_text(encoding="utf-8").splitlines():
        zeile = zeile.strip()
        if not zeile or zeile.startswith("#") or "=" not in zeile:
            continue
        schluessel, wert = (t.strip() for t in zeile.split("=", 1))
        if schluessel and wert and schluessel not in os.environ:
            os.environ[schluessel] = wert


def main(argv: list[str] | None = None) -> int:
    from src.gateway.llm_client import build_default_client
    from src.orchestrator.orchestrator import run
    from src.rag.ingest import run_ingest
    from src.rag.retrieval import build_rag_suche
    from src.rag.store import InMemoryVectorStore
    from src.router.classifier import classify

    args = sys.argv[1:] if argv is None else argv
    frage = args[0] if args else _DEFAULT_FRAGE

    _load_env(_REPO_ROOT / ".env")
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "[demo] Kein ANTHROPIC_API_KEY gefunden. Trage ihn in .env ein "
            "(siehe .env im Projektordner) und starte erneut.",
            file=sys.stderr,
        )
        return 2

    # Korpus aus dem Manifest (BM25-only bis Live-Korpus + Embedding-Modell da sind).
    _, chunks = run_ingest()
    store = InMemoryVectorStore(chunks)
    rag_suche = build_rag_suche(store)

    klassifikation = classify(frage)
    llm = build_default_client()
    antwort = run(frage, klassifikation, llm, rag_suche)

    print("=" * 72)
    print(f"FRAGE: {frage}")
    print(f"ROUTE: {antwort.route.name} (Risiko-Score {antwort.risiko_score})")
    print(f"DOMAENEN: {klassifikation.domaenen or '(keine erkannt)'}")
    print("-" * 72)
    print(antwort.text)
    print("-" * 72)
    print(f"QUELLEN: {', '.join(antwort.quellen_ids) or '(keine)'}")
    print(
        "GUARDRAILS: "
        + ", ".join(f"{e.guardrail_id}:{e.aktion}" for e in antwort.guardrail_events)
    )
    print("=" * 72)
    return 0


if __name__ == "__main__":
    sys.exit(main())
