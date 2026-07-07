"""Local Gemma client via Ollama, implementing the orchestrator's LLMClient protocol.

Runs a local Gemma 4 model through Ollama (http://localhost:11434) — **no API cost and
no data leaves the machine** (DSGVO/EU-first, analog zu den lokalen Embeddings). Setzt ein
laufendes Ollama (`ollama serve`) + gezogenes Modell (`ollama pull gemma4:e4b`) voraus.
Der HTTP-Opener ist injizierbar, damit Tests ohne Ollama/Netz laufen.

# SPEC: AGENT_ARCHITECTURE.md §2 (Modell-Katalog, lokaler Provider); §8 (EU-first/DSGVO)
"""

from __future__ import annotations

import json
import urllib.request
from collections.abc import Callable, Sequence
from typing import Any

from src.gateway.config import ModelProfile
from src.gateway.prompt_builder import build_system, build_user_message
from src.rag.chunker import Chunk
from src.router.router import Route
from src.shared.exceptions import ToolInputError

_DEFAULT_HOST = "http://localhost:11434"
# Lokale CPU-Inferenz ist langsam (ein 4B-Modell kann fuer eine lange Antwort > 2 min
# brauchen); grosszuegiges Timeout, damit der Aufruf nicht faelschlich abbricht.
_TIMEOUT_S = 900


def _default_opener(req: urllib.request.Request) -> Any:
    return urllib.request.urlopen(req, timeout=_TIMEOUT_S)  # noqa: S310  # nur localhost-Ollama


class GemmaLLMClient:
    """LLMClient over a local Ollama /api/chat endpoint (Gemma 4)."""

    def __init__(
        self,
        profil: ModelProfile,
        host: str = _DEFAULT_HOST,
        sprache: str = "de",
        opener: Callable[[urllib.request.Request], Any] = _default_opener,
    ) -> None:
        self._profil = profil
        self._host = host.rstrip("/")
        self._sprache = sprache
        self._opener = opener

    def generate(
        self,
        route: Route,
        anfrage: str,
        chunks: Sequence[Chunk],
        korrektur_hinweis: str | None,
    ) -> str:
        system = build_system()
        user = build_user_message(anfrage, chunks, korrektur_hinweis)
        optionen: dict[str, Any] = {"num_predict": self._profil.max_tokens}
        if self._profil.temperature is not None:
            optionen["temperature"] = self._profil.temperature
        payload: dict[str, Any] = {
            "model": self._profil.id,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "stream": False,
            "options": optionen,
        }
        req = urllib.request.Request(
            f"{self._host}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with self._opener(req) as resp:
                daten = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # Ollama nicht erreichbar / Modell nicht gezogen
            raise ToolInputError(
                f"Lokales Modell nicht erreichbar ({self._host}). Laeuft Ollama "
                f"('ollama serve') und ist '{self._profil.id}' gezogen "
                f"('ollama pull {self._profil.id}')? Ursache: {type(exc).__name__}"
            ) from exc
        nachricht = daten.get("message") or {}
        return str(nachricht.get("content", "")).strip()


def build_gemma_client(profil: ModelProfile, host: str = _DEFAULT_HOST) -> GemmaLLMClient:
    """Construct a GemmaLLMClient for a catalog profile (production opener)."""
    return GemmaLLMClient(profil, host=host)
