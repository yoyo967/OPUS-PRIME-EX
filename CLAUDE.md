# CLAUDE.md
<!-- File 5/8 · Project OPUS PRIME EX · Version 1.2 · Date: 2026-07-06 -->
<!-- v1.1: trademark law (Markenrecht) added as domain 7; golden set ≥140 (20 per domain), smoke subset 14. -->
<!-- v1.2: §3 temperature note aligned to the current Anthropic API (Sonnet 5 / Fable 5 reject sampling params -> Route A/B send no temperature; OPEN_QUESTIONS #10). Owner-confirmed 2026-07-06. -->
<!-- This file lives at the repo root and instructs Claude Code during implementation. -->

# OPUS PRIME EX — Engineering Guide for Claude Code

You are implementing OPUS PRIME EX, a legal/tax-information agent specified in the
`/spec` directory. The spec files are the single source of truth (Perfect Twin
Architecture). **Never implement behavior that contradicts the spec; never silently
extend it.** If a spec gap blocks you, add an entry to `spec/OPEN_QUESTIONS.md` and
choose the most conservative interpretation.

## 1. Spec Traceability (hard rule)

- Spec files live in `spec/`: `PROJECT_INSTRUCTIONS.md`, `SYSTEM_PROMPT_OPUS_PRIME_EX.md`,
  `KNOWLEDGE_ARCHITECTURE.md`, `AGENT_ARCHITECTURE.md`, `COWORK_HANDOFF_BRIEF.md`,
  `FILE_MANIFEST.md`.
- Every module, tool schema, and guardrail carries a doc comment with a trace ID,
  e.g. `// SPEC: AGENT_ARCHITECTURE.md §5 G3 (citation validator)`.
- `scripts/spec_lint.py` (CI-blocking) verifies:
  1. `prompts/system_prompt_v1.md` SHA-256 matches the hash recorded in
     `spec/spec_hashes.json` (regenerate hash only via `make spec-sync`, which
     requires an updated spec file in the same commit).
  2. Every tool in `src/tools/` has a matching section in `AGENT_ARCHITECTURE.md §3`.
  3. Guardrails G1–G8 each map to at least one test in `tests/guardrails/`.

## 2. Repository Structure

```
opus-prime-ex/
├── CLAUDE.md
├── spec/                      # the 7 spec files + spec_hashes.json + OPEN_QUESTIONS.md
├── prompts/
│   ├── system_prompt_v1.md    # verbatim from SYSTEM_PROMPT_OPUS_PRIME_EX.md §1
│   └── few_shots/             # examples from spec §2, one file per domain
├── config/
│   ├── models.yaml            # model IDs & routing thresholds (verify IDs against
│   │                          # https://docs.claude.com/en/api/overview before pinning)
│   ├── guardrails.yaml
│   └── sources.yaml           # corpus sources & update cycles (KNOWLEDGE_ARCHITECTURE §2)
├── src/
│   ├── gateway/               # auth, rate limiting, audit log, PII inbound filter (G5)
│   ├── router/                # Haiku classification + deterministic risk score
│   ├── orchestrator/          # tool loop, escalation logic (never de-escalate)
│   ├── tools/                 # rag_suche, steuer_rechner, fristen_kalender,
│   │                          # dokument_generator, aenderungs_radar (+ phase-2 stubs)
│   ├── guardrails/            # G1–G8 post/pre-processors
│   ├── rag/                   # ingest, chunking, versioning, hybrid retrieval, re-rank
│   └── shared/
├── data/fixtures/             # legal-text fixtures for ingest tests (§19 UStG, Art. 28 GDPR, …)
├── evals/
│   ├── golden_set/            # ≥140 curated cases, 20 per domain (YAML, human-reviewed)
│   └── harness/               # scoring: citation accuracy, disclaimer presence, routing
├── tests/                     # unit + integration + guardrail tests
├── scripts/                   # spec_lint.py, ingest.py, drift_report.py
└── .github/workflows/ci.yaml
```

## 3. Tech Stack & Coding Standards

- **Language:** Python 3.12+ for backend/RAG/tools (typed, `mypy --strict`);
  TypeScript 5+ only if the optional reference web UI (`apps/web/`) is built.
- **Style:** `ruff` (lint + format), Google-style docstrings, no wildcard imports.
- **Domain language:** Code identifiers in English; **domain terms that are legally
  meaningful stay German** (`kleinunternehmer_grenze`, `hebesatz`, `gueltig_ab`) —
  do not translate legal terms, translation loses precision.
- **Determinism first:** All computations with legal effect (tax math, deadlines)
  are pure functions with table-driven parameters under `src/tools/params/`,
  versioned like statutes (`gueltig_ab`/`gueltig_bis`). The LLM never does math.
- **Anthropic API usage:** official Python SDK; tool use via JSON schemas; retries
  with exponential backoff; per-route `max_tokens` budgets from `config/models.yaml`.
  **Sampling params (temperature):** the current API rejects `temperature` on
  `claude-sonnet-5` / `claude-fable-5` (400, sampling removed), so Route A/B send
  **no** `temperature` and steer via adaptive thinking / effort; Route C
  (`claude-haiku-4-5`) keeps `temperature 0.0` for classification. Parametrized per
  AGENT_ARCHITECTURE.md §8 A1; decided in OPEN_QUESTIONS #10 (Owner, 2026-07-06).
- **Error handling:** No silent catches. Guardrail failures raise typed exceptions
  that the orchestrator turns into user-safe messages (never expose stack traces).
- **Secrets:** environment variables only; never commit keys; `.env.example` maintained.
- **Data protection by design:** no PII in logs (hash user IDs); conversation
  retention default 90 days via scheduled purge job; all storage EU-region.

## 4. Testing Requirements (CI-blocking)

1. **Unit tests** (`pytest`, coverage ≥ 85 % on `src/tools/` and `src/guardrails/`):
   - `steuer_rechner`: golden calculations incl. edge cases (Hebesatz 200 minimum,
     §35 EStG cap, Kleinunternehmer boundary at exactly 25,000 € / 100,000 €).
   - `fristen_kalender`: weekend/holiday shifts per Bundesland (§ 108 AO), 72-h
     GDPR breach deadline across weekends.
2. **Ingest tests:** fixtures must chunk to expected boundaries with correct
   metadata (KNOWLEDGE_ARCHITECTURE §7); Muss-Norm coverage matrix must pass.
3. **Guardrail tests:** adversarial cases per guardrail, e.g. prompt injection
   attempting to drop the disclaimer (G1 must still append), fabricated citation
   (G3 must block), free-floating tax figure (G4 must block), request to file a
   tax return (G2 must refuse with escalation template).
4. **Routing tests:** labeled query set → expected route; upward escalation
   allowed, downward forbidden.
5. **Eval harness (`evals/harness`):** runs the golden set against a live or
   recorded model; reports citation accuracy, disclaimer presence (must be 100 %),
   escalation correctness. Gate for release: thresholds from
   PROJECT_INSTRUCTIONS.md §4. Record model ID + prompt hash in every eval report.

## 5. CI/CD Pipeline (`.github/workflows/ci.yaml`)

`lint → typecheck → unit → ingest-fixtures → guardrail-tests → spec_lint → eval-smoke`
- `eval-smoke`: 14-case subset of the golden set on every PR; full golden set
  nightly and before any release tag.
- Deployment: containerized (Docker), staging → production with manual approval;
  infra targets EU regions only; secrets via the platform's secret manager.
- Every release tag freezes: prompt hash, model IDs, corpus snapshot manifest —
  reproducibility of any answer must be possible from these three.

## 6. Consistency Rules During Implementation

- If `SYSTEM_PROMPT_OPUS_PRIME_EX.md` and `AGENT_ARCHITECTURE.md` ever appear to
  conflict, **guardrail/architecture wins for enforcement, prompt wins for tone** —
  and file the conflict in `spec/OPEN_QUESTIONS.md`.
- Never hardcode legal parameters (rates, thresholds, deadlines) in code paths;
  only in versioned parameter tables with source references.
- Any new tool requires: spec section first (Cowork approval), then schema, then
  tests, then implementation.
- German UI/output strings live in `src/shared/i18n/de.yaml` (English fallback
  file maintained in parallel).

## 7. Definition of Done (engineering view)

Mirrors PROJECT_INSTRUCTIONS.md §4. A feature is done when: implemented + traced
to spec + unit/guardrail tests green + eval-smoke unchanged-or-better + docs
updated (`docs/`, incl. `docs/ai-act-assessment.md` when the change touches
classification-relevant behavior).

## 8. Assumptions & Open Points

- A1: Python-first backend assumed; the Owner may swap to TypeScript end-to-end —
  structure and rules translate 1:1.
- A2: Model IDs in `config/models.yaml` are pinned at implementation time after
  verifying current availability in the Anthropic docs.
- A3: Vector store choice is deferred to implementation (must support EU hosting,
  hybrid search, and metadata filtering); wrap it behind `src/rag/store.py`.
- O1: CI provider assumed GitHub Actions; adjust if LYGOX uses GitLab.
