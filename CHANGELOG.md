# Changelog

All notable changes to **OPUS PRIME EX** are documented here.
Alle nennenswerten Änderungen an **OPUS PRIME EX** werden hier dokumentiert.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Status / Hinweis:** Pre-1.0. Die deterministische Pipeline (Routing, Retrieval,
> Guardrails G1–G8, Tools) ist implementiert und getestet; die formulierte Antwort
> benötigt einen eigenen `ANTHROPIC_API_KEY` (BYO key). Eine **menschliche
> RA/StB-Gegenzeichnung** der Rechtsinhalte und Disclaimer steht vor jedem Go-Live
> aus (siehe `spec/OPEN_QUESTIONS.md` #6/#9). Dies ist eine Rechts-*informations*-,
> keine Rechts-*dienstleistung*.

## [Unreleased]

### Added
- **Öffentliche OSS-Grundlage:** MIT-Lizenz, README (DE/EN), `CONTRIBUTING.md`,
  `SECURITY.md`, `CODE_OF_CONDUCT.md`, GitHub Issue-/PR-Templates.
- **Korpus-Abdeckung erweitert:** fünf weitere Gesetze in `config/korpus_quellen.yaml`
  (KStG, InsO, GwG, BDSG, UmwG; Slugs live gegen gesetze-im-internet.de verifiziert).
  Schließt sieben gezählte Muss-Normen der Coverage-Matrix — voller Live-Ingest
  **97/124 → 104/124** (Steuerrecht 22/25, Gewerberecht 14/20, DSGVO 18/20).
  Verbleibende Lücken sind bewusst Nicht-Gesetzes-Quellen (DBA/OECD-MA, BMF-Schreiben
  wie GoBD/AfA-Tabellen, IDW/IFRS, EDSA-Leitlinien, Nizza-Klassifikation), die eigene
  Adapter bräuchten, sowie das für eine einzelne Norm zu große SGB IV.
- **EU-Verordnung VO (EU) 608/2013** (Grenzbeschlagnahme bei Produktpiraterie) im
  Markenrecht-Korpus; Adapter live verifiziert (40 Artikel). Markenrecht 20 → 21/23,
  Gesamt-Coverage **106 → 107/124**.
- **Bring-your-own-key:** jede Entwicklerin nutzt ihren eigenen `ANTHROPIC_API_KEY`
  (`.env`, gitignored); stdlib-Web-UI bindet nur an `127.0.0.1:8848`.
- **CI-Härtung:** Der `unit`-Job der GitHub-Actions-Pipeline führt jetzt auch
  `tests/router`, `tests/gateway`, `tests/web` und `tests/evals` aus — zuvor liefen
  diese Verzeichnisse (u. a. die Klassifikator-Tests) in CI nicht mit.

### Changed
- **G5 (PII/Art.-9-Filter) von hinweisgebend zu technischer Redaktion:**
  `redigiere_pii_g5` ersetzt erkannte Art.-9-Signalwörter durch einen Platzhalter,
  **bevor** der Text Retrieval, Zahlen-Provenienz-Prüfung und Modell erreicht; der
  eigentliche Sachverhalt bleibt erhalten. Erfüllt das Designziel „keine Verarbeitung
  von Art.-9-Daten" (`PROJECT_INSTRUCTIONS §5.7`; Legal-Review #4).
  Spec: `AGENT_ARCHITECTURE.md §5 G5` v1.2, `config/guardrails.yaml` `modus: redaktion`.
- **Domänen-Erkennung des Klassifikators zitatbasiert:** explizite Gesetzes-/
  Verordnungszitate (z. B. „§ 15 MarkenG", „Art. 28 DSGVO") ordnen eine Anfrage jetzt
  auch dann der richtigen Domäne zu, wenn kein Schlagwort matcht.
- **Retrieval-Boost für explizite Zitate:** exakte Treffer auf Gesetz/CELEX und
  Einheit (§/Art.) werden im hybriden Ranking gezielt hochgewichtet.
- **`rechtsstand_abruf` aus echtem Quell-Stand:** der gii-Adapter liest das
  `builddate` des Rechtsakts (Root `<dokumente builddate="YYYYMMDD">`) und stempelt
  es als Rechtsstand auf die Chunks, statt das Ingest-Laufdatum zu verwenden. G6
  (Stale-Warnung) spiegelt damit den tatsächlichen Quellenstand. `builddate` wird
  echt validiert (ungültige Werte fallen auf den Config-Wert zurück); `gueltig_ab`
  bleibt bewusst config-basiert, da das gii-Basis-XML kein verlässliches
  Inkrafttretens-Datum je Paragraf liefert.

### Fixed
- **Coverage-Matcher zählte Ganz-Gesetz-Verweise nicht:** Muss-Normen, die ein
  ganzes Gesetz / eine ganze Verordnung ohne §/Artikel referenzieren (z. B. „UmwG
  (Grundzüge Verschmelzung)", „Anhang III VO (EU) 2024/1689"), konnten nie als
  indexiert gezählt werden, obwohl das Gesetz im Korpus lag. `_norm_indexed`
  erkennt solche Ganzverweise jetzt über Gesetz/CELEX-Präsenz (wortgrenzen-genau,
  keine False-Positives). Gezählte Coverage dadurch **104 → 106/124**
  (Gewerberecht 15/20, EU AI Act 16/17).
- **EUR-Lex-Adapter:** Umstellung auf CELLAR-Content-Negotiation (Formex-4-ZIP,
  `Accept: application/zip;mtype=fmx4`). Die frühere `/TXT/XML/`-URL lieferte nur
  CELLAR-Metadaten (NOTICE), nicht den Rechtsakt. Live gegen die DSGVO verifiziert:
  99 Artikel, 173 Erwägungsgründe, Art. 28 korrekt.
- **gesetze-im-internet.de-Slugs:** reale ZIP-Slugs mit Suffix (z. B. `ustg_1980`)
  in `config/korpus_quellen.yaml` hinterlegt.
- **Python-Packaging:** `[build-system]` + `[tool.setuptools.packages.find]`
  ergänzt, sodass `pip install -e .` nicht mehr an „multiple top-level packages"
  scheitert. Entry-Points `opus-prime-ex-serve` / `opus-prime-ex-ingest`.
- **Modell-Parameter:** Route A/B (Sonnet 5 / Fable 5) senden kein `temperature`
  mehr (die API lehnt den Parameter mit 400 ab); Route C (Haiku 4.5) behält `0.0`.

## Governance

Änderungen an den eingefrorenen Spec-Dateien (`spec/`) folgen dem Perfect-Twin-Prinzip:
Versionsnummer im Dateikopf, Eintrag in `FILE_MANIFEST.md`, Gatekeeper-Nachtrag in
`review/gate_report.md`; Änderungen am System-Prompt erfordern zusätzlich eine
Neuberechnung von `spec/spec_hashes.json` (durch `scripts/spec_lint.py` als CI-Gate
erzwungen).
