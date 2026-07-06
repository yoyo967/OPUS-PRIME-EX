# AI-Act-Selbstklassifizierung OPUS PRIME EX

<!-- SPEC: AGENT_ARCHITECTURE.md §6 (EU AI Act Selbstklassifizierung, zu dokumentieren
     in docs/ai-act-assessment.md); spec/OPEN_QUESTIONS.md #2 (vollstaendige
     Negativ-Pruefung aller acht Anhang-III-Kategorien, nicht nur Nr. 8) -->
<!-- STATUS: ENTWURF - begruendetes Assessment. Bestaetigung durch Fachreviewer
     vor Go-Live erforderlich (AGENT_ARCHITECTURE.md O1). Stand: 2026-07-05.
     Rechtsgrundlage: VO (EU) 2024/1689 (EUR-Lex CELEX 32024R1689); Artikel-/
     Anhangbezuege beim RAG-Ingest gegen die konsolidierte Fassung verifizieren. -->

## 1. System und Einsatzkontext

OPUS PRIME EX ist ein KI-gestützter **Rechts- und Steuerinformations-Assistent**
(ausdrücklich keine Rechts-/Steuerberatung, PROJECT_INSTRUCTIONS.md §5) für
**B2B-Nutzer** (Geschäftsführer, Gründer, CFOs, Compliance-Verantwortliche in
KMU). Er liefert allgemeine Rechtsinformation, Analysen, Fristen und
Dokument-**Entwürfe**; jede Aktion mit Außenwirkung ist technisch gesperrt
(Permission-Modell P4, AGENT_ARCHITECTURE.md §4). Das System nutzt
GPAI-Modelle von Anthropic (Claude) als Downstream-Verwender.

## 2. Negativ-Prüfung: Art. 6 Abs. 2 i. V. m. Anhang III (alle 8 Kategorien)

| Nr. | Anhang-III-Bereich | Einschlägig? | Begründung |
|-----|--------------------|--------------|------------|
| 1 | Biometrie (Fernidentifizierung, biometrische Kategorisierung, Emotionserkennung) | **Nein** | Keine Verarbeitung biometrischer Daten; G5 filtert besondere Kategorien (Art. 9 DSGVO) bereits am Eingang als Designziel heraus. |
| 2 | Kritische Infrastruktur (Sicherheitskomponenten für Verkehr, Wasser, Gas, Wärme, Strom, digitale Infrastruktur) | **Nein** | Reines Informationssystem; keine Steuerungs- oder Sicherheitsfunktion für Infrastruktur. |
| 3 | Allgemeine und berufliche Bildung (Zugang/Zulassung, Lernbewertung, Prüfungsüberwachung) | **Nein** | Kein Einsatz in Bildungs- oder Prüfungskontexten; Zielgruppe sind Unternehmensentscheider. |
| 4 | Beschäftigung, Personalmanagement, Zugang zur Selbstständigkeit (Einstellung/Auswahl, Beförderung/Kündigung, Aufgabenzuweisung, Verhaltensüberwachung) | **Nein** | OPUS PRIME EX trifft/unterstützt keine Personalentscheidungen über konkrete Personen. Er **informiert** über Rechtspflichten (z. B. erklärt er Betreiberpflichten, wenn ein Kunde ein Bewerbungs-Screening-Tool einsetzen will — siehe Few-Shot 3); das macht ihn nicht selbst zum Anhang-III-Nr.-4-System. Abgrenzungs-Marker: Sollte je eine Funktion Personaldaten konkreter Beschäftigter bewerten, ist die Einstufung neu vorzunehmen. |
| 5 | Wesentliche private und öffentliche Dienste (Anspruch auf öffentliche Leistungen, **Kreditwürdigkeit/Bonität natürlicher Personen**, Risikobewertung/Preisbildung Lebens-/Krankenversicherung, Notruf-Triage) | **Nein** | Der `steuer_rechner` berechnet Steuerlasten für Unternehmensentscheidungen des Nutzers selbst — keine Bonitätsbewertung natürlicher Personen und keine Bereitstellung an Dritte für Kreditvergabe-Entscheidungen. **Non-Goal (aus Legal-Review #3):** Berechnungsergebnisse dürfen nicht als Input für Kreditwürfigkeits-/Bonitätsentscheidungen Dritter über natürliche Personen angeboten oder beworben werden; Aufnahme als expliziter Non-Goal in PROJECT_INSTRUCTIONS §5 ist dem Owner als Spec-Änderung vorgeschlagen (siehe OPEN_QUESTIONS #2). |
| 6 | Strafverfolgung | **Nein** | Keine Nutzung durch/für Strafverfolgungsbehörden; Fragen mit Steuerstrafrechts-Bezug werden auf Eskalationsstufe 3 nur allgemein eingeordnet und an Berufsträger verwiesen. |
| 7 | Migration, Asyl, Grenzkontrolle | **Nein** | Kein Bezug; außerhalb der sieben Domänen (Mandats-Ablehnung im System Prompt). |
| 8 | Rechtspflege und demokratische Prozesse (Unterstützung von **Justizbehörden** bei Ermittlung/Auslegung von Sachverhalten und Recht; Wahlbeeinflussung) | **Nein** | Zielnutzer sind Unternehmen, nicht Justizbehörden; das System wird weder von noch für Gerichte/Justizbehörden zur Rechtsanwendung eingesetzt. Kein Bezug zu Wahlen/Abstimmungen. **Re-Assessment-Pflicht**, falls künftig Behörden-Nutzungsszenarien entstehen (AGENT_ARCHITECTURE.md O1). |

**Ergebnis:** OPUS PRIME EX ist nach dieser Prüfung **kein Hochrisiko-KI-System**
i. S. v. Art. 6 Abs. 2 i. V. m. Anhang III. Es ist auch kein System nach
Art. 6 Abs. 1 (kein Sicherheitsbauteil harmonisierter Produkte) und fällt nicht
unter die verbotenen Praktiken des Art. 5.

## 3. Anwendbare Pflichten

- **Art. 50 (Transparenz):** Nutzer werden informiert, dass sie mit einem
  KI-System interagieren — Umsetzung: sichtbarer Hinweis im UI (Frontend-
  Anforderung an Opus Magnum, AGENT_ARCHITECTURE.md A2) plus der in jeder
  fachlichen Antwort serverseitig injizierte Disclaimer (Guardrail G1).
- **Art. 4 (KI-Kompetenz):** Betreiberseitige Schulung der mit dem System
  arbeitenden Personen; Dokumentationspflicht bei Opus Magnum/LYGOX (P5).
- **GPAI-Downstream (Kap. V):** Als Verwender eines GPAI-Modells (Claude)
  übernimmt OPUS PRIME EX die Hersteller-/Transparenzinformationen von
  Anthropic in die technische Dokumentation (Modell-IDs und Bezugsquellen:
  `config/models.yaml`; Modell-Dokumentation: platform.claude.com).

## 4. Überprüfungszyklus

Neubewertung ist **verpflichtend** bei: (a) neuen Nutzungsszenarien
(Behörden, HR-Funktionen, Bonitätsbezug), (b) Änderungen von Anhang III oder
einschlägigen delegierten Rechtsakten/Kommissions-Leitlinien (Monitoring via
`aenderungs_radar`, Quelle `aufsicht_aemter` in `config/sources.yaml`),
(c) spätestens jährlich. Verantwortlich: Owner; Nachweis: Fortschreibung
dieses Dokuments mit Datum und Versionsvermerk.

## 5. Offene Punkte

1. Fachliche Bestätigung dieses Assessments durch Fachreviewer vor Go-Live
   (AGENT_ARCHITECTURE.md O1) — **offen**.
2. Owner-Entscheid zur Aufnahme des Non-Goals (Nr. 5, Kreditwürdigkeit) in
   PROJECT_INSTRUCTIONS §5 — **vorgeschlagen**, siehe OPEN_QUESTIONS #2.
3. Verifikation der Anhang-III-Wortlaute gegen die konsolidierte Fassung beim
   RAG-Ingest (Standardregel).
