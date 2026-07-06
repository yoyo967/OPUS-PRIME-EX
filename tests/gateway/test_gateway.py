"""Gateway tests: config loader, prompt builder, and the LLM client wiring.

The Anthropic client is faked — no package or network needed. These verify the
per-route request parameters that were checked against the live API in Meilenstein 9.

# SPEC: AGENT_ARCHITECTURE.md §2 (Routing); CLAUDE.md §3 (per-route Parameter)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.gateway.config import route_config
from src.gateway.llm_client import AnthropicLLMClient
from src.gateway.prompt_builder import (
    build_system,
    build_user_message,
    load_system_prompt,
)
from src.rag.chunker import Chunk
from src.router.router import Route
from src.shared.texts import text as i18n_text


def _chunk() -> Chunk:
    return Chunk(
        chunk_id="de-ustg-2025-01-01-p19",
        quelle_typ="gesetz",
        jurisdiktion="DE",
        gesetz="UStG",
        celex=None,
        einheit="§ 19",
        ueberschrift="Besteuerung der Kleinunternehmer",
        gueltig_ab="2025-01-01",
        gueltig_bis=None,
        rechtsstand_abruf="2026-07-05",
        quelle_url="https://www.gesetze-im-internet.de/ustg/__19.html",
        text="Grenzen: 25 000 Euro Vorjahr, 100 000 Euro laufend.",
        hash="sha256:test",
        typ="norm",
        domaene=("steuerrecht",),
    )


# --- Fake Anthropic SDK -----------------------------------------------------
@dataclass
class _FakeBlock:
    type: str
    text: str


@dataclass
class _FakeResponse:
    content: list[_FakeBlock]
    stop_reason: str | None = "end_turn"
    model: str = "fake"


class _RecordingMessages:
    def __init__(self, response: _FakeResponse) -> None:
        self._response = response
        self.calls: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> _FakeResponse:
        self.calls.append(kwargs)
        return self._response


class _FakeBeta:
    def __init__(self, messages: _RecordingMessages) -> None:
        self.messages = messages


class _FakeClient:
    def __init__(self, text: str = "Antwort.", stop_reason: str = "end_turn") -> None:
        response = _FakeResponse([_FakeBlock("text", text)], stop_reason)
        self.messages = _RecordingMessages(response)
        self.beta = _FakeBeta(_RecordingMessages(response))


class TestRouteConfig:
    def test_route_a_sonnet_ohne_temperature(self) -> None:
        cfg = route_config(Route.A_STANDARD)
        assert cfg.model == "claude-sonnet-5"
        assert cfg.temperature is None
        assert cfg.fallback_model is None

    def test_route_b_fable_mit_fallback(self) -> None:
        cfg = route_config(Route.B_KOMPLEX)
        assert cfg.model == "claude-fable-5"
        assert cfg.temperature is None
        assert cfg.fallback_model == "claude-opus-4-8"

    def test_route_c_haiku_temperature_0(self) -> None:
        cfg = route_config(Route.C_TRIAGE)
        assert cfg.model == "claude-haiku-4-5-20251001"
        assert cfg.temperature == 0.0


class TestPromptBuilder:
    def test_system_prompt_extrahiert_aus_fence(self) -> None:
        prompt = load_system_prompt()
        assert prompt.startswith("# ROLLE")
        assert "Markenrecht" in prompt  # v1.2 enthaelt Domaene 7
        assert "```" not in prompt  # nur der Fence-Inhalt

    def test_system_enthaelt_few_shots(self) -> None:
        system = build_system()
        assert "<beispiele>" in system
        assert "§ 19 Abs. 1 UStG" in system  # Steuerrecht-Few-Shot

    def test_user_message_enthaelt_zitierkopf_und_frage(self) -> None:
        user = build_user_message("Kleinunternehmergrenze?", [_chunk()], None)
        assert "<kontext" in user
        assert "§ 19" in user and "gesetze-im-internet" in user
        assert user.rstrip().endswith("Frage: Kleinunternehmergrenze?")

    def test_korrekturhinweis_wird_eingebettet(self) -> None:
        user = build_user_message("Frage?", [], "belege § 19 UStG")
        assert "Korrekturhinweis: belege § 19 UStG" in user


class TestAnthropicLLMClient:
    def test_route_a_adaptive_thinking_ohne_temperature(self) -> None:
        fake = _FakeClient(text="Nach § 19 UStG ...")
        client = AnthropicLLMClient(fake)
        out = client.generate(Route.A_STANDARD, "Frage?", [_chunk()], None)
        assert out == "Nach § 19 UStG ..."
        kwargs = fake.messages.calls[0]
        assert kwargs["model"] == "claude-sonnet-5"
        assert kwargs["thinking"] == {"type": "adaptive"}
        assert "temperature" not in kwargs
        assert fake.beta.messages.calls == []  # Standard-Endpoint

    def test_route_b_fable_beta_endpoint_mit_fallback(self) -> None:
        fake = _FakeClient()
        client = AnthropicLLMClient(fake)
        client.generate(Route.B_KOMPLEX, "Komplexe Gestaltung?", [], None)
        assert fake.messages.calls == []  # NICHT der Standard-Endpoint
        kwargs = fake.beta.messages.calls[0]
        assert kwargs["model"] == "claude-fable-5"
        assert kwargs["betas"] == ["server-side-fallback-2026-06-01"]
        assert kwargs["fallbacks"] == [{"model": "claude-opus-4-8"}]
        assert "thinking" not in kwargs  # Fable: thinking immer an
        assert "temperature" not in kwargs

    def test_route_c_haiku_mit_temperature_0(self) -> None:
        fake = _FakeClient()
        client = AnthropicLLMClient(fake)
        client.generate(Route.C_TRIAGE, "Was heisst OSS?", [], None)
        kwargs = fake.messages.calls[0]
        assert kwargs["model"] == "claude-haiku-4-5-20251001"
        assert kwargs["temperature"] == 0.0
        assert "thinking" not in kwargs

    def test_refusal_liefert_sicherheits_template(self) -> None:
        fake = _FakeClient(text="partial", stop_reason="refusal")
        client = AnthropicLLMClient(fake)
        out = client.generate(Route.A_STANDARD, "Frage?", [], None)
        assert out == i18n_text("sicherheits_ablehnung")
        assert "partial" not in out

    def test_generate_erfuellt_orchestrator_protokoll(self) -> None:
        # Der Client wird direkt vom Orchestrator akzeptiert (struktureller Protocol).
        from src.orchestrator.orchestrator import LLMClient

        client: LLMClient = AnthropicLLMClient(_FakeClient())
        assert callable(client.generate)
