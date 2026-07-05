# KNOWLEDGE_ARCHITECTURE.md
<!-- Datei 3/8 · Projekt OPUS PRIME EX · Version 1.1 · Stand: 2026-07-05 -->
<!-- v1.1: Markenrecht als Domäne 7 — Korpus um MarkenG, UMV (EU) 2017/1001, VO (EU) 608/2013, DPMA-/EUIPO-Leitlinien erweitert. -->

# Wissensarchitektur OPUS PRIME EX

## 1. Grundprinzip

Der Agent beantwortet Normfragen **niemals aus freiem Modellwissen**, sondern aus einer versionierten Wissensbasis mit ausgewiesenem Rechtsstand (Perfect-Twin-Prinzip: Wissens-Zwilling). Modellwissen dient nur der Einordnung, Strukturierung und Sprachproduktion; jede zitierfähige Aussage muss durch Retrieval belegt oder ausdrücklich als unbelegt gekennzeichnet sein.

## 2. Quellenkorpus (Priorität 1 = Pflicht für MVP)

| Prio | Quelle | Inhalt | Zugriff | Update-Zyklus |
|------|--------|--------|---------|---------------|
| 1 | gesetze-im-internet.de (BMJ) | EStG, KStG, UStG, UStDV, AO, GewStG, GewO, HGB, GmbHG, BDSG, BetrVG (Auszüge), MarkenG, MarkenV | XML-Download je Gesetz | wöchentlicher Diff-Check |
| 1 | EUR-Lex | DSGVO (32016R0679), EU AI Act (32024R1689), Data Act (32023R2854), SCC-Beschluss (32021D0914), UMV (32017R1001) inkl. DVO/DelVO, Grenzbeschlagnahme-VO (32013R0608), einschlägige Durchführungs-/Delegierte Rechtsakte | CELEX-Abruf, konsolidierte Fassungen | wöchentlich |
| 1 | BMF-Schreiben | Verwaltungsauffassung Steuerrecht, UStAE, AEAO | Web-Monitor auf bundesfinanzministerium.de | wöchentlich |
| 2 | Rechtsprechung | BFH, BVerfG, EuGH, EuG, BGH (Markensachen), BPatG, ausgewählte FG/OVG mit Leitsatz | Open-Data-Portale (rechtsprechung-im-internet.de, curia.europa.eu) | monatlich |
| 2 | Aufsichtsbehörden & Ämter | EDSA-Leitlinien, DSK-Beschlüsse, Kurzpapiere; AI-Office-Leitlinien, GPAI Code of Practice; DPMA-Prüfungsrichtlinien, EUIPO Guidelines for Examination | Web-Monitor | monatlich |
| 3 | DBA-Texte | Doppelbesteuerungsabkommen (aktive Abkommen DE) | BMF-Übersicht | quartalsweise |
| 3 | Sekundärquellen (nur Kontext, nie alleinige Zitatbasis) | IHK-Merkblätter, amtliche Ausfüllhilfen | kuratiert, manuell | quartalsweise |

**Harte Regel:** Zitierfähig sind nur Prio-1/2-Primärquellen. Sekundärquellen dürfen Antworten anreichern, werden aber im Quellenblock als „ergänzend“ markiert.

## 3. Versionierung von Gesetzesständen

Jedes Dokument wird als **unveränderliches Snapshot-Objekt** gespeichert:

```
korpus/
  de/ustg/2025-01-01/ustg_full.xml          # Fassung gültig ab
  de/ustg/2025-01-01/manifest.json          # Quelle, Abruf-Datum, Hash
  eu/32024R1689/2026-02-17/celex.xml        # konsolidierte Fassung
  bmf/2025-03-xx_kleinunternehmer/...       # BMF-Schreiben einzeln
```

- **gueltig_ab / gueltig_bis** pro Norm-Fassung; überlappende Fassungen erlaubt (Übergangsrecht).
- Standard-Retrieval nutzt die **zum Anfragedatum gültige Fassung**; auf Nutzerwunsch („Rechtslage 2024?“) wird per Zeitparameter eine historische Fassung gezogen.
- Ein **Aktualitäts-Monitor** vergleicht wöchentlich Quell-Hashes; bei Änderung: neuer Snapshot, Re-Chunking nur der geänderten Normen, Changelog-Eintrag, Slack/E-Mail-Alert an den Owner (Änderungsradar speist sich hieraus).
- Quellen, deren letzter erfolgreicher Check älter als 2× Update-Zyklus ist, setzen ein `stale`-Flag; der Agent warnt dann in Antworten aus dieser Quelle.

## 4. RAG-Strategie

**Pipeline:** Query-Analyse → Hybrid Retrieval → Re-Ranking → Kontextkomposition → Antwort mit Zitatpflicht.

1. **Query-Analyse (Haiku-Route):** Domänenerkennung (Steuer/Gewerbe/Finanzen/DSGVO/AI-Act/Data-Act/Markenrecht), Extraktion expliziter Normzitate („§ 19 UStG“ → direkter Norm-Lookup), Zeitbezug (Rechtsstand), Risikosignale (für Routing/Eskalation, siehe `AGENT_ARCHITECTURE.md`).
2. **Hybrid Retrieval:** BM25/Keyword (Rechtstexte sind zitatgetrieben – exakte §-Treffer schlagen Semantik) **plus** Dense Embeddings (mehrsprachiges Embedding-Modell, da EU-Quellen teils EN). Gewichtung 0,5/0,5, per Eval-Harness zu kalibrieren.
3. **Struktur-Expansion:** Trifft ein Chunk einen Absatz, werden automatisch (a) die Norm-Überschrift, (b) referenzierte Normen aus dem Verweisgraph (z. B. § 19 Abs. 3 → § 19a UStG) und (c) einschlägige Verwaltungsanweisungen (UStAE-Abschnitt zur Norm) nachgeladen.
4. **Re-Ranking:** Cross-Encoder oder LLM-Re-Ranker (Haiku) auf Top-30 → Top-8; Bonus für: gültige Fassung zum Anfragedatum, Primärquelle, höhere Instanz.
5. **Kontextkomposition:** Chunks mit vollständigem Zitierkopf (siehe Metadaten) in den Prompt; hartes Budget 12k Tokens Kontext; bei Überschreiten: Priorisierung Norm > Verwaltung > Rechtsprechung > Leitlinie.
6. **Zitat-Validierung (Post-Processing):** Ein deterministischer Validator prüft, ob jede im Antworttext zitierte Fundstelle in den gelieferten Chunks existiert; sonst wird die Antwort mit Korrektur-Turn neu generiert (max. 1 Retry, danach Unsicherheits-Kennzeichnung).

## 5. Chunking-Strategie für Rechtstexte

**Atomare Einheit = der Paragraph/Artikel**, nicht der Token-Block. Fixed-size-Chunking ist für Normtexte ungeeignet.

- **Deutsche Gesetze (XML von gesetze-im-internet.de):** 1 Chunk = 1 § (inkl. amtlicher Überschrift). Übersteigt ein § 1.200 Tokens (z. B. § 4 EStG), Split auf Absatz-Ebene mit gemeinsamem Zitierkopf und `parent_id`.
- **EU-Verordnungen (EUR-Lex XML/HTML):** 1 Chunk = 1 Artikel; Erwägungsgründe in 5er-Gruppen als eigene Chunks mit Typ `recital` (niedrigeres Retrieval-Gewicht, aber wichtig für Auslegung); Anhänge je Nummer (Anhang III Nr. 4 AI Act = eigener Chunk).
- **BMF-Schreiben / Leitlinien:** Chunking nach Randnummern/Abschnitten, 300–800 Tokens, 15 % Overlap.
- **Urteile:** Leitsatz + Tenor als Prio-Chunk; Gründe abschnittsweise; Metadaten mit Aktenzeichen, Datum, Instanz, betroffenen Normen.
- **Verweisgraph:** Beim Ingest werden Normverweise („i. V. m.“, „§ … Abs. …“, „Artikel … der Verordnung …“) per Regex + LLM-Extraktion in eine Kanten-Tabelle geschrieben (`verweist_auf`), die Schritt 4.3 speist.

## 6. Metadaten-Schema (pro Chunk)

```json
{
  "chunk_id": "de-ustg-2025-01-01-p19-abs1",
  "quelle_typ": "gesetz | eu_verordnung | bmf | urteil | leitlinie | sekundaer",
  "jurisdiktion": "DE | EU",
  "gesetz": "UStG",
  "celex": null,
  "einheit": "§ 19 Abs. 1",
  "ueberschrift": "Besteuerung der Kleinunternehmer",
  "gueltig_ab": "2025-01-01",
  "gueltig_bis": null,
  "rechtsstand_abruf": "2026-06-29",
  "quelle_url": "https://www.gesetze-im-internet.de/ustg/__19.html",
  "hash": "sha256:…",
  "parent_id": "de-ustg-2025-01-01-p19",
  "verweist_auf": ["de-ustg-…-p19a", "de-ustg-…-p19-abs3"],
  "domaene": ["steuerrecht"],
  "sprache": "de",
  "stale": false
}
```

Der **Zitierkopf** im Prompt-Kontext wird aus `gesetz + einheit + ueberschrift + gueltig_ab + quelle_url` gerendert – daraus baut der Agent seinen Quellenblock, ohne Fundstellen zu halluzinieren.

## 7. Qualitätssicherung der Wissensbasis

- **Ingest-Tests:** Jede Pipeline-Änderung läuft gegen ein Fixture-Set (u. a. § 19 UStG, Art. 28 DSGVO, Art. 6 + Anhang III AI Act, Art. 5 Data Act, § 42 MarkenG + Art. 46 UMV) mit Assertions auf Chunk-Grenzen und Metadaten.
- **Coverage-Matrix:** Je Domäne eine Liste der Muss-Normen; CI schlägt fehl, wenn eine Muss-Norm im Index fehlt.
- **Drift-Report:** Monatlicher automatischer Bericht: neue/aufgehobene Normfassungen, neue BMF-Schreiben, stale Quellen.

## 8. Annahmen & offene Punkte

- A1: Vektor-Store und Embedding-Modell wählt Claude Code nach Infrastruktur-Vorgaben von Opus Magnum (EU-Hosting Pflicht); Schnittstelle ist in `AGENT_ARCHITECTURE.md` abstrakt definiert.
- A2: Lizenzlage: Gesetzestexte und EUR-Lex-Inhalte sind amtliche Werke bzw. mit Weiterverwendungserlaubnis; Sekundärquellen (IHK etc.) werden nur verlinkt/kurz referenziert, nicht vollständig gespiegelt.
- A3: OSS/USt-EU-Detailquellen (Erläuterungen der EU-Kommission) werden als Prio-2 nachgezogen, sobald O1 aus PROJECT_INSTRUCTIONS (Branchenmix) geklärt ist.
- O1: Entscheidung, ob juris/beck-online-Lizenzen zugekauft werden (würde Rechtsprechungs-Abdeckung deutlich verbessern; MVP kommt ohne aus).
