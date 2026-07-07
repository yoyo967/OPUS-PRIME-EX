"""Generischer MCP-Client: verbinde dich mit einem MCP-Server und rufe Tools auf.

Produktionspfad: stdio (der Server laeuft als Subprozess). Die Ergebnis-Extraktion
(ergebnis_aus) ist SDK-frei und testbar; der Verbindungsaufbau nutzt das offizielle SDK.

# SPEC/ADR: opus-deck ADR-0002 (MCP), ADR-0005 (Second Brain als MCP-Server)
"""

from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass(frozen=True)
class MCPServerSpec:
    """Wie ein MCP-Server (als Subprozess) gestartet/erreicht wird."""

    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] | None = None


# Vordefinierter Spec fuer den geteilten Second Brain (stdio-Subprozess).
SECOND_BRAIN = MCPServerSpec(
    command=sys.executable, args=[str(_REPO_ROOT / "scripts" / "brain_serve.py")]
)


def ergebnis_aus(result: Any) -> Any:
    """Nutzbaren Rueckgabewert aus einem CallToolResult extrahieren.

    FastMCP verpackt strukturierte Rueckgaben unter structuredContent['result']; sonst
    werden die Text-Bloecke zusammengefuegt. Dependency-frei (nimmt ein result-Objekt).
    """
    strukturiert = getattr(result, "structuredContent", None)
    if isinstance(strukturiert, dict):
        if set(strukturiert.keys()) == {"result"}:
            return strukturiert["result"]
        return strukturiert
    if strukturiert is not None:
        return strukturiert
    teile: list[str] = []
    for block in getattr(result, "content", None) or []:
        text = getattr(block, "text", None)
        if text is not None:
            teile.append(str(text))
    return "\n".join(teile)


async def call_tool(
    spec: MCPServerSpec, name: str, arguments: dict[str, Any] | None = None
) -> Any:
    """Verbinde dich (stdio) mit dem MCP-Server, rufe ein Tool auf, gib das Ergebnis zurueck."""
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    params = StdioServerParameters(
        command=spec.command, args=list(spec.args), env=spec.env
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.call_tool(name, arguments or {})
            return ergebnis_aus(result)


def call_tool_sync(
    spec: MCPServerSpec, name: str, arguments: dict[str, Any] | None = None
) -> Any:
    """Synchrone Einmal-Bequemlichkeit (spawnt Server, ruft Tool, beendet)."""
    return asyncio.run(call_tool(spec, name, arguments))
