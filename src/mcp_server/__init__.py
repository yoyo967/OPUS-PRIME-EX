"""MCP-Rueckgrat: OPUS PRIME EX exponiert geteilte Faehigkeiten ueber MCP.

Der MCP-Server (server.py, optionales Extra [mcp]) macht Faehigkeiten wie die
Rechtsquellen-Suche fuer BELIEBIGE MCP-Clients verfuegbar (Claude Code, OPUS DECK,
weitere Agenten) — ein Standard, viele Konsumenten. Die Tool-Logik (tools.py) ist
dependency-frei und offline testbar; nur das Ausfuehren des Servers braucht das SDK.

# ADR: opus-deck/docs/adr/ADR-0002 (ACP/MCP), ADR-0005 (Second Brain als MCP-Server)
"""
