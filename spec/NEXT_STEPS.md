# NEXT_STEPS.md
<!-- Datei 8/8 · Projekt OPUS PRIME EX · Version 1.0 · Stand: 2026-07-05 -->

# Nächste Schritte: Einspielen der Artefakte (exakte Reihenfolge)

## Schritt 1 – Lokal sichern & versionieren (heute)
1. Alle 8 Dateien aus diesem Chat herunterladen.
2. Lokales Git-Repo `opus-prime-ex` anlegen; Dateien 1–4, 6–8 nach `spec/`, `CLAUDE.md` in den Repo-Root.
3. Initial-Commit: `spec: OPUS PRIME EX v1.0 (Fable-5-generiert)`.

## Schritt 2 – Claude Cowork (Phase P2)
1. Neue Cowork-Session öffnen, Arbeitsordner = das Repo (bzw. die 8 Dateien in einen Session-Ordner `spec/` legen).
2. Startanweisung an Cowork (wörtlich verwendbar):
   > „Lies `spec/COWORK_HANDOFF_BRIEF.md` und führe die Rollen 1–5 in der dort definierten Reihenfolge aus. Halte dich an die Arbeitsregeln in Abschnitt 4. Stoppe nach Rolle 4 und lege mir alle BLOCKER-Findings zur Entscheidung vor."
3. BLOCKER-Findings entscheiden (du als Owner), dann Cowork Rolle 5 (Gatekeeper) ausführen lassen.
4. Prüfen: Checkliste in `COWORK_HANDOFF_BRIEF.md` §5 vollständig abgehakt? `spec/` eingefroren, `spec_hashes.json` vorhanden?
5. Ergebnis committen: `review: Cowork P2 abgeschlossen, spec eingefroren`.

## Schritt 3 – Claude Code (Phase P3)
1. Claude Code im Repo-Root starten (`CLAUDE.md` wird automatisch gelesen).
2. Startanweisung (wörtlich verwendbar, identisch mit Handoff-Brief §5):
   > „Implementiere gemäß `CLAUDE.md`. Beginne mit dem Repo-Skeleton und `config/models.yaml` (Modell-IDs vorab gegen https://docs.claude.com/en/api/overview verifizieren), danach `src/tools/steuer_rechner` inklusive Tests, dann RAG-Ingest mit den Fixtures, dann Router, Orchestrator, Guardrails G1–G8, zuletzt Eval-Harness."
3. Nach jedem Meilenstein: CI grün? Spec-Lint grün? Erst dann weiter.
4. Vor Release: vollständiges Golden-Set-Eval laufen lassen; Ergebnis gegen `PROJECT_INSTRUCTIONS.md` §4 (Definition of Done) abgleichen.

## Schritt 4 – Menschliche Abnahme (Phase P4, vor Go-Live Pflicht)
1. Disclaimer-Wortlaut durch zugelassenen Rechtsanwalt freigeben lassen (PROJECT_INSTRUCTIONS O3).
2. Golden Set durch Fachreviewer (StB/RA) gegenzeichnen lassen (A3).
3. `docs/ai-act-assessment.md` (Art.-50-Transparenz, Selbstklassifizierung) und DSGVO-Unterlagen (VVT, AVV, TOMs) final prüfen.
4. Abnahmeprotokoll gegen Definition of Done erstellen → Go-Live-Entscheid.

## Kurzübersicht

| Schritt | Werkzeug | Dauer (Schätzung) | Blockierend für nächsten Schritt |
|---------|----------|-------------------|----------------------------------|
| 1 | lokal/Git | 15 min | ja |
| 2 | Claude Cowork | 0,5–1 Tag | ja (Checkliste §5) |
| 3 | Claude Code | 3–7 Tage iterativ | ja (CI + Eval) |
| 4 | Mensch (RA/StB) | parallel zu 3 startbar | ja für Go-Live |
