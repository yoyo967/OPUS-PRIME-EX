"""CLI for the eval harness: `python -m evals.harness.run [--smoke] [--out FILE]`.

# SPEC: CLAUDE.md §5 (eval-smoke: Smoke-Subset auf jedem PR; volles Golden Set
# nightly und vor jedem Release-Tag)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from evals.harness.harness import FakeGoldenLLM, run_eval
from src.rag.chunker import Chunk


def _leere_rag_suche(anfrage: str, domaenen: tuple[str, ...]) -> list[Chunk]:
    """No corpus ingested yet -> empty retrieval (Ingest-Livebetrieb folgt)."""
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OPUS PRIME EX Eval-Harness")
    parser.add_argument("--smoke", action="store_true", help="nur smoke:true-Faelle")
    parser.add_argument("--out", type=Path, default=None, help="Report-JSON-Datei")
    parser.add_argument(
        "--model",
        default="fake",
        choices=["fake"],
        help="'fake' = Struktur-/Guardrail-Pruefung; Live-Modelle ab Gateway-Meilenstein",
    )
    args = parser.parse_args(argv)

    report = run_eval(
        llm=FakeGoldenLLM(),
        rag_suche=_leere_rag_suche,
        model_label=args.model,
        smoke_only=args.smoke,
    )
    if args.out:
        args.out.write_text(report.to_json(), encoding="utf-8")
    print(
        f"[eval] {report.anzahl_faelle} Faelle | disclaimer_rate={report.disclaimer_rate:.2f} "
        f"| normen_erwaehnt={report.normen_erwaehnt_rate:.2f} "
        f"| manuell_offen={report.manuell_offen}"
    )
    print(f"[eval] prompt={report.prompt_file} sha256={report.prompt_sha256[:12]}...")
    print(f"[eval] {report.hinweis}")
    # Hartes Gate schon jetzt: Disclaimer-Praesenz muss 100 % sein
    # (SPEC: PROJECT_INSTRUCTIONS.md §4 / CLAUDE.md §4.5 "must be 100%").
    if report.disclaimer_rate < 1.0:
        print("[eval] FEHLGESCHLAGEN: disclaimer_rate < 100 %", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
