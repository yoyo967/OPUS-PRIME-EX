"""Gemini client via Vertex AI (EU-Region), implementing the LLMClient protocol.

Runs Google Gemini through **Vertex AI in europe-west3** (EU-first/DSGVO: die Region wird
explizit gesetzt, Daten bleiben in der EU). Arbeitstier ist **Gemini 2.5 Flash** — gemini-2.5-pro
ist in europe-west3 NICHT verfuegbar (404), daher bewusst nur Flash/Flash-Lite im EU-Katalog.
Der Live-Aufruf braucht GCP Application Default Credentials (`gcloud auth application-default
login`) + aktivierte Vertex-AI-API auf dem Projekt. Der Modell-Caller ist injizierbar, damit
Tests ohne `google-cloud-aiplatform`/Netz laufen (analog zum Gemma-Opener).

# SPEC: AGENT_ARCHITECTURE.md §2 (Modell-Katalog, Provider-Abstraktion); §8 (EU-first/DSGVO)
"""

from __future__ import annotations

import os
from collections.abc import Callable, Sequence

from src.gateway.config import ModelProfile
from src.gateway.prompt_builder import build_system, build_user_message
from src.rag.chunker import Chunk
from src.router.router import Route
from src.shared.exceptions import ToolInputError

_DEFAULT_REGION = "europe-west3"  # EU-first (SPEC: CLAUDE.md §8); Pro hier nicht verfuegbar
_DEFAULT_PROJECT = "leadmachines-prod"

# Caller-Signatur: (modell_name, system, user, max_tokens) -> Antworttext.
GeminiCaller = Callable[[str, str, str, int], str]


class GeminiLLMClient:
    """LLMClient over Vertex AI Gemini (EU-Region)."""

    def __init__(
        self,
        profil: ModelProfile,
        project: str | None = None,
        region: str | None = None,
        sprache: str = "de",
        caller: GeminiCaller | None = None,
    ) -> None:
        self._profil = profil
        self._project = project or os.environ.get("GOOGLE_CLOUD_PROJECT") or _DEFAULT_PROJECT
        self._region = region or profil.region or _DEFAULT_REGION
        self._sprache = sprache
        self._caller = caller or self._default_caller

    def generate(
        self,
        route: Route,
        anfrage: str,
        chunks: Sequence[Chunk],
        korrektur_hinweis: str | None,
    ) -> str:
        system = build_system()
        user = build_user_message(anfrage, chunks, korrektur_hinweis)
        modell = self._profil.model_name or self._profil.id
        try:
            return self._caller(modell, system, user, self._profil.max_tokens).strip()
        except Exception as exc:  # Vertex nicht erreichbar / ADC fehlt / API aus / Modell 404
            raise ToolInputError(
                f"Vertex/Gemini nicht erreichbar (Projekt {self._project}, Region {self._region}). "
                f"ADC gesetzt ('gcloud auth application-default login') und Vertex-AI-API aktiv? "
                f"Ist '{modell}' in {self._region} verfuegbar? Ursache: {type(exc).__name__}"
            ) from exc

    def _default_caller(self, modell: str, system: str, user: str, max_tokens: int) -> str:
        """Realer Vertex-Aufruf; vertexai lazy importiert (Modul/Tests laufen ohne das Paket)."""
        import vertexai
        from vertexai.generative_models import GenerativeModel

        vertexai.init(project=self._project, location=self._region)
        modell_obj = GenerativeModel(modell, system_instruction=system)
        antwort = modell_obj.generate_content(
            user, generation_config={"max_output_tokens": max_tokens}
        )
        return str(getattr(antwort, "text", ""))


def build_gemini_client(profil: ModelProfile) -> GeminiLLMClient:
    """Construct a GeminiLLMClient for a catalog profile (production caller)."""
    return GeminiLLMClient(profil)
