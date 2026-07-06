"""Assemble the system prompt (+ few-shots) and the user message for a request.

The productive system prompt is prompts/system_prompt_v1.2.md — the exact file whose
SHA-256 spec_lint verifies. Only the fenced ```markdown block is the prompt itself;
the changelog/few-shot sections after it are documentation. Few-shots and RAG context
are appended per the spec (SYSTEM_PROMPT §2 "<beispiele>", KNOWLEDGE_ARCHITECTURE §4.5).

# SPEC: CLAUDE.md §1 (prompt file hash), §2 (prompts/); SYSTEM_PROMPT_OPUS_PRIME_EX.md
# SPEC: KNOWLEDGE_ARCHITECTURE.md §6 (Zitierkopf im Kontext)
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path

from src.rag.chunker import Chunk
from src.shared.exceptions import OpusPrimeError

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_PROMPT_FILE = _REPO_ROOT / "prompts" / "system_prompt_v1.2.md"
_FEW_SHOTS_DIR = _REPO_ROOT / "prompts" / "few_shots"

_FENCE = re.compile(r"```markdown\n(.*?)\n```", re.DOTALL)


@lru_cache(maxsize=1)
def load_system_prompt(prompt_file: str = str(_PROMPT_FILE)) -> str:
    """Extract the productive prompt text from the fenced block of the v1.2 file."""
    text = Path(prompt_file).read_text(encoding="utf-8")
    match = _FENCE.search(text)
    if match is None:
        raise OpusPrimeError(
            f"Kein ```markdown-Prompt-Block in {prompt_file} gefunden (Spec-Drift?)."
        )
    return match.group(1).strip()


@lru_cache(maxsize=1)
def load_few_shots(few_shots_dir: str = str(_FEW_SHOTS_DIR)) -> str:
    """Concatenate the domain few-shot files into a <beispiele> block."""
    parts: list[str] = []
    for pfad in sorted(Path(few_shots_dir).glob("*.md")):
        if pfad.stem == "README":
            continue
        parts.append(pfad.read_text(encoding="utf-8").strip())
    if not parts:
        return ""
    return "<beispiele>\n" + "\n\n---\n\n".join(parts) + "\n</beispiele>"


def build_system() -> str:
    """Full system content: productive prompt + few-shot examples."""
    prompt = load_system_prompt()
    few_shots = load_few_shots()
    if few_shots:
        return f"{prompt}\n\n{few_shots}"
    return prompt


def _kontext_block(chunks: Sequence[Chunk]) -> str:
    if not chunks:
        return ""
    zeilen = ["<kontext quelle=\"wissensbasis\">"]
    for chunk in chunks:
        zeilen.append(f"[{chunk.zitierkopf()}]")
        zeilen.append(chunk.text.strip())
        zeilen.append("")
    zeilen.append("</kontext>")
    return "\n".join(zeilen)


def build_user_message(
    anfrage: str, chunks: Sequence[Chunk], korrektur_hinweis: str | None
) -> str:
    """User-turn content: retrieval context + the question (+ any correction hint).

    Volatile content stays in the user turn so the system prefix stays cache-stable
    (SPEC: CLAUDE.md §3 retries; prompt-caching best practice).
    """
    teile: list[str] = []
    kontext = _kontext_block(chunks)
    if kontext:
        teile.append(kontext)
    if korrektur_hinweis:
        teile.append(f"[Korrekturhinweis: {korrektur_hinweis}]")
    teile.append(f"Frage: {anfrage}")
    return "\n\n".join(teile)
