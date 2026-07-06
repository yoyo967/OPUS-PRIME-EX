"""G8 Audit-Trail: full traceability without PII.

# SPEC: AGENT_ARCHITECTURE.md §5 G8 (Anfrage-Hash, Route, Tools, Quellen-IDs,
# Guardrail-Ereignisse); CLAUDE.md §3 (no PII in logs - hash user IDs)
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence
from dataclasses import asdict
from datetime import UTC, datetime

from src.guardrails.events import GuardrailEvent


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def create_audit_record(
    anfrage: str,
    user_id: str,
    route: str,
    risiko_score: int,
    tools: Sequence[str],
    quellen_ids: Sequence[str],
    events: Sequence[GuardrailEvent],
) -> dict[str, object]:
    """Build one audit-trail record; contains hashes, never raw request or user ID."""
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "anfrage_hash": _sha256(anfrage),
        "user_id_hash": _sha256(user_id),
        "route": route,
        "risiko_score": risiko_score,
        "tools": list(tools),
        "quellen_ids": list(quellen_ids),
        "guardrail_events": [asdict(e) for e in events],
    }
