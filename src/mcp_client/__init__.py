"""MCP-Client — die Client-Seite des Rueckgrats.

Verbindet sich mit BELIEBIGEN MCP-Servern (der Second Brain, ein anderer Agent, jeder
MCP-Server) und ruft deren Tools auf. Damit kann OPUS PRIME EX (oder jeder Agent) das
geteilte Gehirn und weitere Faehigkeiten konsumieren — ein Standard, viele Server.

Das mcp-SDK ist optionales Extra [mcp] und wird lazy importiert; die Ergebnis-Extraktion
(ergebnis_aus) ist dependency-frei und offline testbar.

# ADR: opus-deck/docs/adr/ADR-0002 (ACP/MCP-Rueckgrat), ADR-0005 (Second Brain)
"""

from src.mcp_client.client import (
    SECOND_BRAIN,
    MCPServerSpec,
    call_tool,
    call_tool_sync,
    ergebnis_aus,
)

__all__ = [
    "SECOND_BRAIN",
    "MCPServerSpec",
    "call_tool",
    "call_tool_sync",
    "ergebnis_aus",
]
