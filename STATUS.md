# STATUS — OPUS PRIME EX

> Ehrlicher Projekt-Snapshot. Stand: 2026-07-07.
> *Honest project snapshot. Detailhistorie in [CHANGELOG.md](CHANGELOG.md); Roadmap/offene
> Fragen in [spec/OPEN_QUESTIONS.md](spec/OPEN_QUESTIONS.md).*

## Kurzfassung

Die **deterministische Pipeline ist vollständig gebaut und getestet** (Routing, hybrides
Retrieval, Guardrails G1–G8, Tools, Ingest, Referenz-Web-UI). Der einzige Schritt, der
einen eigenen API-Key + Guthaben braucht, ist die **formulierte Modell-Antwort** —
Architektur, Recht-Retrieval und Schutzmechanismen laufen ohne Key sichtbar durch
(Bring-your-own-key, `.env`). **Pre-1.0:** eine menschliche RA/StB-Gegenzeichnung der
Rechtsinhalte und Disclaimer steht vor jedem Go-Live aus.

## Was heute funktioniert

| Bereich | Stand |
|---------|-------|
| **Routing** | Deterministischer Klassifikator + Risiko-Score, 3 Routen (A/B/C), zitatbasierte Domänenerkennung |
| **Retrieval** | Hybrid BM25 + optionale Dense-Embeddings, Verweisgraph, Norm-Lookup-Boost, 12k-Budget, Priorität Norm > Verwaltung |
| **Guardrails** | G1–G8 aktiv; G5 redigiert Art.-9-Daten technisch **vor** dem Modell; G3 validiert jede §/Art.-Fundstelle gegen den Korpus |
| **Korpus** | Live-Ingest aus 13 deutschen Gesetzen (gii) + 5 EU-Verordnungen (EUR-Lex Formex-4). ~4.500 Chunks, ~7.600 Verweiskanten |
| **Coverage** | **113 / 124 Muss-Normen** (Steuer 23/25, Gewerbe 19/20, Finanzen 7/11, DSGVO 19/20, AI-Act 16/17, Data-Act 8/8, Marken 21/23) |
| **Quell-Adapter** | gii (deutsche Gesetze), EUR-Lex (EU-Verordnungen), BMF (Verwaltungsauffassung, Infrastruktur fertig) |
| **Tools** | steuer_rechner, fristen_kalender, dokument_generator, aenderungs_radar — deterministisch, Einreichung hart gesperrt |
| **Qualität** | 202 Tests; vier Gates grün (`ruff`, `mypy --strict`, `pytest`, `spec_lint`); CI-Pipeline auf jedem Push/PR |
| **Compliance** | AI-Act-Selbstassessment (Entwurf), Disclaimer-Pflicht, kein PII in Logs, EU-first |

## Diese Runde (Bug-/Feature-Härtung, 2026-07-07)

11 einzeln geprüfte + gepushte Blöcke; vier echte Bugs behoben:

- **G5** von hinweisgebend → technischer Redaktion von Art.-9-Daten (OPEN_QUESTIONS #3).
- **CI-Lücke:** `router/gateway/web/evals` liefen nie in CI — jetzt abgedeckt.
- **gii-Bug:** Paragraphen ohne amtliche Überschrift (HGB § 1 usw.) wurden still
  verworfen — +241 Chunks zurückgeholt.
- **Coverage-Matcher:** Ganz-Gesetz-Verweise wurden nie gezählt.
- Korpus erweitert (KStG/InsO/GwG/BDSG/UmwG, VO 608/2013); Rechtsstand aus echtem
  Quell-`builddate`; neuer **BMF-Adapter** (Kern + PDF-Extraktion + Ingest-Loop).

Coverage in Summe: **97 → 112 / 124**.

## Offen — ehrlich

**Externe Blocker (kein Code löst das):**
- **API-Guthaben** für die erste echte Live-Antwort (Account-Sache).
- **Menschliche RA/StB-Abnahme** der Rechtsinhalte + Disclaimer-Freigabe vor Go-Live
  (spec/OPEN_QUESTIONS #6/#9) — Pflicht. **Instrument bereit:** das strukturierte
  Go-Live-Gate [review/human_signoff_checklist.md](review/human_signoff_checklist.md)
  ist zum Abarbeiten + Unterschreiben durch eine Berufsträger:in vorbereitet.
- **EU-gehostetes Embedding-Modell** (Infra-Entscheidung; verbessert Retrieval gegen
  BM25-Rauschen).

**Die verbleibenden 12 Coverage-Lücken brauchen neue Quelltypen, keine weiteren
gii-/EUR-Lex-Einträge:**
- BMF-Schreiben (GoBD/AfA-Tabellen/UStAE) — Adapter-Infrastruktur steht, aber es gibt
  aktuell **keine stabile, Randnummer-strukturierte Quell-URL** (BMF-Portal-Deep-Links
  rotieren; das volle GoBD 2019 ist archiviert). Spec §2 sieht dafür einen Web-Monitor vor.
- OECD-MA/DBA, IDW S6, IAS 1 — Sekundär-/Lizenzquellen.
- EDSA-Leitlinien, GPAI Code of Practice, DPMA/EUIPO-Guidelines — Soft Law.
- Nizza-Klassifikation (WIPO) — Lizenzfrage.
- SGB IV (§ 7a) — bewusst weggelassen (zu groß für eine einzelne Norm).

*(Erledigt 2026-07-07: SCC-Durchführungsbeschluss 2021/914 — eigener Klausel-Parser,
DSGVO 18 → 19.)*

---

*EN summary:* The deterministic pipeline (routing, retrieval, guardrails G1–G8, tools,
ingest, web UI) is complete and tested (202 tests, four green gates, CI on every push).
Legal-source coverage is 112/124 must-have norms across 7 domains. Remaining gaps need
new source-type adapters (BMF/soft-law/secondary), a working stable BMF URL, API credits
for the first live answer, and — mandatory before any go-live — human review by a
qualified lawyer/tax advisor. This is legal *information*, not legal *advice*.
