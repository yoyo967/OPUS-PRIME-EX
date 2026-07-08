"""Schlanke Referenz-Web-UI fuer OPUS PRIME EX (nur Python-Standardbibliothek).

Serviert eine Chat-Oberflaeche und einen /api/frage-Endpoint, der die volle
Pipeline (Klassifikation -> Router -> Retrieval -> Modell -> Guardrails) durchlaeuft
und das Ergebnis inkl. sichtbarer Pipeline-Details zurueckgibt.

Die deterministische Pipeline (Klassifikation, Retrieval, Guardrails) laeuft OHNE
API-Key/Guthaben; nur die Modellantwort haengt am Key. Faellt der Modellaufruf aus
(kein Guthaben/Key), zeigt die UI die Pipeline trotzdem an und meldet den Grund
nutzerfreundlich - kein Stacktrace nach aussen (CLAUDE.md §3).

Bind: lokal an 127.0.0.1 (DSGVO/Least-Privilege); auf Cloud Run (Env PORT gesetzt) an
0.0.0.0:$PORT. Der Server hat KEINE eigene Auth -> Zugriffskontrolle ueber die
Cloud-Run-Exposition (IAM/Identity-Token bzw. vorgelagerter Proxy).

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
from urllib.parse import parse_qs, urlparse

_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT))

from src.brain.retrieval import brain_search, build_brain_index  # noqa: E402
from src.brain.store import BrainStore  # noqa: E402
from src.gateway.config import list_models, resolve_model  # noqa: E402
from src.orchestrator.orchestrator import run  # noqa: E402
from src.rag.ingest import run_ingest  # noqa: E402
from src.rag.retrieval import build_rag_suche  # noqa: E402
from src.rag.store import InMemoryVectorStore  # noqa: E402
from src.router.classifier import classify  # noqa: E402
from src.router.router import route_for  # noqa: E402
from src.shared.exceptions import ToolInputError  # noqa: E402

_INDEX = Path(__file__).resolve().parent / "index.html"
_BRAIN_ROOT = _ROOT / "brain"


def _resolve_bind() -> tuple[str, int]:
    """Bind-Adresse: lokal 127.0.0.1:8848 (DSGVO/Least-Privilege). Auf Cloud Run setzt die
    Plattform PORT und erwartet Lauschen auf 0.0.0.0:$PORT -> dann container-weit binden.
    HOST explizit ueberschreibbar. Der Server selbst hat KEINE Auth; die Zugriffskontrolle
    liegt auf der Cloud-Run-Exposition (IAM/Identity-Token bzw. vorgelagerter Proxy).
    """
    port = int(os.environ.get("PORT", "8848"))
    host = os.environ.get("HOST") or ("0.0.0.0" if os.environ.get("PORT") else "127.0.0.1")
    return host, port


def _token_ok(header_value: str | None) -> bool:
    """Schreib-/teure Endpoints (POST) optional per Token schuetzen.

    Ist OPUS_API_TOKEN NICHT gesetzt (lokal), bleibt alles offen wie bisher. Ist es gesetzt
    (oeffentliche Cloud-Exposition), muss der Header X-Opus-Token exakt passen. Der Token liegt
    im Browser (client-seitig) -> Bremsschwelle gegen Drive-by-/Bot-Missbrauch + Kostenschutz,
    KEIN Vault; die harte Absicherung ist IAP/Proxy (siehe docs/deploy_cloud_run.md).
    """
    token = os.environ.get("OPUS_API_TOKEN")
    return not token or header_value == token

# Route -> lesbarer Modellname fuer die UI (Anzeige, nicht Logik).
_ROUTE_MODELL = {
    "A_STANDARD": "Claude Sonnet 5 (Standard)",
    "B_KOMPLEX": "Claude Fable 5 (komplex)",
    "C_TRIAGE": "Claude Haiku 4.5 (Triage)",
}


def build_store() -> InMemoryVectorStore:
    """Korpus laden: bevorzugt den Live-Snapshot (echte Gesetze), sonst die Fixtures.

    Erzeuge den Live-Snapshot mit:  python scripts/ingest.py --live

    Dense-Embeddings werden nur genutzt, wenn config/embeddings.yaml sie aktiviert
    (sonst reines BM25, dependency-frei).
    """
    from src.rag.embeddings import build_embedder, load_embedding_config

    embedder = build_embedder(load_embedding_config())
    snapshot = _ROOT / "korpus" / "snapshot.jsonl"
    if snapshot.exists():
        from src.rag.persistence import load_corpus

        return InMemoryVectorStore(load_corpus(snapshot), embedder=embedder)
    _, chunks = run_ingest()
    return InMemoryVectorStore(chunks, embedder=embedder)


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


def verarbeite_frage(
    frage: str,
    store: InMemoryVectorStore,
    llm: Any | None,
    modell_anzeige: str | None = None,
) -> dict[str, Any]:
    """Eine Frage durch die Pipeline; gibt Antwort + sichtbare Pipeline-Details.

    modell_anzeige: Label des explizit gewaehlten Modells (Hybrid Anthropic <-> lokal);
    ueberschreibt die routenbasierte Modellanzeige, falls gesetzt.
    """
    klassifikation = classify(frage)
    route, score = route_for(klassifikation)
    rag_suche = build_rag_suche(store)
    ergebnis: dict[str, Any] = {
        "frage": frage,
        "route": route.name,
        "modell": modell_anzeige or _ROUTE_MODELL.get(route.name, route.name),
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
        if not modell_anzeige:
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


def _llm_for(model_id: str | None, default_llm: Any | None) -> tuple[Any | None, str | None]:
    """LLM-Client fuer eine Anfrage: explizite Modellwahl (Anthropic/Gemma) oder Default.

    Ein gewaehltes lokales Gemma-Modell laeuft ohne API-Key; ein Anthropic-Modell ohne Key
    schlaegt erst beim Aufruf fehl (nutzerfreundlich in _fehlertext gemappt).
    """
    if not model_id:
        return default_llm, None
    try:
        profil = resolve_model(model_id)
    except Exception:
        return default_llm, None  # unbekannte Modell-ID -> Default-Routing
    from src.gateway.llm_client import build_llm_client

    return build_llm_client(model_id), profil.label


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
    brain: BrainStore
    brain_index: InMemoryVectorStore

    @classmethod
    def _brain_reindex(cls) -> None:
        cls.brain_index = build_brain_index(cls.brain.alle())

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        # CORS: die OPUS-DECK-UI (anderer Origin) darf das Backend aufrufen. X-Opus-Token muss
        # in Allow-Headers stehen, sonst blockt der Preflight die POSTs mit Token.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-Opus-Token")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802  (CORS-Preflight)
        self._send(204, b"", "text/plain")

    def _send_json(self, obj: Any, code: int = 200) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self._send(code, body, "application/json; charset=utf-8")

    def do_GET(self) -> None:  # noqa: N802  (http.server-Konvention)
        parsed = urlparse(self.path)
        pfad = parsed.path.rstrip("/")
        q = parse_qs(parsed.query)
        if pfad == "/api/models":
            self._send_json(
                {"modelle": [
                    {"id": m.id, "label": m.label, "provider": m.provider}
                    for m in list_models()
                ]}
            )
            return
        if pfad.startswith("/api/brain/") and self._brain_get(pfad, q):
            return
        if self.path not in ("/", "/index.html"):
            self._send(404, b"not found", "text/plain; charset=utf-8")
            return
        html = _INDEX.read_text(encoding="utf-8").encode("utf-8")
        self._send(200, html, "text/html; charset=utf-8")

    def _brain_get(self, pfad: str, q: dict[str, list[str]]) -> bool:
        """Second-Brain-Lese-Endpoints (search/list/proposals/proposal). True wenn behandelt."""
        if pfad == "/api/brain/search":
            query = (q.get("q") or [""])[0]
            k = int((q.get("k") or ["5"])[0])
            self._send_json({"treffer": brain_search(self.brain_index, query, k)})
        elif pfad == "/api/brain/list":
            schicht = (q.get("schicht") or [""])[0] or None
            self._send_json({"docs": [
                {"id": d.id, "schicht": d.schicht, "titel": d.titel}
                for d in self.brain.liste(schicht)
            ]})
        elif pfad == "/api/brain/proposals":
            self._send_json({"proposals": [
                {"id": p.id, "ziel": p.ziel, "titel": p.titel, "wer": p.wer}
                for p in self.brain.list_proposals()
            ]})
        elif pfad == "/api/brain/proposal":
            try:
                p = self.brain.read_proposal((q.get("id") or [""])[0])
            except ToolInputError as exc:
                self._send_json({"fehler": str(exc)}, 404)
                return True
            self._send_json({"id": p.id, "ziel": p.ziel, "titel": p.titel,
                             "inhalt": p.inhalt, "diff": p.diff})
        else:
            return False
        return True

    def do_POST(self) -> None:  # noqa: N802
        pfad = urlparse(self.path).path.rstrip("/")
        if pfad not in ("/api/frage", "/api/brain/add_raw", "/api/brain/approve",
                        "/api/brain/reject"):
            self._send(404, b"not found", "text/plain; charset=utf-8")
            return
        if not _token_ok(self.headers.get("X-Opus-Token")):
            self._send_json({"fehler": "nicht autorisiert"}, 401)
            return
        laenge = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(laenge) or b"{}")
        except (ValueError, TypeError):
            self._send_json({"fehler": "ungueltige Anfrage"}, 400)
            return
        if pfad == "/api/frage":
            self._post_frage(payload)
        else:
            self._brain_post(pfad, payload)

    def _post_frage(self, payload: dict[str, Any]) -> None:
        frage = str(payload.get("frage", "")).strip()
        model_id = payload.get("model_id")
        model_id = str(model_id).strip() if model_id else None
        if not frage:
            self._send_json({"fehler": "leere Frage"}, 400)
            return
        llm, label = _llm_for(model_id, self.llm)
        ergebnis = verarbeite_frage(frage, self.store, llm, modell_anzeige=label)
        self._send_json(ergebnis)

    def _brain_post(self, pfad: str, payload: dict[str, Any]) -> None:
        """Second-Brain-Schreib-Endpoints. approve/reject = MENSCH-Aktion (nur ueber die UI)."""
        try:
            if pfad == "/api/brain/add_raw":
                d = self.brain.add_raw(
                    str(payload.get("titel") or "Notiz"),
                    str(payload.get("inhalt", "")),
                    payload.get("tags"),
                )
                self._brain_reindex()
                self._send_json({"id": d.id, "titel": d.titel})
            elif pfad == "/api/brain/approve":
                d = self.brain.approve_proposal(str(payload.get("id", "")))
                self._brain_reindex()
                self._send_json({"id": d.id, "titel": d.titel})
            else:  # /api/brain/reject
                self.brain.reject_proposal(str(payload.get("id", "")))
                self._send_json({"ok": True})
        except ToolInputError as exc:
            self._send_json({"fehler": str(exc)}, 400)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        pass  # ruhige Konsole


def main() -> int:
    _load_env(_ROOT / ".env")
    _Handler.store = build_store()
    _Handler.llm = _build_llm()
    _Handler.brain = BrainStore(_BRAIN_ROOT)
    _Handler.brain_index = build_brain_index(_Handler.brain.alle())
    zustand = "mit API-Key (Live-Antworten)" if _Handler.llm else "OHNE Key (nur Pipeline sichtbar)"
    print(f"[web] OPUS PRIME EX Referenz-UI - {zustand}")
    print(f"[web] Korpus: {len(_Handler.store.chunks)} Chunks (Fixtures, BM25-only)")
    print(f"[web] Second Brain: {len(_Handler.brain.alle())} Dokumente ({_BRAIN_ROOT})")
    host, port = _resolve_bind()
    print(f"[web] -> http://{host}:{port}   (Strg+C zum Beenden)")
    with socketserver.ThreadingTCPServer((host, port), _Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[web] beendet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
