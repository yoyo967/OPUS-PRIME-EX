# FILE_MANIFEST.md
<!-- Datei 7/8 · Projekt OPUS PRIME EX · Version 1.2 · Stand: 2026-07-06 -->
<!-- v1.1 (Owner-Entscheid 2026-07-05): Markenrecht als Domäne 7. Geänderte Dateien: PROJECT_INSTRUCTIONS v1.1,
     SYSTEM_PROMPT_OPUS_PRIME_EX v1.1, KNOWLEDGE_ARCHITECTURE v1.1, AGENT_ARCHITECTURE v1.1, CLAUDE.md v1.1.
     Neue Folge-Artefakte: prompts/system_prompt_v1.2.md (produktiv, Hash in spec_hashes.json),
     evals/golden_set/markenrecht.yaml (20 Fälle, 2 Smoke → Gesamt 140/14), coverage_matrix.yaml v1.1 (Markenrecht-Block).
     Gatekeeper-Nachtrag: review/gate_report.md, Abschnitt "Nachtrag v1.1". -->
<!-- v1.2 (Owner-Entscheide 2026-07-06): PROJECT_INSTRUCTIONS v1.2 (§5 Nr. 9 Non-Goal Kreditwürdigkeit; §7 O1
     entschieden = SHK Berlin), CLAUDE.md v1.2 (§3 temperature-Parametrisierung). Reine Doku/Governance —
     KEIN Prompt-/Code-Twin geändert, prompts/system_prompt_v1.2.md-Hash bleibt gültig. OPEN_QUESTIONS #2/#7/#10
     erledigt. Gatekeeper-Nachtrag: review/gate_report.md, Abschnitt "Nachtrag v1.2". -->
<!-- v1.3 (2026-07-06): AGENT_ARCHITECTURE v1.2 — G5 technische Redaktion (redigiere_pii_g5, im Orchestrator
     aktiv; config/guardrails.yaml modus: redaktion). Erledigt OPEN_QUESTIONS #3 / Legal-Review #4.
     Prompt-Hash unverändert. Gatekeeper-Nachtrag: review/gate_report.md "Nachtrag v1.3". -->

# Manifest aller Projekt-Artefakte

| # | Datei | Zweck | Zielort im Repo | Abhängigkeiten (liest/wird gelesen von) |
|---|-------|-------|-----------------|------------------------------------------|
| 1 | `PROJECT_INSTRUCTIONS.md` | Projektüberblick, Perfect-Twin-Prinzip, Definition of Done, Scope-Abgrenzung | `spec/` | Referenzrahmen für alle anderen Dateien; DoD wird von CLAUDE.md §7 und Eval-Harness gespiegelt |
| 2 | `SYSTEM_PROMPT_OPUS_PRIME_EX.md` | Produktiver System Prompt + Few-Shots | `spec/`; Prompt-Wortlaut zusätzlich als `prompts/system_prompt_v1.md` | Muss konsistent sein mit AGENT_ARCHITECTURE §5 (Guardrails) und §2 (Eskalation); Hash-geprüft durch spec_lint (CLAUDE.md §1) |
| 3 | `KNOWLEDGE_ARCHITECTURE.md` | Quellenkorpus, Versionierung, RAG-, Chunking- & Metadaten-Strategie | `spec/` | Implementiert durch `src/rag/` + `config/sources.yaml`; Coverage-Matrix aus Cowork-Rolle 3 |
| 4 | `AGENT_ARCHITECTURE.md` | Modell-Routing, Tools, Permission-Modell, Guardrails G1–G8, Compliance des Agenten | `spec/` | Implementiert durch `src/router/ · src/orchestrator/ · src/tools/ · src/guardrails/`; Tool-Abschnitte 1:1 gespiegelt in Code (spec_lint-Regel 2) |
| 5 | `CLAUDE.md` | Engineering-Guide: Repo-Struktur, Standards, Tests, CI/CD, Konsistenzregeln | **Repo-Root** (nicht `spec/`) | Liest alle Spec-Dateien; erzwingt Traceability via `scripts/spec_lint.py` |
| 6 | `COWORK_HANDOFF_BRIEF.md` | Rollenplan & Checkliste für Cowork sowie Handoff Cowork→Code | `spec/` | Erzeugt `review/*`, `spec/spec_hashes.json`, Golden-Set-Gerüst in `evals/golden_set/` |
| 7 | `FILE_MANIFEST.md` | Diese Übersicht | `spec/` | Muss bei jeder Spec-Änderung mitgepflegt werden (Gatekeeper-Rolle prüft) |
| 8 | `NEXT_STEPS.md` | Exakte Einspiel-Reihenfolge für den Nutzer (Chat → Cowork → Claude Code) | `spec/` (nur bis P3, danach archivierbar) | Verweist auf COWORK_HANDOFF_BRIEF §5 |

## Von Cowork/Code zu erzeugende Folge-Artefakte (Soll-Liste)

| Artefakt | Erzeuger | Zielort |
|----------|----------|---------|
| `review/legal_review.md`, `review/prompt_review.md`, `review/gate_report.md` | Cowork (Rollen 1, 2, 5) | `review/` |
| `review/legal_review_markenrecht_addendum.md` (v1.1-Erweiterung, Normzitate live-verifiziert; menschliche Gegenzeichnung vor Go-Live ausstehend) | Spec-Erweiterung v1.1 (analog Rolle 1) | `review/` |
| `review/coverage_matrix.yaml` | Cowork (Rolle 3) | `review/` |
| `evals/golden_set/*.yaml` (140 Fälle, 14 Smoke; davon markenrecht.yaml aus Spec-Erweiterung v1.1) | Cowork (Rolle 4) bzw. v1.1-Erweiterung, menschlich geprüft | `evals/golden_set/` |
| `spec/spec_hashes.json`, `spec/OPEN_QUESTIONS.md` | Cowork (Rolle 5) | `spec/` |
| Repo-Code, Tests, `config/*.yaml`, CI-Pipeline, `docs/ai-act-assessment.md` | Claude Code | gemäß CLAUDE.md §2 |

## Integritätsregeln

1. Änderungen an Datei 1–4 erfordern: neue Versionsnummer im Dateikopf, Aktualisierung dieses Manifests, Neuberechnung `spec_hashes.json`, erneuter Gatekeeper-Lauf.
2. Kein Artefakt außerhalb dieser Liste darf als „Spezifikation" behandelt werden (Schutz vor Spec-Drift durch Chat-Verläufe).
