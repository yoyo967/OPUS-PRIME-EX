"""Load and type the model-routing config (config/models.yaml).

# SPEC: AGENT_ARCHITECTURE.md §2 (Modell-Routing), §8 A1 (IDs/Parameter gegen die
# aktuelle Anthropic-API parametrisiert); CLAUDE.md §3 (per-route max_tokens/temperature)
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from src.router.router import Route
from src.shared.exceptions import ParameterNotFoundError

_MODELS_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "models.yaml"

# Route-Enum -> Schluessel in config/models.yaml
_ROUTE_KEY = {
    Route.A_STANDARD: "a_standard",
    Route.B_KOMPLEX: "b_komplex",
    Route.C_TRIAGE: "c_triage",
}


@dataclass(frozen=True)
class RouteConfig:
    """Model + sampling parameters for one route.

    temperature is None when the parameter must NOT be sent (rejected with 400 on
    claude-sonnet-5 / claude-fable-5; see config/models.yaml comment and
    spec/OPEN_QUESTIONS.md #10). fallback_model is set only for the Fable route
    (server-side refusal fallback).
    """

    model: str
    temperature: float | None
    max_tokens: int
    fallback_model: str | None = None


@dataclass(frozen=True)
class RetryConfig:
    """Retry/backoff parameters (SPEC: CLAUDE.md §3)."""

    max_attempts: int
    backoff_base_s: float
    backoff_factor: float


@dataclass(frozen=True)
class ModelProfile:
    """A user-selectable model and its request profile (Hybrid Anthropic <-> lokal).

    provider: "anthropic" | "gemma". Fuer anthropic steuern endpoint/thinking/temperature/
    fallback_model den Request; fuer gemma laeuft das Modell lokal ueber Ollama.
    # SPEC: AGENT_ARCHITECTURE.md §2 (Modell-Katalog, Provider-Abstraktion), §7 (Kosten)
    """

    id: str
    label: str
    provider: str
    endpoint: str = "standard"  # anthropic: standard | beta
    thinking: str | None = None  # anthropic: "adaptive" | None
    temperature: float | None = None
    max_tokens: int = 4096
    fallback_model: str | None = None


def _profile_from(eintrag: dict[str, Any]) -> ModelProfile:
    temp_raw = eintrag.get("temperature")
    return ModelProfile(
        id=str(eintrag["id"]),
        label=str(eintrag.get("label", eintrag["id"])),
        provider=str(eintrag["provider"]),
        endpoint=str(eintrag.get("endpoint", "standard")),
        thinking=(str(eintrag["thinking"]) if eintrag.get("thinking") else None),
        temperature=(None if temp_raw is None else float(temp_raw)),
        max_tokens=int(eintrag.get("max_tokens", 4096)),
        fallback_model=(
            str(eintrag["fallback_model"]) if eintrag.get("fallback_model") else None
        ),
    )


def list_models(models_path: Path = _MODELS_PATH) -> list[ModelProfile]:
    """Return the user-selectable model catalog (order preserved)."""
    raw = _load_raw(str(models_path))
    return [_profile_from(e) for e in raw.get("catalog", []) or []]


def default_model_id(models_path: Path = _MODELS_PATH) -> str:
    """Return the id of the default model (falls back to the first catalog entry)."""
    raw = _load_raw(str(models_path))
    if raw.get("default_model"):
        return str(raw["default_model"])
    katalog = raw.get("catalog") or []
    if not katalog:
        raise ParameterNotFoundError("models.yaml hat weder default_model noch catalog.")
    return str(katalog[0]["id"])


def resolve_model(model_id: str, models_path: Path = _MODELS_PATH) -> ModelProfile:
    """Return the ModelProfile for a chosen model id."""
    for profil in list_models(models_path):
        if profil.id == model_id:
            return profil
    raise ParameterNotFoundError(f"Unbekanntes Modell '{model_id}' (nicht im Katalog).")


@lru_cache(maxsize=1)
def _load_raw(path: str) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        loaded: dict[str, Any] = yaml.safe_load(handle)
    return loaded


def route_config(route: Route, models_path: Path = _MODELS_PATH) -> RouteConfig:
    """Return the RouteConfig for a routing decision."""
    raw = _load_raw(str(models_path))
    key = _ROUTE_KEY[route]
    routes: dict[str, Any] = raw.get("routes", {})
    if key not in routes:
        raise ParameterNotFoundError(f"Keine Route-Konfiguration fuer '{key}' in models.yaml.")
    eintrag = routes[key]
    temp_raw = eintrag.get("temperature")
    return RouteConfig(
        model=str(eintrag["model"]),
        temperature=None if temp_raw is None else float(temp_raw),
        max_tokens=int(eintrag["max_tokens"]),
        fallback_model=(
            str(eintrag["fallback_model"]) if eintrag.get("fallback_model") else None
        ),
    )


def retry_config(models_path: Path = _MODELS_PATH) -> RetryConfig:
    """Return the retry/backoff config."""
    raw = _load_raw(str(models_path))
    eintrag: dict[str, Any] = raw.get("retry", {})
    return RetryConfig(
        max_attempts=int(eintrag.get("max_attempts", 3)),
        backoff_base_s=float(eintrag.get("backoff_base_s", 1.0)),
        backoff_factor=float(eintrag.get("backoff_factor", 2.0)),
    )
