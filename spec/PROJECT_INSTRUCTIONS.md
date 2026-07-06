# PROJECT_INSTRUCTIONS.md
<!-- Datei 1/8 · Projekt OPUS PRIME EX · Version 1.2 · Stand: 2026-07-06 -->
<!-- v1.1: Markenrecht als Domäne 7 ergänzt (Owner-Entscheid Yahya Yildirim, 2026-07-05); Golden Set ≥140; Scope-Abgrenzung Nr. 4/8 erweitert. -->
<!-- v1.2 (Owner-Entscheide Yahya Yildirim, 2026-07-06): §5 Nr. 9 (Non-Goal Kreditwürdigkeit, aus AI-Act-Assessment / Legal-Review #3); §7 O1 entschieden (Branchen-Erstfokus SHK/Heizung-Sanitär Berlin). Prompt v1.2 unberührt (Hash gültig). -->

# OPUS PRIME EX – Projektinstruktionen

## 1. Projektüberblick

**OPUS PRIME EX** ist ein hochspezialisierter KI-Agent innerhalb des "Opus Magnum"-Ökosystems. Er liefert Expertenwissen auf Profi-Niveau in sieben Rechtsdomänen mit EU/Deutschland-Fokus (Berlin, EU-first):

| # | Domäne | Kernumfang |
|---|--------|-----------|
| 1 | Steuerrecht | EStG, KStG, UStG, AO, GewStG, DBA, USt national/EU/OSS, Betriebsprüfung, Gestaltungsanalyse |
| 2 | Gewerberecht | GewO, HGB, Gesellschaftsrecht (GmbH, UG, GmbH & Co. KG), Gewerbeanmeldung, Erlaubnispflichten, Compliance |
| 3 | Finanzen | Buchhaltung, Bilanzierung (HGB/IFRS), Liquiditätsplanung, Finanzierungsstrukturen, Controlling, KPI-Reporting |
| 4 | DSGVO | Art. 5–99 DSGVO, VVT, DPIA, AVV (Art. 28), Betroffenenrechte, Drittlandtransfer (Kap. V), BDSG-Bezüge |
| 5 | EU AI Act | Verordnung (EU) 2024/1689: Risikoklassifizierung, Konformitätsbewertung, GPAI-Pflichten, Governance, technische Dokumentation |
| 6 | Data Act | Verordnung (EU) 2023/2854: Datenzugangsrechte, IoT-Daten, Interoperabilität, B2B/B2G-Datenteilung, Cloud-Switching |
| 7 | Markenrecht | MarkenG, UMV (EU) 2017/1001, Schutzentstehung, absolute/relative Schutzhindernisse, Verwechslungsgefahr, Widerspruchs-/Löschungsverfahren, Benutzungszwang, Nizza-Klassifikation, Lizenzen, IR-Marke (Madrid-System), Abmahnung/Verletzung, Grenzbeschlagnahme |

**Auftraggeber / Stakeholder:**

- **Owner & Systems Architect:** Yahya Yildirim (Berlin) – Produktvision, Architekturentscheidungen, finale Freigaben
- **Organisation:** Opus Magnum / LYGOX – Betreiber des Agenten-Ökosystems (Annahme: B2B-SaaS-Kontext)
- **Zielnutzer (Annahme):** Geschäftsführer, Gründer, CFOs, Compliance-Verantwortliche und Datenschutzkoordinatoren kleiner und mittlerer Unternehmen (UG, GmbH, GmbH & Co. KG) in Deutschland/EU – **keine** Verbraucher, **keine** Privatpersonen als primäre Zielgruppe
- **Bauende Instanzen:** Claude Fable 5 (Spezifikation/Generierung, dieses Dokument), Claude Cowork (Orchestrierung, Review, Qualitätssicherung), Claude Code (Implementierung, Codebase, Deployment)

## 2. Architekturprinzip: Perfect Twin Architecture, angewendet auf OPUS PRIME EX

Die Perfect-Twin-Philosophie des Opus-Magnum-Ökosystems wird hier so operationalisiert: Jede fachliche Fähigkeit des Agenten existiert als **Zwillingspaar aus (a) deklarativer Spezifikation und (b) ausführbarer Implementierung**, die zu jedem Zeitpunkt nachweisbar synchron sind.

1. **Spezifikations-Zwilling (dieses Artefakt-Set):** Die sieben MD-Dateien dieses Projekts sind die *Single Source of Truth*. Verhalten, das nicht spezifiziert ist, darf nicht implementiert werden; spezifiziertes Verhalten darf nicht stillschweigend abweichen.
2. **Implementierungs-Zwilling (Repo):** Claude Code erzeugt Code, Prompts, Tool-Definitionen und Tests, die 1:1 auf Abschnitte der Spezifikation rückverweisen (Trace-IDs, siehe `CLAUDE.md`, Abschnitt "Spec Traceability").
3. **Wissens-Zwilling:** Jede Rechtsaussage des Agenten spiegelt einen versionierten Rechtsstand in der Wissensbasis (siehe `KNOWLEDGE_ARCHITECTURE.md`). Der Agent antwortet nie aus "freiem Modellwissen" zu Normen, ohne den Stand der Quelle auszuweisen.
4. **Drift-Kontrolle:** Ein CI-Check (Spec-Lint) schlägt fehl, wenn System-Prompt-Hash, Tool-Schemata oder Guardrail-Konfiguration im Repo vom Stand der MD-Spezifikation abweichen.

**Konsequenz:** Änderungen laufen immer Spezifikation → Review → Implementierung, nie umgekehrt.

## 3. Zielsetzung

1. Ein produktiv einsetzbarer Agent, der auf jede Anfrage in seinen sieben Domänen mit **Rechtsgrundlage + Praxisimplikation + Risikoeinschätzung + Quellenangabe** antwortet.
2. Proaktive Hinweise auf Fristen, Übergangsregelungen und bevorstehende Rechtsänderungen (z. B. gestaffelte Anwendbarkeit des EU AI Act, BMF-Schreiben, Jahressteuergesetze).
3. Rechtssichere Selbstbegrenzung: Der Agent liefert **Rechtsinformation und Entscheidungsvorbereitung**, keine Rechts- oder Steuerberatung im Sinne von RDG bzw. StBerG (siehe Abschnitt 5).
4. Vollständige Übergabefähigkeit: Chat → Cowork → Claude Code ohne Informationsverlust (siehe `COWORK_HANDOFF_BRIEF.md` und `NEXT_STEPS.md`).

## 4. Erfolgskriterien – Definition of Done (fertiger Agent)

Der Agent gilt als fertig, wenn alle folgenden Kriterien erfüllt und nachgewiesen sind:

**Fachliche Qualität**
- [ ] Golden-Set-Evaluation: ≥ 95 % korrekte Rechtsgrundlagen-Zitierung auf einem kuratierten Testset von ≥ 140 Fällen (20 je Domäne), reviewt durch menschlichen Fachprüfer.
- [ ] 0 Fälle im Golden Set, in denen der Agent eine vorbehaltene Rechts-/Steuerberatungsleistung ohne Disclaimer und Eskalationshinweis erbringt.
- [ ] Jede Antwort mit Normbezug enthält: Norm (§/Art., Gesetz), Rechtsstand-Datum, mindestens eine Primärquelle.
- [ ] Zahlenwerke (Steuerlast, Fristen, GewSt-Hebesatz-Rechnungen) werden ausschließlich durch deterministische Tools berechnet, nie durch das LLM frei generiert (Tool-Coverage-Test grün).

**Technik & Betrieb**
- [ ] Modell-Routing gemäß `AGENT_ARCHITECTURE.md` implementiert und durch Routing-Tests abgedeckt.
- [ ] RAG-Pipeline mit versionierten Rechtsständen live; Aktualitäts-Monitor meldet Quellen älter als der definierte Update-Zyklus.
- [ ] CI/CD-Pipeline grün (Lint, Unit, Eval-Harness, Spec-Lint) gemäß `CLAUDE.md`.
- [ ] Latenz-Budget: p95 ≤ 20 s für Standardfragen (Sonnet-Route), ≤ 60 s für komplexe Gestaltungsanalysen (Fable-Route).

**Compliance des Agenten selbst**
- [ ] DSGVO: VVT-Eintrag, AVV mit allen Prozessoren, TOMs dokumentiert, EU-Datenresidenz konfiguriert.
- [ ] EU AI Act: Selbstklassifizierung dokumentiert, Transparenzpflichten nach Art. 50 umgesetzt (Nutzer werden informiert, dass sie mit einem KI-System interagieren), technische Dokumentation angelegt.
- [ ] Pflicht-Disclaimer in jeder ausgehenden Antwort mit rechtlicher Tragweite (automatisch injiziert, nicht prompt-abhängig).

## 5. Scope-Abgrenzung – was OPUS PRIME EX NICHT tut

1. **Keine Rechtsdienstleistung im Einzelfall (§ 2 RDG):** keine verbindliche rechtliche Prüfung konkreter Einzelfälle mit Vertretungs- oder Gestaltungsanspruch; stets Kennzeichnung als allgemeine Rechtsinformation.
2. **Keine geschäftsmäßige Hilfeleistung in Steuersachen (§§ 2–5 StBerG):** keine Erstellung/Einreichung von Steuererklärungen, keine Vertretung gegenüber Finanzbehörden, keine verbindliche steuerliche Einzelfallberatung. Der Agent bereitet Entscheidungen vor und verweist für verbindliche Beratung an Steuerberater/Rechtsanwälte.
3. **Keine Wirtschaftsprüfungs- oder Abschlussprüfungsleistungen** (HGB/WPO-vorbehalten).
4. **Keine Übermittlung an Behörden und Ämter** (ELSTER, Transparenzregister, Gewerbeamt, DPMA, EUIPO, WIPO) – der Agent generiert Entwürfe/Checklisten, die Einreichung erfolgt durch den Nutzer oder dessen Berater. Insbesondere keine Einreichung von Markenanmeldungen, Widersprüchen oder Löschungsanträgen und keine Vertretung in Amts-/Gerichtsverfahren (§ 2 RDG; Vertretungsvorbehalte für Rechts-/Patentanwälte).
5. **Keine Rechtsauskünfte außerhalb des Geltungsbereichs** EU/Deutschland (andere Jurisdiktionen nur als ausdrücklich gekennzeichnete Orientierung mit Eskalationsempfehlung).
6. **Keine Garantie der Tagesaktualität:** Der Agent weist den Rechtsstand seiner Quellen aus; bei erkennbar veralteten Ständen warnt er aktiv.
7. **Keine Verarbeitung besonderer Kategorien personenbezogener Daten (Art. 9 DSGVO)** als Designziel; Eingaben werden dahingehend gefiltert und Nutzer zur Datenminimierung angehalten.
8. **Keine Marken-Verfügbarkeitsgarantie:** Identitäts-/Ähnlichkeitsrecherchen und Aussagen zur Eintragungsfähigkeit sind stets orientierend (keine Vollständigkeits- oder Freiheitsgarantie gegenüber Drittrechten); die abschließende Recherche und Anmeldestrategie bleibt Rechts-/Patentanwälten vorbehalten.
9. **Keine Verwendung von Berechnungsergebnissen für Kreditvergabe-/Bonitätsentscheidungen Dritter** (v1.2, Owner-Entscheid 2026-07-06): Ausgaben des `steuer_rechner` und andere Ergebnisse dienen der Entscheidungsvorbereitung des anfragenden Unternehmens selbst; sie werden nicht für die Bewertung der Kreditwürdigkeit oder Bonität natürlicher Personen durch Dritte angeboten oder beworben. Dieser Non-Goal stützt zugleich die AI-Act-Selbstklassifizierung (kein Hochrisiko-System nach Anhang III Nr. 5, siehe `docs/ai-act-assessment.md`).

## 6. Projektphasen

| Phase | Instanz | Ergebnis |
|-------|---------|----------|
| P1 Spezifikation | Fable 5 (Chat) | Dieses Artefakt-Set (8 Dateien) |
| P2 Orchestrierung & Review | Claude Cowork | Reviewte, ggf. korrigierte Spezifikation + Arbeitspakete |
| P3 Implementierung | Claude Code | Repo, Tests, Deployment-Pipeline |
| P4 Evaluation | Cowork + Mensch | Golden-Set-Ergebnis, Abnahmeprotokoll gegen Abschnitt 4 |
| P5 Betrieb | Opus Magnum / LYGOX | Monitoring, Update-Zyklen der Wissensbasis |

## 7. Annahmen & offene Punkte

**Annahmen (A):**
- A1: Zielnutzer sind B2B-Kunden (KMU-Entscheider), Vertragssprache Deutsch, UI-Sprache Deutsch mit englischem Fallback.
- A2: Deployment auf Anthropic API mit EU-Datenresidenz-Anforderung; Hosting eigener Komponenten in EU-Rechenzentren.
- A3: Opus Magnum / LYGOX verfügt über oder beauftragt mindestens einen menschlichen Fachreviewer (StB/RA) für das Golden Set.
- A4: Monetarisierung/Abrechnung ist Out-of-Scope dieses Artefakt-Sets.
- A5: "Perfect Twin Architecture" wird mangels schriftlicher Kanon-Definition wie in Abschnitt 2 operationalisiert; Anpassung durch Owner möglich.

**Offene Punkte (O):**
- O1: ~~Exakter Mandanten-/Branchenmix der Zielnutzer~~ **Entschieden (Owner Yahya Yildirim, 2026-07-06): Erstfokus SHK/Heizung-Sanitär, Region Berlin** (KMU-Handwerksbetriebe). Priorisierung der Wissensbasis entsprechend: Steuer-/Gewerbe-/Markenrecht mit Handwerks-/Innungsbezug vor E-Commerce/OSS-Schwerpunkt; OSS bleibt Prio-2 (KNOWLEDGE_ARCHITECTURE.md A3). Steht im Einklang mit der Pilot-Nische aus dem Agenticum-Kontext.
- O2: Gewünschte Integrationen (DATEV-Export, Kalender, DMS) – in `AGENT_ARCHITECTURE.md` als optionale Tool-Slots vorgesehen.
- O3: Freigabe des finalen Disclaimer-Wortlauts durch einen zugelassenen Rechtsanwalt vor Go-Live.
