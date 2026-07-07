"""MCP-Client-Tests: Ergebnis-Extraktion (SDK-frei) + echter Interop Client<->Brain.

# ADR: opus-deck ADR-0002 (MCP-Rueckgrat, Client-Seite)
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from src.mcp_client.client import ergebnis_aus


class _Text:
    def __init__(self, text: str) -> None:
        self.text = text


class _Result:
    def __init__(self, structured: object = None, content: list[object] | None = None) -> None:
        self.structuredContent = structured
        self.content = content or []


class TestErgebnisExtraktion:
    def test_strukturiert_result_wird_ausgepackt(self) -> None:
        assert ergebnis_aus(_Result(structured={"result": [1, 2, 3]})) == [1, 2, 3]

    def test_strukturiert_dict_bleibt(self) -> None:
        assert ergebnis_aus(_Result(structured={"a": 1, "b": 2})) == {"a": 1, "b": 2}

    def test_textbloecke_werden_gefuegt(self) -> None:
        out = ergebnis_aus(_Result(content=[_Text("hallo"), _Text("welt")]))
        assert out == "hallo\nwelt"


class TestClientBrainInterop:
    """Echter MCP-Roundtrip: ein Client nutzt den Second-Brain-Server (In-Memory-Transport)."""

    def test_client_legt_ab_und_findet_ueber_mcp(self, tmp_path: Path) -> None:
        pytest.importorskip("mcp")
        from mcp.shared.memory import create_connected_server_and_client_session as connect

        from src.brain.server import build_server

        async def run() -> object:
            server = build_server(root=tmp_path / "brain")
            async with connect(server) as session:
                await session.initialize()
                await session.call_tool(
                    "brain_add_raw",
                    {"titel": "Notiz", "inhalt": "Kleinunternehmer Umsatzsteuer Grenze 25000."},
                )
                res = await session.call_tool(
                    "brain_search", {"query": "Kleinunternehmer Umsatzsteuer", "k": 3}
                )
                return ergebnis_aus(res)

        treffer = asyncio.run(run())
        assert isinstance(treffer, list) and treffer
        assert "Notiz" in treffer[0]["titel"]
