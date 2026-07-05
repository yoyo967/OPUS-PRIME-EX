# spec/OPEN_QUESTIONS.md
<!-- Angelegt durch Cowork Rolle 5-Vorbereitung, gespeist aus Findings der Rollen 1-4 · 2026-07-05 -->
<!-- Arbeitsregel COWORK_HANDOFF_BRIEF.md §4.1: alles fachlich Neue landet hier statt eigenmaechtig in der Spec geaendert zu werden. -->

| # | Quelle | Offener Punkt | Vorschlag | Status |
|---|--------|----------------|-----------|--------|
| 1 | review/legal_review.md #1 (BLOCKER) | Abgrenzung Rechtsinformation vs. Rechtsdienstleistung/Steuerhilfeleistung bei individualisierten Zahlen-Subsumtionen in Kurzantworten | Formulierungsregel (siehe prompts/system_prompt_v1.1.md Aenderung #4) + zwingende RA/StB-Pruefung vor Go-Live | **Entschieden (Owner Yahya Yildirim, 2026-07-05): Formulierungsvorschlag uebernommen.** Few-Shot Beispiel 1 in prompts/system_prompt_v1.1.md entsprechend reformuliert. RA/StB-Pruefung vor Go-Live (O3/A3) bleibt zusaetzlich erforderlich, ist aber nicht mehr Handoff-blockierend. |
| 2 | review/legal_review.md #3 (MAJOR) | AI-Act-Selbstklassifizierung nur gegen Anhang III Nr. 8 begruendet, nicht gegen alle 8 Kategorien | Vollstaendige Negativ-Pruefung in docs/ai-act-assessment.md (Claude-Code-Aufgabe, P3) | Offen, nicht blockierend fuer Handoff |
| 3 | review/legal_review.md #4 (MAJOR) | G5 (PII-Filter) nur hinweisgebend, PROJECT_INSTRUCTIONS §5.7 verlangt aber Designziel "keine Verarbeitung Art. 9-Daten" | G5-Spezifikation um technische Redaktion/Pseudonymisierung ergaenzen (AGENT_ARCHITECTURE.md Aenderung noetig, P3) | Offen, nicht blockierend fuer Handoff |
| 4 | review/legal_review.md #5 (MINOR) | § 19 Abs. 3 UStG Bindungsfrist im Few-Shot ggf. durch Reform 01.01.2025 veraltet/verschoben | Vor RAG-Ingest gegen Live-Quelle verifizieren, Few-Shot ggf. generalisieren | Offen, technische Aufgabe P3 |
| 5 | review/coverage_matrix.yaml (data_act #16-Fall) | Nationales Ausfuehrungsgesetz zum Data Act (Sanktionsnormen) noch nicht identifiziert/benannt | Bei RAG-Ingest recherchieren und Coverage-Matrix ergaenzen | Offen, technische Aufgabe P3 |
| 6 | PROJECT_INSTRUCTIONS.md O3 | Finale Freigabe des Disclaimer-Wortlauts durch zugelassenen Rechtsanwalt | Vor Go-Live (P4), nicht vor Cowork-Handoff | Offen, Phase P4 |
| 7 | PROJECT_INSTRUCTIONS.md O1 | Mandanten-/Branchenmix der Zielnutzer noch nicht geklaert (beeinflusst OSS/EU-Priorisierung Wissensbasis, siehe KNOWLEDGE_ARCHITECTURE.md A3) | OSS-/USt-EU-Detailquellen als Prio-2 nachziehen, sobald Branchenmix vom Owner geklaert ist | Offen, Owner-Input, nicht blockierend |
| 8 | KNOWLEDGE_ARCHITECTURE.md O1 | Entscheidung, ob juris-/beck-online-Lizenzen zugekauft werden (wuerde Rechtsprechungs-Abdeckung deutlich verbessern) | MVP ohne kommerzielle Lizenzen (Open-Data-Portale gem. KNOWLEDGE_ARCHITECTURE.md §2 Prio 2); Entscheidung vor P5/Betrieb | Offen, Owner-Entscheidung, nicht blockierend |

<!-- Hinweis (2026-07-05, Reparatur): Die Datei war nach Eintrag #7 mitten im Satz abgeschnitten
     (Dateiabbruch beim urspruenglichen Speichern). Eintrag #7 wurde aus PROJECT_INSTRUCTIONS.md O1 /
     KNOWLEDGE_ARCHITECTURE.md A3 vervollstaendigt; Eintrag #8 wurde gemaess review/gate_report.md
     ("8 Eintraege, davon 1 entschieden, 7 offen") aus dem verbleibenden offenen Spec-Punkt
     KNOWLEDGE_ARCHITECTURE.md O1 rekonstruiert. Beide bei naechster Owner-Durchsicht bestaetigen. -->
