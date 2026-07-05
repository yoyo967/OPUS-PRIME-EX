# AGENT_ARCHITECTURE.md
<!-- Datei 4/8 · Projekt OPUS PRIME EX · Version 1.0 · Stand: 2026-07-05 -->

# Technische Architektur OPUS PRIME EX

## 1. Systemüberblick

```
Nutzer (Web-UI / API, B2B)
   │
   ▼
[Gateway]  Auth, Rate-Limit, Audit-Log, PII-Eingangsfilter
   │
   ▼
[Router]   Haiku-Klassifikation: Domäne · Komplexität · Risiko · Zeitbezug
   │
   ├── Route A: Standard  ──►  claude-sonnet-4-6
   ├── Route B: Komplex   ──►  claude-fable-5
   └── Route C: Triage/Format ► claude-haiku-4-5
   │
   ▼
[Orchestrator]  Tool-Loop (RAG, Rechner, Fristen, Dokumente)
   │
   ▼
[Guardrail-Layer]  Zitat-Validator · Disclaimer-Injektor · Scope-Filter
   │
   ▼
Antwort (+ Quellen, + Rechtsstand, + Risiko-Label)
```

Alle Komponenten laufen in EU-Regionen; Modellzugriff über die Anthropic API (Modellverfügbarkeit und aktuelle Modell-IDs vor Implementierung gegen https://docs.claude.com/en/api/overview verifizieren).

## 2. Modell-Routing (risikobasiert)

| Route | Modell (ID) | Auslöser | Beispiele |
|-------|-------------|----------|-----------|
| C – Triage & Utility | `claude-haiku-4-5` | Query-Klassifikation, Re-Ranking, Formatierung, Smalltalk, Metadaten-Extraktion | „Was heißt OSS?“, Routing-Vorstufe jeder Anfrage |
| A – Standard | `claude-sonnet-4-6` | Einzeldomäne, klare Rechtslage, Risiko-Score NIEDRIG/MITTEL | Kleinunternehmergrenze, AVV-Pflichtinhalte, Gewerbeanmeldung |
| B – Komplex | `claude-fable-5` | Domänenübergreifend, Gestaltungsanalyse, widersprüchliche Quellen, Risiko-Score HOCH, Stufe-2/3-Eskalation, Dokumentgenerierung mit Rechtsfolgen | Holding-Struktur UG→GmbH, DBA-Fälle, AI-Act-Konformitätsstrategie |

**Routing-Regeln:**
- Der Risiko-Score (0–100) wird deterministisch aus Klassifikationsmerkmalen berechnet (Betragsschwellen genannt? Betriebsprüfung/Strafrecht-Keywords? mehrere Domänen? Fristen mit Rechtsverlust?) – nicht vom LLM „gefühlt“.
- **Eskalation nach oben ist immer erlaubt** (Sonnet kann an Fable übergeben, wenn Tool-Loop Widersprüche findet), **Deeskalation nie** innerhalb einer Anfrage.
- Jede Antwort loggt Route + Score für das Eval-Harness.

## 3. Tool-Definitionen

Alle Tools sind deterministisch bzw. datenbankgestützt; das LLM orchestriert nur. Schemata (JSON Schema) implementiert Claude Code unter `src/tools/`.

### 3.1 `rag_suche`
- **Zweck:** Zugriff auf die Wissensbasis (siehe `KNOWLEDGE_ARCHITECTURE.md`).
- **Input:** `query`, `domaene[]`, `rechtsstand_datum` (default: heute), `max_chunks`.
- **Output:** Chunks inkl. Zitierkopf-Metadaten.
- **Regel:** Pflicht-Tool bei jeder Normfrage; der Orchestrator erzwingt mindestens einen Aufruf, bevor eine Antwort mit Normzitat freigegeben wird.

### 3.2 `steuer_rechner`
- **Zweck:** Deterministische Berechnungen: USt (Regelsteuersatz/ermäßigt, OSS-Sätze je Mitgliedstaat aus Tabelle), GewSt (Messbetrag × Hebesatz, § 35 EStG-Anrechnung), KSt inkl. Soli, EÜR-Überschlag, Kleinunternehmer-Grenzprüfung.
- **Input:** typisiertes Berechnungsobjekt (z. B. `{art: "gewst", gewinn: 120000, hebesatz: 410, rechtsjahr: 2026}`).
- **Output:** Ergebnis + Rechenweg + verwendete Parameter mit Quellen-Referenz (Parametertabellen sind versioniert wie Normen).
- **Regel:** LLM darf Zahlen aus Antworten nur aus Tool-Output übernehmen (Guardrail G4 prüft dies).

### 3.3 `fristen_kalender`
- **Zweck:** Fristberechnung nach AO/BGB-Regeln (§§ 108 ff. AO, Wochenend-/Feiertagsverschiebung je Bundesland), Abgabefristen (USt-VA, Jahreserklärungen mit/ohne Berater), AI-Act-Stichtage, DSGVO-Meldefrist 72 h (Art. 33).
- **Input:** `fristtyp`, `ausloese_datum`, `bundesland`, `mit_berater`.
- **Output:** Fristende (Datum), Rechtsgrundlage der Frist, Warnstufe.

### 3.4 `dokument_generator`
- **Zweck:** Entwürfe: AVV-Checkliste, VVT-Eintrag, DPIA-Gerüst, Gewerbeanmeldungs-Checkliste, AI-Act-Konformitäts-Gap-Liste, Beratervorbereitungs-Dossier.
- **Regel:** Jeder Output trägt Kopfzeile „ENTWURF – vor Verwendung fachlich prüfen lassen“ + Disclaimer; Dokumente mit Einreichungscharakter (Steuererklärungen) sind gesperrt (Scope-Abgrenzung Nr. 2).

### 3.5 `aenderungs_radar`
- **Zweck:** Abfrage des Changelogs der Wissensbasis (neue BMF-Schreiben, Normänderungen, AI-Act-Durchführungsrechtsakte) für proaktive Hinweise.
- **Input:** `domaene[]`, `seit_datum`.

### 3.6 Optionale Tool-Slots (Phase 2, siehe PROJECT_INSTRUCTIONS O2)
`datev_export` (Buchungsstapel-Entwurf), `kalender_sync` (Fristen → Kalender des Nutzers), `dms_ablage`. Slots sind im Schema reserviert, aber im MVP deaktiviert.

## 4. Permission-Modell

| Stufe | Wer/Was | Rechte |
|-------|---------|--------|
| P0 System | Orchestrator, Guardrails | Vollzugriff Pipeline, kein Zugriff auf Fremd-Mandanten-Daten |
| P1 Agent-Read | LLM-Kontext | Lesen: Wissensbasis, eigene Konversation, Tool-Outputs |
| P2 Agent-Write (unkritisch) | `dokument_generator` Entwürfe, Fristen in eigene Liste | Ohne Freigabe erlaubt, immer als ENTWURF markiert |
| P3 Agent-Write (kritisch) | Versand von Dokumenten, Kalender-Sync, jede Aktion mit Außenwirkung | **Human-in-the-Loop:** explizite Nutzerbestätigung pro Aktion; keine Sammelfreigaben |
| P4 Verboten | Behördenübermittlung (ELSTER etc.), Zahlungsauslösung, Änderung von Guardrail-Konfiguration zur Laufzeit | Technisch nicht implementiert (kein Tool vorhanden = stärkste Sperre) |

**Freigabeprozess kritischer Aussagen:** Antworten mit Risiko-Label HOCH und Eskalationsstufe 3 werden im UI mit Warnbanner gerendert; optional (Konfigurationsflag `review_mode=on` für Enterprise-Kunden) landen sie zusätzlich in einer Review-Queue für einen menschlichen Fachprüfer, bevor der Nutzer sie sieht.

## 5. Guardrails & Compliance-Checks

| ID | Guardrail | Mechanismus |
|----|-----------|-------------|
| G1 | Disclaimer-Injektion | Post-Processor hängt Pflicht-Disclaimer an jede fachliche Antwort an, unabhängig vom LLM-Output (Prompt-Injection-resistent) |
| G2 | RDG/StBerG-Scope-Filter | Klassifikator erkennt Anfragen nach vorbehaltenen Leistungen („reich meine UStVA ein“, „vertritt mich beim Finanzamt“) → höfliche Ablehnung + Eskalationsempfehlung, Template-basiert |
| G3 | Zitat-Validator | Deterministischer Abgleich aller Fundstellen im Output gegen gelieferte RAG-Chunks; Fail → 1 Korrektur-Turn → sonst Unsicherheits-Kennzeichnung |
| G4 | Zahlen-Provenienz | Regex/Parser extrahiert Beträge & Fristen aus dem Output und matcht gegen Tool-Outputs; freie LLM-Zahlen mit Rechtsfolge → Block & Retry |
| G5 | PII-Filter (Eingang) | Erkennung besonderer Kategorien (Art. 9 DSGVO) und überschüssiger personenbezogener Daten → Hinweis zur Datenminimierung, Pseudonymisierung im Kontext |
| G6 | Stale-Warnung | `stale`-Flag aus Wissensbasis → sichtbarer Aktualitätshinweis in der Antwort |
| G7 | Jurisdiktions-Gate | Fragen außerhalb DE/EU → Kennzeichnung als Orientierung + Eskalation |
| G8 | Audit-Trail | Vollständiges Logging (Anfrage-Hash, Route, Tools, Quellen-IDs, Guardrail-Ereignisse) für Nachvollziehbarkeit; Aufbewahrung gem. Löschkonzept |

## 6. Compliance des Agenten selbst

- **DSGVO:** Rollen: Opus Magnum/LYGOX = Verantwortlicher bzw. Auftragsverarbeiter je Vertragsmodell; AVV mit Anthropic und allen Sub-Prozessoren; EU-Datenresidenz; Löschkonzept (Konversationen default 90 Tage, konfigurierbar); Betroffenenrechte-Prozess; VVT-Eintrag und TOMs werden von `dokument_generator`-Templates selbst mitgepflegt (Dogfooding).
- **EU AI Act (Selbstklassifizierung):** OPUS PRIME EX ist nach vorläufiger Einordnung **kein Hochrisiko-System** i. S. v. Art. 6 Abs. 2 i. V. m. Anhang III (Rechtsinformations-Assistent für Unternehmen fällt nicht unter die Anhang-III-Bereiche; keine Rechtspflege i. S. v. Anhang III Nr. 8, da keine Nutzung durch/для Justizbehörden). Es gelten **Transparenzpflichten nach Art. 50** (Information, dass Nutzer mit KI interagieren) und Art. 4 (KI-Kompetenz). Die Einordnung ist als begründetes Assessment in `docs/ai-act-assessment.md` zu dokumentieren und bei Leitlinien-Updates zu überprüfen. Nutzung eines GPAI-Modells (Claude) als Downstream-Anbieter: Herstellerinformationen von Anthropic in die technische Dokumentation übernehmen.
- **Berufsrecht:** Marketing und UI dürfen den Agenten nicht als „Steuerberatung“/„Rechtsberatung“ bezeichnen; verbindliche Formulierung: „KI-gestützte Rechts- und Steuerinformation“.

## 7. Nicht-funktionale Anforderungen

- Latenz p95: Route A ≤ 20 s, Route B ≤ 60 s (inkl. Tool-Loop).
- Verfügbarkeit 99,5 % (MVP), Degradation: bei RAG-Ausfall nur noch Definitionsfragen mit deutlichem Hinweis, keine Normauskünfte.
- Kostensteuerung: Router-Ziel ≥ 60 % der Anfragen auf Route A/C; Monitoring pro Route.
- Observability: strukturierte Logs, Trace pro Anfrage (Route, Tools, Token, Guardrail-Hits), Dashboards.

## 8. Annahmen & offene Punkte

- A1: Modell-IDs entsprechen dem Stand Juli 2026 (`claude-fable-5`, `claude-sonnet-4-6`, `claude-haiku-4-5`); Claude Code verifiziert vor Implementierung gegen die API-Dokumentation und parametrisiert IDs in `config/models.yaml`.
- A2: UI/Frontend existiert im Opus-Magnum-Ökosystem oder wird als schlanke Referenz-Web-UI mitgeliefert (Entscheidung Owner; Repo sieht `apps/web/` optional vor).
- A3: Review-Queue (P3/review_mode) ist im MVP als Feature-Flag angelegt, Standard: aus.
- O1: Finale AI-Act-Selbstklassifizierung durch Fachreviewer bestätigen lassen (insb. falls künftig Behörden- oder HR-Nutzungsszenarien hinzukommen – dann Neubewertung Pflicht).
- O2: SLA/Verfügbarkeit mit Betriebsteam von LYGOX abstimmen.
