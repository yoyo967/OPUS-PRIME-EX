"""Second Brain — geteilter, agentengepflegter Wissensspeicher (Karpathy-LLM-Wiki-Muster).

raw/ (unveraenderliche Quellen) · wiki/ (agenten-gepflegte Seiten) · BRAIN.md (Schema).
Menschen und alle Agenten nutzen dasselbe Gehirn ueber MCP (src/brain/server.py).
Retrieval reuset die OPUS-PRIME-EX-RAG-Engine (Hybrid BM25 + optionale Embeddings).

Modular und **extrahierbar** in ein eigenes `opus-brain`-Repo — hier zunaechst neben der
RAG-Engine, die es wiederverwendet.

# ADR: opus-deck/docs/adr/ADR-0005 (Second Brain als MCP-Server).
# Spec: opus-deck/spec/SECOND_BRAIN.md
"""
