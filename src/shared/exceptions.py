"""Typed exceptions for OPUS PRIME EX.

# SPEC: CLAUDE.md §3 (Error handling: no silent catches; guardrail failures raise
# typed exceptions that the orchestrator turns into user-safe messages)
"""

from __future__ import annotations


class OpusPrimeError(Exception):
    """Base class for all OPUS PRIME EX errors."""


class ToolInputError(OpusPrimeError):
    """Raised when a tool receives invalid input (user-safe message required)."""


class ParameterNotFoundError(OpusPrimeError):
    """Raised when no versioned legal parameter matches the requested rechtsjahr.

    # SPEC: CLAUDE.md §6 (never hardcode legal parameters; missing table entry
    # must fail loudly instead of falling back to invented values)
    """


class GuardrailViolationError(OpusPrimeError):
    """Raised when a guardrail (G1-G8) blocks a response.

    # SPEC: AGENT_ARCHITECTURE.md §5
    """
