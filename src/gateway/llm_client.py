"""Anthropic API client implementing the orchestrator's LLMClient protocol.

Per-route request parameters are verified against the current Anthropic API
(claude-api reference, Abruf 2026-07-06):

- Route C (claude-haiku-4-5): standard endpoint, temperature 0.0 (classification).
- Route A (claude-sonnet-5): standard endpoint, adaptive thinking, NO temperature
  (sampling params rejected with 400 on Sonnet 5).
- Route B (claude-fable-5): beta endpoint, thinking always on (parameter omitted),
  NO temperature, server-side refusal fallback to claude-opus-4-8
  (betas=["server-side-fallback-2026-06-01"], fallbacks=[...]).

The `anthropic` SDK is injected (real client built lazily via build_default_client),
so tests run without the package or network.

# SPEC: AGENT_ARCHITECTURE.md §1 (Modellzugriff ueber Anthropic API), §2 (Routing)
# SPEC: CLAUDE.md §3 (offizielle Python-SDK, Retries mit Backoff, per-route max_tokens)
"""

from __future__ import annotations

import os
from collections.abc import Sequence
from typing import Any, Protocol

from src.gateway.config import (
    ModelProfile,
    RouteConfig,
    default_model_id,
    resolve_model,
    retry_config,
    route_config,
)
from src.gateway.gemini_client import GeminiLLMClient, build_gemini_client
from src.gateway.gemma_client import (
    _DEFAULT_HOST,
    GemmaLLMClient,
    build_gemma_client,
)
from src.gateway.prompt_builder import build_system, build_user_message
from src.rag.chunker import Chunk
from src.router.router import Route
from src.shared.exceptions import ParameterNotFoundError
from src.shared.texts import text as i18n_text

# Beta-Flag fuer server-side Refusal-Fallback (claude-api-Referenz, exakt dieser String).
_FALLBACK_BETA = "server-side-fallback-2026-06-01"


class _MessagesAPI(Protocol):
    def create(self, **kwargs: Any) -> Any: ...


class _Beta(Protocol):
    messages: _MessagesAPI


class AnthropicClient(Protocol):
    """Minimal surface of anthropic.Anthropic that this module uses."""

    messages: _MessagesAPI
    beta: _Beta


def _extract_text(response: Any, sprache: str) -> str:
    """Collect text blocks; a refused chain returns the safety-refusal template.

    # SPEC: Fable-5 refusal handling (claude-api-Referenz): stop_reason 'refusal'
    # before reading content.
    """
    if getattr(response, "stop_reason", None) == "refusal":
        return i18n_text("sicherheits_ablehnung", sprache)
    teile = [
        block.text
        for block in getattr(response, "content", [])
        if getattr(block, "type", None) == "text"
    ]
    return "".join(teile)


class AnthropicLLMClient:
    """LLMClient implementation over the Anthropic Messages API.

    Implements the structural protocol expected by src.orchestrator (generate()).
    """

    def __init__(
        self,
        client: AnthropicClient,
        sprache: str = "de",
        modell_profil: ModelProfile | None = None,
    ) -> None:
        self._client = client
        self._sprache = sprache
        # Ist ein Profil gesetzt (User-Modellwahl), ueberschreibt es das Route-Modell.
        self._profil = modell_profil

    def generate(
        self,
        route: Route,
        anfrage: str,
        chunks: Sequence[Chunk],
        korrektur_hinweis: str | None,
    ) -> str:
        system = build_system()
        user = build_user_message(anfrage, chunks, korrektur_hinweis)
        messages = [{"role": "user", "content": user}]

        if self._profil is not None:
            return self._generate_profil(self._profil, system, messages)

        cfg = route_config(route)
        if route is Route.B_KOMPLEX:
            return self._generate_fable(cfg, system, messages)
        if route is Route.A_STANDARD:
            return self._generate_sonnet(cfg, system, messages)
        return self._generate_haiku(cfg, system, messages)

    def _generate_profil(
        self, profil: ModelProfile, system: str, messages: list[dict[str, str]]
    ) -> str:
        """Generate with an explicitly chosen model (any Claude model in the catalog)."""
        kwargs: dict[str, Any] = {
            "model": profil.id,
            "max_tokens": profil.max_tokens,
            "system": system,
            "messages": messages,
        }
        if profil.thinking:
            kwargs["thinking"] = {"type": profil.thinking}
        if profil.temperature is not None:
            kwargs["temperature"] = profil.temperature
        if profil.endpoint == "beta":
            if profil.fallback_model:
                kwargs["betas"] = [_FALLBACK_BETA]
                kwargs["fallbacks"] = [{"model": profil.fallback_model}]
            return _extract_text(self._client.beta.messages.create(**kwargs), self._sprache)
        return _extract_text(self._client.messages.create(**kwargs), self._sprache)

    def _generate_haiku(
        self, cfg: RouteConfig, system: str, messages: list[dict[str, str]]
    ) -> str:
        kwargs: dict[str, Any] = {
            "model": cfg.model,
            "max_tokens": cfg.max_tokens,
            "system": system,
            "messages": messages,
        }
        if cfg.temperature is not None:
            kwargs["temperature"] = cfg.temperature
        return _extract_text(self._client.messages.create(**kwargs), self._sprache)

    def _generate_sonnet(
        self, cfg: RouteConfig, system: str, messages: list[dict[str, str]]
    ) -> str:
        # Adaptive thinking; NO temperature (400 on Sonnet 5).
        kwargs: dict[str, Any] = {
            "model": cfg.model,
            "max_tokens": cfg.max_tokens,
            "thinking": {"type": "adaptive"},
            "system": system,
            "messages": messages,
        }
        return _extract_text(self._client.messages.create(**kwargs), self._sprache)

    def _generate_fable(
        self, cfg: RouteConfig, system: str, messages: list[dict[str, str]]
    ) -> str:
        # Thinking always on -> omit the parameter; NO temperature; refusal fallback.
        kwargs: dict[str, Any] = {
            "model": cfg.model,
            "max_tokens": cfg.max_tokens,
            "system": system,
            "messages": messages,
        }
        if cfg.fallback_model:
            kwargs["betas"] = [_FALLBACK_BETA]
            kwargs["fallbacks"] = [{"model": cfg.fallback_model}]
        return _extract_text(self._client.beta.messages.create(**kwargs), self._sprache)


def _build_anthropic_client(profil: ModelProfile | None) -> AnthropicLLMClient:
    """Construct the Anthropic client from ANTHROPIC_API_KEY + retry config.

    anthropic wird lazy importiert, damit Modul/Tests ohne das Paket laufen.
    # SPEC: CLAUDE.md §3 (Secrets: environment variables only)
    """
    import anthropic

    retries = retry_config()
    # Der echte SDK-Client erfuellt AnthropicClient strukturell (messages.create,
    # beta.messages.create); die Protocol-Attribute sind bewusst minimal.
    sdk_client: AnthropicClient = anthropic.Anthropic(  # type: ignore[assignment]
        max_retries=retries.max_attempts
    )
    return AnthropicLLMClient(sdk_client, modell_profil=profil)


def build_default_client() -> AnthropicLLMClient:
    """Route-basierter Anthropic-Client (Rueckwaertskompatibilitaet, kein Modell-Override)."""
    return _build_anthropic_client(None)


def _gemma_host(profil: ModelProfile) -> str:
    """Ollama-Host fuer ein Gemma-Profil: lokal, oder Remote (Cloud-GPU) aus host_env.

    Ist host_env gesetzt, aber die Env-Var leer -> klarer Fehler statt stiller 404
    (der Cloud-GPU-Endpoint wird im GCP-Deploy-Baustein bereitgestellt).
    """
    if not profil.host_env:
        return _DEFAULT_HOST
    host = os.environ.get(profil.host_env)
    if not host:
        raise ParameterNotFoundError(
            f"Cloud-Gemma '{profil.id}' braucht einen Remote-Host: setze ${profil.host_env} "
            f"(GPU-Endpoint). Bis dahin die lokalen Gemma-Modelle nutzen."
        )
    return host


def build_llm_client(
    model_id: str | None = None,
) -> AnthropicLLMClient | GemmaLLMClient | GeminiLLMClient:
    """Return the LLMClient for a user-chosen model id (Hybrid Anthropic <-> Vertex-EU <-> lokal).

    Ohne model_id greift das Katalog-Default-Modell. Der zurueckgegebene Client erfuellt
    das Orchestrator-LLMClient-Protokoll (generate()) unabhaengig vom Provider.
    # SPEC: AGENT_ARCHITECTURE.md §2 (Modell-Katalog, User-Wahl); §8 (EU-first/DSGVO)
    """
    profil = resolve_model(model_id or default_model_id())
    if profil.provider == "gemma":
        return build_gemma_client(profil, host=_gemma_host(profil))
    if profil.provider == "gemini":
        return build_gemini_client(profil)
    return _build_anthropic_client(profil)
