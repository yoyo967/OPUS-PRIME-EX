"""Schlanke Referenz-Web-UI fuer OPUS PRIME EX (nur Python-Standardbibliothek).

Serviert eine Chat-Oberflaeche und einen /api/frage-Endpoint, der die volle
Pipeline (Klassifikation -> Router -> Retrieval -> Modell -> Guardrails) durchlaeuft
und das Ergebnis inkl. sichtbarer Pipeline-Details zurueckgibt.

Die deterministische Pipeline (Klassifikation, Retrieval, Guardrails) laeuft OHNE
API-Key/Guthaben; nur die Modellantwort haengt am Key. Faellt der Modellaufruf aus
(kein Guthaben/Key), zeigt die UI die Pipeline trotzdem an und meldet den Grund
nutzerfreundlich - kein Stacktrace nach aussen (CLAUDE.md §3).

Nur an 127.0.0.1 gebunden (lokal, DSGVO/Least-Privilege).

Nutzung:  python apps/web/server.py   ->  http://127.0.0.1:8848

# SPEC: AGENT_ARCHITECTURE.md §1 (End-to-End), §6 (Art.-50-Transparenz), §8 A2 (Web-UI)
"""

from __future__ import annotations

import http.server
import json
import os
import socketserver
import sys
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT))

from src.orchestrator.orchestrator import run  # noqa: E402
from src.rag.ingest import run_ingest  # noqa: E402
from src.rag.retrieval import build_rag_suche  # noqa: E402
from src.rag.store import InMemoryVectorStore  # noqa: E402
from src.router.classifier import classify  # noqa: E402
from src.router.router import route_for  # noqa: E402

_INDEX = Path(__file__).resolve().parent / "index.html"
_HOST = "127.0.0.1"
_PORT = 8848

# Route -> lesbarer Modellname fuer die UI (Anzeige, nicht Logik).
_ROUTE_MODELL = {
    "A_STANDARD": "Claude Sonnet 5 (Standard)",
    "B_KOMPLEX": "Claude Fable 5 (komplex)",
    "C_TRIAGE": "Claude Haiku 4.5 (Triage)",
}


def build_store() -> InMemoryVectorStore:
    """Korpus laden: bevorzugt den Live-Snapshot (echte Gesetze), sonst die Fixtures.

    Erzeuge den Live-Snapshot mit:  python scripts/ingest.py --live
    """
    snapshot = _ROOT / "korpus" / "snapshot.jsonl"
    if snapshot.exists():
        from src.rag.persistence import load_corpus

        return InMemoryVectorStore(load_corpus(snapshot))
    _, chunks = run_ingest()
    return InMemoryVectorStore(chunks)


def _fehlertext(exc: Exception) -> str:
    text = str(exc).lower()
    if "credit balance" in text or "too low" in text:
        return (
            "Kein API-Guthaben hinterlegt - die Modellantwort ist noch nicht verfuegbar. "
            "Die Analyse-Pipeline (Klassifikation, Quellenrecherche, Guardrails) laeuft bereits. "
            "Guthaben unter platform.claude.com -> Plans & Billing aufladen."
        )
    if "authentication" in text or "401" in text or "x-api-key" in text:
        return "Der hinterlegte API-Key ist ungueltig. Bitte in der .env pruefen."
    return f"Modellaufruf momentan nicht moeglich ({type(exc).__name__})."


def verarbeite_frage(frage: str, store: InMemoryVectorStore, llm: Any | None) -> dict[str, Any]:
    """Eine Frage durch die Pipeline; gibt Antwort + sichtbare Pipeline-Details."""
    klassifikation = classify(frage)
    route, score = route_for(klassifikation)
    rag_suche = build_rag_suche(store)
    ergebnis: dict[str, Any] = {
        "frage": frage,
        "route": route.name,
        "modell": _ROUTE_MODELL.get(route.name, route.name),
        "domaenen": list(klassifikation.domaenen),
        "risiko_score": score,
        "quellen": [],
        "guardrails": [],
        "antwort": None,
        "fehler": None,
    }
    if llm is None:
        chunks = [] if klassifikation.ist_smalltalk else rag_suche(frage, klassifikation.domaenen)
        ergebnis["quellen"] = [c.chunk_id for c in chunks]
        ergebnis["fehler"] = (
            "Kein API-Key hinterlegt (.env). Die Pipeline laeuft, die Modellantwort ist "
            "noch nicht verfuegbar."
        )
        return ergebnis
    try:
        antwort = run(frage, klassifikation, llm, rag_suche)
        ergebnis["antwort"] = antwort.text
        ergebnis["route"] = antwort.route.name
        ergebnis["modell"] = _ROUTE_MODELL.get(antwort.route.name, antwort.route.name)
        ergebnis["risiko_score"] = antwort.risiko_score
        ergebnis["quellen"] = list(antwort.quellen_ids)
        ergebnis["guardrails"] = [
            f"{e.guardrail_id}:{e.aktion}" for e in antwort.guardrail_events
        ]
    except Exception as exc:  # nur nutzerfreundliche Meldung nach aussen
        chunks = [] if klassifikation.ist_smalltalk else rag_suche(frage, klassifikation.domaenen)
        ergebnis["quellen"] = [c.chunk_id for c in chunks]
        ergebnis["fehler"] = _fehlertext(exc)
    return ergebnis


def _build_llm() -> Any | None:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    from src.gateway.llm_client import build_default_client

    return build_default_client()


def _load_env(pfad: Path) -> None:
    if not pfad.exists():
        return
    for zeile in pfad.read_text(encoding="utf-8").splitlines():
        zeile = zeile.strip()
        if not zeile or zeile.startswith("#") or "=" not in zeile:
            continue
        schluessel, wert = (t.strip() for t in zeile.split("=", 1))
        if schluessel and wert and schluessel not in os.environ:
            os.environ[schluessel] = wert


class _Handler(http.server.BaseHTTPRequestHandler):
    store: InMemoryVectorStore
    llm: Any | None

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802  (http.server-Konvention)
        if self.path not in ("/", "/index.html"):
            self._send(404, b"not found", "text/plain; charset=utf-8")
            return
        html = _INDEX.read_text(encoding="utf-8").encode("utf-8")
        self._send(200, html, "text/html; charset=utf-8")

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/frage":
            self._send(404, b"not found", "text/plain; charset=utf-8")
            return
        laenge = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(laenge) or b"{}")
            frage = str(payload.get("frage", "")).strip()
        except (ValueError, TypeError):
            self._send(400, b'{"fehler":"ungueltige Anfrage"}', "application/json")
            return
        if not frage:
            self._send(400, b'{"fehler":"leere Frage"}', "application/json")
            return
        ergebnis = verarbeite_frage(frage, self.store, self.llm)
        body = json.dumps(ergebnis, ensure_ascii=False).encode("utf-8")
        self._send(200, body, "application/json; charset=utf-8")

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        pass  # ruhige Konsole


def main() -> int:
    _load_env(_ROOT / ".env")
    _Handler.store = build_store()
    _Handler.llm = _build_llm()
    zustand = "mit API-Key (Live-Antworten)" if _Handler.llm else "OHNE Key (nur Pipeline sichtbar)"
    print(f"[web] OPUS PRIME EX Referenz-UI - {zustand}")
    print(f"[web] Korpus: {len(_Handler.store.chunks)} Chunks (Fixtures, BM25-only)")
    print(f"[web] -> http://{_HOST}:{_PORT}   (Strg+C zum Beenden)")
    with socketserver.ThreadingTCPServer((_HOST, _PORT), _Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[web] beendet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
