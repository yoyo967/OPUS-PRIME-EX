"""Spec-Lint: verifies that the implementation twin matches the spec twin.

CI-blocking. Checks per CLAUDE.md §1 (Spec Traceability):
  1. Productive prompt SHA-256 matches spec/spec_hashes.json (which names the
     authoritative prompt file, currently prompts/system_prompt_v1.2.md).
  2. Every tool module in src/tools/ has a matching section in
     AGENT_ARCHITECTURE.md §3.
  3. Guardrails G1-G8 each map to at least one test in tests/guardrails/.
     Conservative interpretation: enforced as soon as src/guardrails/ contains
     implementation modules; until then reported as PENDING (guardrail milestone
     not started), since untestable-because-unimplemented must not block the
     preceding milestones (SPEC: CLAUDE.md §1 note in repo history).

# SPEC: CLAUDE.md §1 (scripts/spec_lint.py, CI-blocking)
# SPEC: PROJECT_INSTRUCTIONS.md §2.4 (Drift-Kontrolle)
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GUARDRAIL_IDS = [f"G{n}" for n in range(1, 9)]


def check_prompt_hash() -> list[str]:
    """Check 1: prompt file hash matches spec/spec_hashes.json."""
    hashes_path = REPO_ROOT / "spec" / "spec_hashes.json"
    data = json.loads(hashes_path.read_text(encoding="utf-8"))
    prompt_path = REPO_ROOT / str(data["prompt_file"])
    if not prompt_path.exists():
        return [f"FEHLER: Prompt-Datei fehlt: {data['prompt_file']}"]
    actual = hashlib.sha256(prompt_path.read_bytes()).hexdigest()
    expected = str(data["sha256"])
    if actual != expected:
        return [
            f"FEHLER: SHA-256-Drift in {data['prompt_file']}: "
            f"erwartet {expected}, tatsaechlich {actual}. "
            f"Prompt-Aenderungen erfordern Spec-Update im selben Commit (CLAUDE.md §1)."
        ]
    return []


def check_tool_sections() -> list[str]:
    """Check 2: every tool module has a section in AGENT_ARCHITECTURE.md §3."""
    arch = (REPO_ROOT / "spec" / "AGENT_ARCHITECTURE.md").read_text(encoding="utf-8")
    spec_tools = set(re.findall(r"### 3\.\d+ `(\w+)`", arch))
    errors: list[str] = []
    tools_dir = REPO_ROOT / "src" / "tools"
    for module in sorted(tools_dir.glob("*.py")):
        if module.stem.startswith("_"):
            continue
        if module.stem not in spec_tools:
            errors.append(
                f"FEHLER: Tool '{module.stem}' ohne Abschnitt in AGENT_ARCHITECTURE.md §3 "
                f"(neue Tools brauchen erst Spec, dann Code - CLAUDE.md §6)."
            )
    return errors


def check_guardrail_tests() -> tuple[list[str], list[str]]:
    """Check 3: G1-G8 each map to >= 1 test in tests/guardrails/ (once implemented)."""
    guardrails_dir = REPO_ROOT / "src" / "guardrails"
    impl_modules = [
        p for p in guardrails_dir.glob("*.py") if p.stem != "__init__"
    ]
    if not impl_modules:
        return [], [
            "PENDING: src/guardrails/ noch ohne Implementierung - Guardrail-Test-Pflicht "
            "(CLAUDE.md §1 Regel 3) wird ab dem Guardrail-Meilenstein erzwungen."
        ]
    tests_dir = REPO_ROOT / "tests" / "guardrails"
    test_text = "\n".join(
        p.read_text(encoding="utf-8") for p in tests_dir.glob("test_*.py")
    )
    errors = [
        f"FEHLER: Guardrail {gid} ohne Test in tests/guardrails/ (CLAUDE.md §1 Regel 3)."
        for gid in GUARDRAIL_IDS
        if gid not in test_text
    ]
    return errors, []


def main() -> int:
    errors: list[str] = []
    warnings: list[str] = []
    errors += check_prompt_hash()
    errors += check_tool_sections()
    g_errors, g_warnings = check_guardrail_tests()
    errors += g_errors
    warnings += g_warnings

    for warning in warnings:
        print(f"[spec-lint] {warning}")
    for error in errors:
        print(f"[spec-lint] {error}", file=sys.stderr)
    if errors:
        print(f"[spec-lint] FEHLGESCHLAGEN ({len(errors)} Fehler).", file=sys.stderr)
        return 1
    print("[spec-lint] OK - Implementierungs-Zwilling konsistent mit Spezifikation.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
