"""Gateway tests: config loader, prompt builder, and the LLM client wiring.

The Anthropic client is faked — no package or network needed. These verify the
per-route request parameters that were checked against the live API in Meilenstein 9.

# SPEC: AGENT_ARCHITECTURE.md §2 (Routing); CLAUDE.md §3 (per-route Parameter)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

import pytest

from src.gateway.config import (
    default_model_id,
    list_models,
    resolve_model,
    route_config,
)
from src.gateway.gemini_client import GeminiLLMClient
from src.gateway.gemma_client import GemmaLLMClient
from src.gateway.llm_client import AnthropicLLMClient, build_llm_client
from src.gateway.prompt_builder import (
    build_system,
    build_user_message,
    load_system_prompt,
)
from src.rag.chunker import Chunk
from src.router.router import Route
from src.shared.exceptions import ParameterNotFoundError, ToolInputError
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


class TestModelCatalog:
    def test_katalog_enthaelt_anthropic_und_gemma(self) -> None:
        provider = {m.id: m.provider for m in list_models()}
        assert provider["claude-sonnet-5"] == "anthropic"
        assert provider["claude-opus-4-8"] == "anthropic"
        assert provider["gemma4:e4b"] == "gemma"

    def test_default_model(self) -> None:
        assert default_model_id() == "claude-sonnet-5"

    def test_resolve_unbekannt_faellt(self) -> None:
        with pytest.raises(ParameterNotFoundError):
            resolve_model("gibt-es-nicht")


class TestAnthropicProfil:
    """User-Modellwahl ueberschreibt das Route-Modell (beliebiges Claude-Modell)."""

    def test_opus_standard_mit_thinking(self) -> None:
        fake = _FakeClient(text="x")
        client = AnthropicLLMClient(fake, modell_profil=resolve_model("claude-opus-4-8"))
        client.generate(Route.C_TRIAGE, "Frage?", [], None)  # Route bewusst egal
        kwargs = fake.messages.calls[0]
        assert kwargs["model"] == "claude-opus-4-8"
        assert kwargs["thinking"] == {"type": "adaptive"}
        assert fake.beta.messages.calls == []

    def test_fable_beta_mit_fallback(self) -> None:
        fake = _FakeClient()
        client = AnthropicLLMClient(fake, modell_profil=resolve_model("claude-fable-5"))
        client.generate(Route.A_STANDARD, "Frage?", [], None)
        assert fake.messages.calls == []
        kwargs = fake.beta.messages.calls[0]
        assert kwargs["model"] == "claude-fable-5"
        assert kwargs["fallbacks"] == [{"model": "claude-opus-4-8"}]

    def test_haiku_mit_temperature(self) -> None:
        fake = _FakeClient()
        client = AnthropicLLMClient(
            fake, modell_profil=resolve_model("claude-haiku-4-5-20251001")
        )
        client.generate(Route.A_STANDARD, "Frage?", [], None)
        assert fake.messages.calls[0]["temperature"] == 0.0


class _FakeOllamaResp:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def __enter__(self) -> _FakeOllamaResp:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")


class TestGemmaClient:
    def test_ruft_ollama_und_liefert_content(self) -> None:
        erfasst: dict[str, Any] = {}

        def opener(req: Any) -> _FakeOllamaResp:
            erfasst["body"] = json.loads(req.data.decode("utf-8"))
            return _FakeOllamaResp(
                {"message": {"role": "assistant", "content": "Nach § 19 UStG ..."}}
            )

        client = GemmaLLMClient(resolve_model("gemma4:e4b"), opener=opener)
        out = client.generate(Route.A_STANDARD, "Frage?", [_chunk()], None)
        assert out == "Nach § 19 UStG ..."
        body = erfasst["body"]
        assert body["model"] == "gemma4:e4b"
        assert body["stream"] is False
        assert body["messages"][0]["role"] == "system"
        assert body["messages"][1]["role"] == "user"

    def test_fehler_liefert_klare_meldung(self) -> None:
        def boom(req: Any) -> Any:
            raise ConnectionRefusedError()

        client = GemmaLLMClient(resolve_model("gemma4:e4b"), opener=boom)
        with pytest.raises(ToolInputError, match="nicht erreichbar"):
            client.generate(Route.A_STANDARD, "Frage?", [], None)


class TestGeminiCatalog:
    def test_katalog_enthaelt_gemini_eu_und_cloud_gemma(self) -> None:
        profile = {m.id: m for m in list_models()}
        flash = profile["gemini-2.5-flash"]
        assert flash.provider == "gemini" and flash.region == "europe-west3"
        cloud = profile["gemma4:27b-cloud"]
        assert cloud.provider == "gemma"
        assert cloud.host_env == "GEMMA_REMOTE_HOST"
        assert cloud.model_name == "gemma4:27b"  # provider-nativer Name != Katalog-id


class TestGeminiClient:
    def test_ruft_caller_mit_model_name_und_liefert_text(self) -> None:
        erfasst: dict[str, Any] = {}

        def caller(modell: str, system: str, user: str, max_tokens: int) -> str:
            erfasst.update(modell=modell, system=system, user=user, max_tokens=max_tokens)
            return "  Nach § 19 UStG ...  "

        client = GeminiLLMClient(resolve_model("gemini-2.5-flash"), caller=caller)
        out = client.generate(Route.A_STANDARD, "Frage?", [_chunk()], None)
        assert out == "Nach § 19 UStG ..."  # getrimmt
        assert erfasst["modell"] == "gemini-2.5-flash"
        assert erfasst["max_tokens"] == 4096
        assert "Frage?" in erfasst["user"]

    def test_fehler_liefert_klare_meldung(self) -> None:
        def boom(modell: str, system: str, user: str, max_tokens: int) -> str:
            raise RuntimeError("kein ADC")

        client = GeminiLLMClient(resolve_model("gemini-2.5-flash"), caller=boom)
        with pytest.raises(ToolInputError, match="Vertex/Gemini nicht erreichbar"):
            client.generate(Route.A_STANDARD, "Frage?", [], None)

    def test_generate_erfuellt_orchestrator_protokoll(self) -> None:
        from src.orchestrator.orchestrator import LLMClient

        client: LLMClient = GeminiLLMClient(
            resolve_model("gemini-2.5-flash"), caller=lambda *_: "ok"
        )
        assert callable(client.generate)


class TestClientFactory:
    def test_gemma_id_liefert_gemma_client(self) -> None:
        assert isinstance(build_llm_client("gemma4:26b"), GemmaLLMClient)

    def test_gemma_client_erfuellt_orchestrator_protokoll(self) -> None:
        from src.orchestrator.orchestrator import LLMClient

        client: LLMClient = build_llm_client("gemma4:e4b")
        assert callable(client.generate)

    def test_gemini_id_liefert_gemini_client(self) -> None:
        assert isinstance(build_llm_client("gemini-2.5-flash"), GeminiLLMClient)

    def test_cloud_gemma_ohne_env_faellt_klar(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GEMMA_REMOTE_HOST", raising=False)
        with pytest.raises(ParameterNotFoundError, match="GEMMA_REMOTE_HOST"):
            build_llm_client("gemma4:27b-cloud")

    def test_cloud_gemma_mit_env_nutzt_remote_host(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("GEMMA_REMOTE_HOST", "http://gpu.example:11434")
        client = build_llm_client("gemma4:27b-cloud")
        assert isinstance(client, GemmaLLMClient)
        assert client._host == "http://gpu.example:11434"  # Remote-GPU-Endpoint
