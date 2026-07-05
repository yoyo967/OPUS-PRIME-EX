# COWORK_HANDOFF_BRIEF.md
<!-- Datei 6/8 · Projekt OPUS PRIME EX · Version 1.0 · Stand: 2026-07-05 -->

# Übergabe-Brief an Claude Cowork

## 1. Auftrag an Cowork (eine Zeile)

Reviewe, härte und operationalisiere das Spezifikations-Set von OPUS PRIME EX (7 Dateien) und übergib es implementierungsreif an Claude Code – ohne den fachlichen Scope zu verändern.

## 2. Eingaben

Lade alle 8 Dateien in die Cowork-Session (Ordner `spec/`):
`PROJECT_INSTRUCTIONS.md`, `SYSTEM_PROMPT_OPUS_PRIME_EX.md`, `KNOWLEDGE_ARCHITECTURE.md`, `AGENT_ARCHITECTURE.md`, `CLAUDE.md`, `COWORK_HANDOFF_BRIEF.md` (diese Datei), `FILE_MANIFEST.md`, `NEXT_STEPS.md`.

## 3. Zu simulierende Rollen (Cowork-Arbeitsmodi)

Arbeite die folgenden Rollen **sequenziell** ab; jede Rolle erzeugt ein kurzes Ergebnis-Memo in `review/`:

| Reihenfolge | Rolle | Auftrag | Primär genutzte Dateien | Output |
|---|-------|---------|--------------------------|--------|
| 1 | **Legal Reviewer** (StB/RA-Perspektive) | Prüfe: RDG/StBerG-Abgrenzung wasserdicht? Disclaimer tragfähig? Few-Shots fachlich korrekt (insb. § 19 UStG-Grenzen, Art. 26/99 AI Act, Art. 28/83 DSGVO)? AI-Act-Selbstklassifizierung plausibel? | SYSTEM_PROMPT, AGENT_ARCHITECTURE §6, PROJECT_INSTRUCTIONS §5 | `review/legal_review.md` mit Findings (BLOCKER/MAJOR/MINOR) |
| 2 | **Prompt Engineer** | Härte den System Prompt: Injection-Resistenz, Klarheit der Eskalationslogik, Konsistenz mit Guardrails G1–G8; schlage max. 5 präzise Wortlaut-Änderungen vor | SYSTEM_PROMPT, AGENT_ARCHITECTURE §5 | `review/prompt_review.md` + ggf. `prompts/system_prompt_v1.1.md` |
| 3 | **RAG/Knowledge Engineer** | Verifiziere Quellenliste & Chunking gegen die Muss-Normen-Matrix; ergänze fehlende Muss-Normen je Domäne (Ziel: vollständige Coverage-Liste als YAML) | KNOWLEDGE_ARCHITECTURE | `review/coverage_matrix.yaml` |
| 4 | **QA / Eval Lead** | Erzeuge das Golden-Set-Gerüst: 120 Fälle (20 je Domäne) als YAML mit Feldern `frage`, `erwartete_normen[]`, `erwartete_eskalationsstufe`, `verbotene_inhalte[]`; markiere 12 davon als `smoke: true` | SYSTEM_PROMPT §2, CLAUDE.md §4–5 | `evals/golden_set/*.yaml` (Entwurf, zur menschlichen Prüfung) |
| 5 | **Architecture Gatekeeper** | Konsistenz-Schlussprüfung aller Dateien (Widerspruchsfreiheit, Trace-Fähigkeit); friere `spec/` ein und berechne `spec_hashes.json` | alle | `review/gate_report.md` + `spec/spec_hashes.json` |

**Konfliktregel:** Findings der Rollen 1–4 mit Stufe BLOCKER müssen vor Rolle 5 durch den Owner (Yahya) entschieden werden. Cowork ändert Spezifikationsinhalte nie eigenmächtig bei BLOCKERn – nur Vorschläge.

## 4. Arbeitsregeln in Cowork

1. **Scope-Treue:** Kein neues Feature, keine neue Domäne ohne Owner-Entscheid; alles Neue landet in `spec/OPEN_QUESTIONS.md`.
2. **Menschliche Prüfung:** Golden-Set-Entwürfe und der Disclaimer-Wortlaut sind explizit als „zur menschlichen Fachprüfung" gekennzeichnet (PROJECT_INSTRUCTIONS O3, A3).
3. **Keine Live-Aktionen:** Cowork versendet nichts, published nichts und ruft keine externen Behörden-/Kanzlei-Systeme auf; reine Dokumentenarbeit im Session-Ordner.
4. **Ergebnisformat:** Alle Memos kurz (≤ 1 Seite), Findings als Tabelle mit Referenz auf Datei+Abschnitt.

## 5. Checkliste: Übergabe Cowork → Claude Code

Erst wenn **alle** Punkte abgehakt sind, startet die Implementierung:

- [ ] `review/legal_review.md`: keine offenen BLOCKER
- [ ] System Prompt final (v1.0 oder v1.1) in `prompts/`, Hash in `spec/spec_hashes.json`
- [ ] `review/coverage_matrix.yaml` vollständig (alle Muss-Normen je Domäne gelistet)
- [ ] Golden-Set-Gerüst vorhanden, 12 Smoke-Fälle markiert
- [ ] `spec/OPEN_QUESTIONS.md` angelegt (auch wenn leer)
- [ ] `review/gate_report.md`: Konsistenz bestätigt, `spec/` eingefroren
- [ ] Owner-Freigabe dokumentiert (Name, Datum, Commit-/Versionsstand)
- [ ] Startanweisung an Claude Code: „Implementiere gemäß `CLAUDE.md` im Repo-Root; beginne mit Repo-Skeleton, `config/models.yaml` (Modell-IDs gegen Anthropic-Doku verifizieren), dann `src/tools/steuer_rechner` inkl. Tests."

## 6. Annahmen & offene Punkte

- A1: Cowork hat Dateisystem-Zugriff auf den Session-Ordner und kann die Ordnerstruktur `spec/ · review/ · prompts/ · evals/` anlegen.
- A2: Der Owner nimmt zwischen Rolle 4 und 5 mindestens einmal aktiv Findings ab (asynchron möglich).
- O1: Ob ein realer StB/RA das Legal-Review zusätzlich gegenzeichnet (empfohlen, siehe PROJECT_INSTRUCTIONS O3), entscheidet der Owner vor Go-Live – für den Cowork→Code-Handoff ist es nicht blockierend, für den Produktivstart schon.
