# review/gate_report.md
<!-- Cowork-Rolle 5: Architecture Gatekeeper · Projekt OPUS PRIME EX · 2026-07-05 -->

## Konsistenz-Schlussprüfung

| Prüfpunkt | Ergebnis |
|---|---|
| SYSTEM_PROMPT_OPUS_PRIME_EX.md vs. AGENT_ARCHITECTURE.md §5 (Guardrails) | Konsistent nach Übernahme der 5 Prompt-Änderungen (`prompts/system_prompt_v1.1.md`); verbleibende Lücken (G2-Erweiterung, G5-Durchsetzung) sind in `spec/OPEN_QUESTIONS.md` #2/#3 dokumentiert und für Claude Code als Arbeitsauftrag markiert, kein Widerspruch zur Spec. |
| SYSTEM_PROMPT vs. AGENT_ARCHITECTURE §2 (Eskalation) | Konsistent; Änderung #5 (Querverweis statt "hohe Beträge") beseitigt die einzige gefundene Divergenz. |
| PROJECT_INSTRUCTIONS.md §5 (Scope) vs. SYSTEM_PROMPT (Auftrag und Grenzen) | Konsistent; BLOCKER-Risiko (Legal Review #1) ist keine Divergenz zwischen den Dateien, sondern ein Restrisiko der gemeinsamen Formulierung – durch Owner-Entscheid adressiert. |
| KNOWLEDGE_ARCHITECTURE.md §2/§7 vs. review/coverage_matrix.yaml | Konsistent; Coverage-Matrix konkretisiert die in KNOWLEDGE_ARCHITECTURE nur pauschal benannten Quellen zu einer prüfbaren Muss-Normen-Liste je Domäne (120 Normen/Themen über 6 Domänen). |
| CLAUDE.md §1 (Spec Traceability) vs. tatsächliche Artefakte | Erfüllbar: `spec/spec_hashes.json` verweist auf `prompts/system_prompt_v1.1.md`; Tool-Sektionen in AGENT_ARCHITECTURE.md §3 sind 1:1 mit den in CLAUDE.md §2 gelisteten `src/tools/`-Modulen benennbar; Guardrails G1–G8 sind vollständig in AGENT_ARCHITECTURE.md §5 enumeriert (Testabdeckung ist P3-Aufgabe). |
| Golden-Set (evals/golden_set/*.yaml) vs. CLAUDE.md §4.5 Anforderung | Erfüllt: 120 Fälle, 20 je Domäne, 12 als smoke:true markiert, Felder `frage/erwartete_normen/erwartete_eskalationsstufe/verbotene_inhalte` vorhanden. |
| FILE_MANIFEST.md Zielorte | Erfüllt: alle 7 Spec-Dateien in `spec/`, `CLAUDE.md` im Repo-Root, Folge-Artefakte in `review/`, `prompts/`, `evals/golden_set/`. |

## BLOCKER-Status

Der einzige BLOCKER (`review/legal_review.md` #1) ist durch Owner-Entscheid (Yahya Yildirim, 2026-07-05) aufgelöst: Formulierungsvorschlag aus `prompts/system_prompt_v1.1.md` übernommen, Few-Shot Beispiel 1 reformuliert. Damit bestehen **keine offenen BLOCKER** mehr für den Handoff Cowork → Claude Code.

## Checkliste COWORK_HANDOFF_BRIEF.md §5

- [x] `review/legal_review.md`: keine offenen BLOCKER (siehe oben)
- [x] System Prompt final (v1.1) in `prompts/`, Hash in `spec/spec_hashes.json`
- [x] `review/coverage_matrix.yaml` vollständig (alle Muss-Normen je Domäne gelistet, Status `pending_ingest` bis Ingest in P3)
- [x] Golden-Set-Gerüst vorhanden, 12 Smoke-Fälle markiert
- [x] `spec/OPEN_QUESTIONS.md` angelegt (8 Einträge, davon 1 durch Owner entschieden, 7 offen/nicht-blockierend)
- [x] `review/gate_report.md`: Konsistenz bestätigt, `spec/` eingefroren (siehe unten)
- [x] Owner-Freigabe dokumentiert
- [x] Startanweisung an Claude Code vorbereitet (unverändert aus COWORK_HANDOFF_BRIEF §5 Punkt 8, siehe NEXT_STEPS.md Schritt 3)

## Owner-Freigabe

- **Name:** Yahya Yildirim
- **Datum:** 2026-07-05
- **Entscheidung:** BLOCKER #1 – Formulierungsvorschlag übernommen
- **Commit-/Versionsstand:** siehe `git log` – dieser Report ist Teil des Freeze-Commits (Hash wird in `spec/spec_hashes.json.frozen_at_commit` nachgetragen)

## Spec-Freeze

Ab diesem Commit gilt `spec/` (inkl. `prompts/system_prompt_v1.1.md`, `review/*`, `evals/golden_set/*`) als eingefroren für den Handoff an Claude Code. Änderungen erfordern erneuten Durchlauf der Integritätsregeln aus `FILE_MANIFEST.md` ("Von Cowork/Code zu erzeugende Folge-Artefakte") und ggf. erneute Gatekeeper-Prüfung.

---

## Nachtrag v1.1 — Markenrecht als Domäne 7 (2026-07-05)

**Auslöser:** Owner-Entscheid (Yahya Yildirim, 2026-07-05): Markenrecht wird als siebte Domäne ergänzt. Der Freeze v1.0 wurde dafür gemäß Integritätsregeln `FILE_MANIFEST.md` geöffnet und mit diesem Nachtrag erneut geschlossen.

| Prüfpunkt | Ergebnis |
|---|---|
| Versionierung | Dateien 1–5 (PROJECT_INSTRUCTIONS, SYSTEM_PROMPT, KNOWLEDGE_ARCHITECTURE, AGENT_ARCHITECTURE, CLAUDE.md) auf v1.1; Manifest v1.1; Änderungsvermerk je Dateikopf. |
| Konsistenz „sieben Domänen" | Domänen-Tabelle (PROJECT_INSTRUCTIONS §1), Prompt-ROLLE (v1.2), Query-Analyse-Domänenliste (KNOWLEDGE_ARCHITECTURE §4.1), Routing-Beispiele (AGENT_ARCHITECTURE §2) durchgängig. |
| Scope/RDG | Neue Abgrenzungen: keine Einreichung/Vertretung vor DPMA/EUIPO/WIPO (§5 Nr. 4), keine Verfügbarkeitsgarantie bei Recherchen (§5 Nr. 8); gespiegelt in Prompt v1.2 (AUFTRAG UND GRENZEN), G2-Beispielen und dokument_generator-Sperre. |
| Prompt | `prompts/system_prompt_v1.2.md` = v1.1-Härtungen + 5 Markenrecht-Änderungen (Changelog in der Datei); Hash in `spec/spec_hashes.json` aktualisiert. Kein neues Few-Shot (bewusst, bis Legal-Review-Addendum: OPEN_QUESTIONS #9). |
| Coverage-Matrix | v1.1: +22 Markenrecht-Einträge (MarkenG, UMV, VO 608/2013, Nizza, Amts-Leitlinien), alle `pending_ingest`; UMV-Artikelnummern beim Ingest zu verifizieren. |
| Golden Set | `markenrecht.yaml`: 20 Fälle, 2 Smoke → Gesamt **140 Fälle / 14 Smoke** (PROJECT_INSTRUCTIONS §4 und CLAUDE.md entsprechend angepasst). |
| Reviews | **Einschränkung:** Legal-/Prompt-Review (Rollen 1–2) haben die Markenrecht-Inhalte nicht geprüft — als Pflicht-Nachtrag vor Go-Live in `spec/OPEN_QUESTIONS.md` #9 erfasst. Für den P3-Implementierungsstart nicht blockierend (analog Findings #2–#5). |
| COWORK_HANDOFF_BRIEF.md | Unverändert (historisches P2-Arbeitsdokument, beschreibt den durchgeführten 6-Domänen-Review; Delta dokumentiert dieser Nachtrag). |

**Owner-Freigabe v1.1:** Yahya Yildirim, 2026-07-05 (Anweisung „Markenrecht hinzufügen"). **Re-Freeze:** ab dem Commit dieses Nachtrags; Hash-Stand siehe `spec/spec_hashes.json`.

---

## Nachtrag v1.2 — Owner-Entscheide #2/#7/#10 (2026-07-06)

**Auslöser:** Owner-Entscheide (Yahya Yildirim, 2026-07-06) zu drei offenen Punkten aus `spec/OPEN_QUESTIONS.md`. Reine Doku-/Governance-Änderung — **kein Prompt-, Tool-, Golden-Set- oder Coverage-Twin berührt.**

| Punkt | Entscheid | Umsetzung |
|---|---|---|
| #2 (Legal-Review #3) | Non-Goal „keine Verwendung von Berechnungsergebnissen für Kreditvergabe-/Bonitätsentscheidungen Dritter" aufnehmen | PROJECT_INSTRUCTIONS.md v1.2 §5 **Nr. 9**; stützt die AI-Act-Selbstklassifizierung (Anhang III Nr. 5) in `docs/ai-act-assessment.md` |
| #10 | temperature-Parametrisierung bestätigt (API lehnt Sampling auf Sonnet 5 / Fable 5 ab) | CLAUDE.md v1.2 §3 redaktionell nachgezogen (Route A/B ohne temperature, Route C 0.0); deckt sich mit `config/models.yaml` |
| #7 | Branchen-Erstfokus = **SHK/Heizung-Sanitär Berlin** | PROJECT_INSTRUCTIONS.md v1.2 §7 O1 entschieden; Wissensbasis-Priorisierung entsprechend |

**Konsistenzprüfung:**
- Prompt `prompts/system_prompt_v1.2.md` **unverändert** → SHA-256 in `spec/spec_hashes.json` weiterhin gültig, kein Prompt-Re-Freeze nötig. (Der Kreditwürdigkeits-Non-Goal ist eine Scope-Dokumentation; die generelle RDG/StBerG-Selbstbegrenzung im Prompt deckt das Verhalten bereits ab.)
- Versionsstände gezogen: PROJECT_INSTRUCTIONS v1.2, CLAUDE.md v1.2, FILE_MANIFEST v1.2.
- OPEN_QUESTIONS #2 (Non-Goal-Teil), #7, #10 auf „erledigt/entschieden"; #2-Rest (Fachreviewer-Bestätigung) bleibt P4-Pflicht.
- spec_lint bleibt grün (Prompt-Hash, Tool-Sektionen, Guardrail-Tests unverändert).

**Owner-Freigabe v1.2:** Yahya Yildirim, 2026-07-06. **Stand eingefroren** ab dem Commit dieses Nachtrags.

---

## Nachtrag v1.3 — G5 technische Redaktion (OPEN_QUESTIONS #3, 2026-07-06)

**Auslöser:** Umsetzung von Legal-Review #4 / OPEN_QUESTIONS #3 im Zuge der Bug-/Feature-Runde. G5 war bislang nur hinweisgebend; PROJECT_INSTRUCTIONS §5.7 verlangt aber das Designziel „keine Verarbeitung von Art.-9-Daten".

| Prüfpunkt | Ergebnis |
|---|---|
| Spec-Änderung | AGENT_ARCHITECTURE.md §5 G5 auf **v1.2**: technische Redaktion ergänzt (Platzhalter statt Klartext vor Retrieval/Modell), zusätzlich Nutzerhinweis. |
| Implementierung | `redigiere_pii_g5` (src/guardrails/pre.py) redigiert Art.-9-Signalwörter; der Orchestrator nutzt die redigierte Anfrage (`anfrage_modell`) für Retrieval, Zahlen-Provenienz und Modell — die Original-Anfrage geht nur in G2 (Scope) und den gehashten Audit-Eintrag. |
| Konfiguration | config/guardrails.yaml `g5_pii_filter.modus: redaktion`. |
| Tests | Redaktions-Tests in tests/guardrails (G5) + tests/orchestrator (redigierte Anfrage erreicht das Modell nicht im Klartext). |
| Prompt | **unverändert** → SHA-256 in spec_hashes.json weiterhin gültig, kein Prompt-Re-Freeze. |
| spec_lint | grün (G5 weiterhin testabgedeckt). |

**Owner-Freigabe v1.3:** im Rahmen des erteilten grünen Lichts für die Bug-/Feature-Runde (2026-07-06). **Stand eingefroren** ab dem Commit dieses Nachtrags.

---

## Nachtrag v1.4 — Modell-Katalog & Hybrid-Wahl (Owner-Entscheid 2026-07-07)

| Feld | Ergebnis |
|------|----------|
| Änderung | AGENT_ARCHITECTURE §2 (v1.3): User-wählbarer Modell-Katalog, Modell entkoppelt von Route. `config/models.yaml` `catalog` (alle Claude-Modelle + lokales Gemma 4). Neu: `src/gateway/gemma_client.py` (GemmaLLMClient über Ollama, injizierbarer Opener), `config.ModelProfile`/`list_models`/`resolve_model`/`default_model_id`, `AnthropicLLMClient` Profil-Pfad, `build_llm_client(model_id)`-Fabrik. |
| Rationale | Hybrid Anthropic ↔ lokal. Lokales Gemma: keine API-Kosten, kein Datenabfluss (EU-first/DSGVO, analog lokale Embeddings). Owner-Vorgabe: alle Anthropic-Modelle zur Wahl + Gemma 4; Start CPU/32 GB, GPU (GCP) später. |
| Tests | tests/gateway: Katalog, Anthropic-Profil-Pfad (Opus/Fable/Haiku), GemmaLLMClient (Fake-Opener + Fehlerpfad), Fabrik (gemma → GemmaLLMClient, Orchestrator-Protokoll). 227 Tests grün. |
| Guardrails | unverändert — Modellwechsel läuft durch dieselbe Pipeline (Routing/Retrieval/Guardrails G1–G8); Gemma-Antworten werden identisch geprüft. |
| Prompt | **unverändert** → SHA-256 in spec_hashes.json weiterhin gültig, kein Re-Freeze. |
| spec_lint | grün. |
| Offen | Qualität von Gemma gegen das Golden Set messen (DoD-Gate ≥ 95 %) vor Vertrauen für echte Rechtsauskünfte; menschliche RA/StB-Abnahme bleibt Pflicht (modellunabhängig). |

**Owner-Freigabe v1.4:** im Rahmen des erteilten grünen Lichts für die Modell-Hybrid-Funktion (2026-07-07).
