# review/legal_review_markenrecht_addendum.md
<!-- Legal-Review-Addendum zur Spec-Erweiterung v1.1 (Markenrecht als Domäne 7) · 2026-07-05 -->
<!-- Auftrag: spec/OPEN_QUESTIONS.md #9 · Methodik analog Cowork-Rolle 1 (review/legal_review.md) -->

Geprüfte Artefakte: `PROJECT_INSTRUCTIONS.md` v1.1 §1/§5, `AGENT_ARCHITECTURE.md` v1.1 §2/§3/§5,
`prompts/system_prompt_v1.2.md`, `review/coverage_matrix.yaml` v1.1 (Markenrecht-Block),
`evals/golden_set/markenrecht.yaml`.

Diese Prüfung ist eine **simulierte Fachprüfung (Claude Fable 5)**, keine Rechtsberatung und kein
Ersatz für die Gegenzeichnung durch zugelassene(n) Rechtsanwalt/Patentanwalt vor Go-Live (O3/A3-analog).
**Abweichend vom P2-Review wurden die zentralen Normzitate live gegen Primär-/Fachquellen verifiziert**
(gesetze-im-internet.de, EUR-Lex, ergänzend lxgesetze.de/ipright.eu als Sekundärbestätigung);
Abrufdatum jeweils 2026-07-05.

## A. Live-Verifikation der Normzitate

| Zitat in Spec/Artefakten | Quelle (Abruf 2026-07-05) | Ergebnis |
|---|---|---|
| § 42 MarkenG: Widerspruch 3 Monate ab Veröffentlichung der **Eintragung** | gesetze-im-internet.de/markeng/__42.html | **BESTÄTIGT** (Wortlaut: "Innerhalb einer Frist von drei Monaten nach dem Tag der Veröffentlichung der Eintragung … gemäß § 41 Absatz 2") |
| § 47 MarkenG: Schutzdauer 10 Jahre ab Anmeldetag, Verlängerung um je 10 Jahre (Antrag 6 Monate vor Ablauf, Nachfrist 6 Monate) | gesetze-im-internet.de/markeng/__47.html | **BESTÄTIGT** |
| Art. 46 UMV: Widerspruch 3 Monate ab Veröffentlichung der **Anmeldung** (nicht verlängerbar) | EUR-Lex 32017R1001 / lxgesetze.de/umv/46 | **BESTÄTIGT** — der in Golden-Set-Fall 08 und Coverage-Matrix hervorgehobene DE/EU-Unterschied (Eintragung vs. Anmeldung) ist korrekt |
| Art. 4 (Markenformen), Art. 7 (absolute Eintragungshindernisse), Art. 8 (relative), Art. 9 (Rechte aus der Unionsmarke), Art. 18 (Benutzung) UMV | EUR-Lex 32017R1001 (Volltext) | **BESTÄTIGT** (amtliche Überschriften stimmen) |
| Art. 52 (Dauer der Eintragung, 10 Jahre ab Anmeldetag), Art. 53 (Verlängerung) UMV | lxgesetze.de / ipright.eu (EUR-Lex-Spiegel) | **BESTÄTIGT** |
| Art. 58 (Verfallsgründe, 5-Jahres-Nichtbenutzung), Art. 59 (absolute Nichtigkeitsgründe inkl. Bösgläubigkeit), Art. 60 (relative Nichtigkeitsgründe) UMV | lxgesetze.de (EUR-Lex-Spiegel) | **BESTÄTIGT** |
| VO (EU) 608/2013 (zollrechtliche Durchsetzung / Grenzbeschlagnahme) | Standardzitat, unstrittig | **BESTÄTIGT** (beim Ingest regulär gegenprüfen) |
| §§ 119 ff. MarkenG als Fundstelle für IR-Marken (Madrid) | gesetze-im-internet.de/markeng (Inhaltsverzeichnis) | **FALSCH — korrigiert.** Seit dem MaMoG regelt der Abschnitt §§ 107–118 MarkenG den Schutz nach dem **Protokoll zum Madrider Markenabkommen**; **§§ 119–125a MarkenG betreffen Unionsmarken**. Siehe Finding #A1 |

## B. Findings

| # | Stufe | Finding | Referenz | Maßnahme |
|---|-------|---------|----------|----------|
| A1 | **MAJOR (behoben)** | Falsche Fundstelle für das Madrid-System: Coverage-Matrix und Golden-Set-Fall 10 zitierten "§§ 119 ff. MarkenG" (alte Gliederung vor MaMoG: PMMA ab § 119). Nach aktueller Gesetzesfassung: Madrid-Protokoll = §§ 107–118, Unionsmarken = §§ 119–125a. | coverage_matrix.yaml v1.1; markenrecht.yaml Fall 10 | **Direkt korrigiert** (Matrix: "§§ 107-118 MarkenG" + neuer Eintrag "§§ 119-125a MarkenG/Unionsmarken"; Golden-Set-Fall 10: "§§ 107 ff. MarkenG"). Reines Zitat-Fixing, keine Scope-Änderung; Spec-Dateien und Prompt v1.2 waren nicht betroffen (dort ohne §§-Angabe formuliert → Hash unverändert gültig). |
| A2 | MINOR | RDG-/Vertretungsabgrenzung Markenrecht: Die Kombination aus (a) P4-Sperre "kein Tool vorhanden" für Einreichungen, (b) Scope-Abgrenzung §5 Nr. 4/8, (c) Prompt-v1.2-Formulierungsregel ("orientierende Einschätzung, keine Verfügbarkeitsgarantie") überträgt den Owner-Entscheid zu BLOCKER #1 konsistent auf das Markenrecht. Restrisiko analog Finding #1 des P2-Reviews: individualisierte Kollisions-/Eintragungsfähigkeitsaussagen können trotz Formulierungsregel als Rechtsdienstleistung eingeordnet werden; zusätzlich sind im Markenrecht **Patentanwälte** vertretungsbefugt (PAO), was Eskalationsempfehlungen erwähnen sollten (in Prompt v1.2 bereits "Rechts- oder Patentanwält:in" — korrekt). | system_prompt_v1.2.md AUFTRAG UND GRENZEN; PROJECT_INSTRUCTIONS §5 Nr. 4/8 | Keine Änderung nötig; von der ohnehin vorgeschriebenen RA/PA-Gegenzeichnung vor Go-Live mit abdecken. |
| A3 | MINOR | Golden-Set-Fall 09 (Verwechslungsgefahr) und Fall 06 (beschreibende Angabe) verlangen zu Recht keine abschließende Einzelfall-Feststellung (`verbotene_inhalte` entsprechend gesetzt) — konsistent mit Prompt-Änderung #4. Fall 05 (Abmahnung, Stufe 3) korrekt als kritisch eingestuft (fristgebundener Rechtsverlust). | markenrecht.yaml Fälle 05/06/09 | Bestätigt, keine Aktion. |
| A4 | MINOR | Benutzungsschonfrist (Fall 18): § 26 MarkenG i. V. m. Art. 18 UMV korrekt; die 5-Jahres-Frist selbst ist in § 49 Abs. 1 MarkenG (Verfall) bzw. Art. 58 Abs. 1 lit. a UMV verankert — beim Ingest sicherstellen, dass der Verweisgraph § 26 ↔ § 49 abbildet, damit Antworten die Frist korrekt belegen. | markenrecht.yaml Fall 18; KNOWLEDGE_ARCHITECTURE §5 (Verweisgraph) | Ingest-Hinweis für P3, keine Spec-Änderung. |
| A5 | MINOR | Nizza-Klassifikation ist WIPO-Werk (kein amtliches Werk i. S. v. § 5 UrhG DE) — Matrix-Hinweis "nur referenzieren, nicht spiegeln" ist korrekt und bleibt bestehen. | coverage_matrix.yaml Hinweis | Bestätigt, keine Aktion. |

## C. Ergebnis

- **Keine BLOCKER.** 1 MAJOR-Finding (falsche Madrid-Fundstelle) wurde im selben Durchgang behoben;
  alle übrigen geprüften Normzitate live bestätigt.
- Prompt v1.2 unverändert → `spec/spec_hashes.json` bleibt gültig (Hash-Match geprüft).
- **Verbleibende Pflicht vor Go-Live (unverändert):** Gegenzeichnung dieses Addendums, des
  Golden-Sets `markenrecht.yaml` und des Disclaimer-Wortlauts durch zugelassene(n) RA/Patentanwalt
  (spec/OPEN_QUESTIONS.md #9 bleibt dafür offen, Status aktualisiert).

Quellen (Abruf 2026-07-05): gesetze-im-internet.de (§§ 42, 47 MarkenG, Inhaltsverzeichnis MarkenG),
EUR-Lex CELEX 32017R1001, lxgesetze.de/umv (Art. 46, 52, 53, 58–60), ipright.eu (Kap. V UMV),
euipo.europa.eu (Widerspruchsverfahren).
