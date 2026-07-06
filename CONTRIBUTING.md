# Contributing to OPUS PRIME EX

Thanks for your interest! This project has a strict engineering discipline because it
handles legal information — please read this before opening a PR.

*(Diese Datei ist bewusst auf Englisch gehalten, dem Standard für Open-Source-Beiträge;
die fachlichen Regeln gelten sprachunabhängig.)*

## Prerequisites & setup

```bash
python -m pip install -e ".[dev]"
```

Python 3.12+. Never commit secrets — `.env` is gitignored; put your `ANTHROPIC_API_KEY`
there (see `.env.example`).

## The four gates (green before every commit)

A change is only mergeable when **all** of these pass locally and in CI:

```bash
python -m ruff check .        # lint & import order
python -m mypy                # strict typing (src, apps, scripts, evals/harness)
python -m pytest -q           # tests
python scripts/spec_lint.py   # spec ↔ implementation consistency (CI-blocking)
```

CI pipeline: `lint → typecheck → unit → ingest-fixtures → guardrail-tests → spec_lint → eval-smoke`.

## Non-negotiable rules

1. **Spec is the source of truth (Perfect Twin).** `spec/` is frozen. Behaviour that is
   not specified must not be implemented, and specified behaviour must not silently
   change. To change behaviour: update the spec first, bump the affected file's version,
   add a *gatekeeper note* in `review/gate_report.md`, and update `spec/FILE_MANIFEST.md`
   per its integrity rules. Prompt changes require a new hash in `spec/spec_hashes.json`.
2. **Determinism first.** Anything with legal effect (tax math, deadlines, thresholds)
   lives in **versioned parameter tables** (`src/tools/params/`, `gueltig_ab`/`gueltig_bis`),
   never hardcoded in code paths. **The LLM never computes and never invents citations.**
3. **Guardrails are load-bearing.** New guardrails (G1–G8) need adversarial tests in
   `tests/guardrails/`; `spec_lint` enforces coverage.
4. **New tool → spec section first, then schema, then tests, then implementation.**
5. **No overclaiming.** Docs and comments must honestly mark what is verified vs. pending.
   If you add a source/model boundary that isn't verified, flag it (see the
   `OPEN_QUESTIONS`-style caveats in the codebase).
6. **Legal boundary.** Nothing may make the agent perform services reserved to attorneys/
   tax advisors (RDG/StBerG). Filing/submission tools stay blocked.

## Commit messages

Use a short type prefix — `feat:`, `fix:`, `docs:`, `spec:`, `test:`, `chore:` — and a
concise imperative summary. Reference the milestone/spec section when relevant.

## Pull requests

- Keep PRs focused; one concern per PR.
- Include tests for new behaviour.
- Confirm the four gates are green and note it in the PR description.
- For anything touching legal parameters or guardrails, describe the source you verified
  against.

## Reporting issues

Use the issue templates. For security or data-protection concerns, follow
[SECURITY.md](SECURITY.md) instead of opening a public issue.
