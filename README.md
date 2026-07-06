# OPUS PRIME EX

> A spec-driven, guardrailed **legal & tax information agent for German / EU law** —
> RAG over *live* statutes, deterministic calculation tools, and Claude models,
> with every answer routed through eight compliance guardrails.

![Python](https://img.shields.io/badge/python-3.12+-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)
![Typed: mypy --strict](https://img.shields.io/badge/typed-mypy%20--strict-blue)
![Lint: ruff](https://img.shields.io/badge/lint-ruff-orange)
![Status: alpha](https://img.shields.io/badge/status-alpha-yellow)

**Bring your own Anthropic API key.** Clone, add your key, run — the corpus is built
from public primary sources (Federal law + EUR-Lex) at ingest time.

🇬🇧 English below · 🇩🇪 [Deutsch weiter unten](#-deutsch)

---

## ⚖️ Scope & Legal Notice (read this first)

OPUS PRIME EX provides **general legal and tax *information*** — **not** legal or tax
*advice* in an individual case. It does **not** replace a licensed attorney
(*Rechtsanwalt*) or tax advisor (*Steuerberater*), and it is designed **not** to
perform services reserved to them (§ 2 RDG, §§ 2–5 StBerG). Every substantive answer
carries a mandatory disclaimer, injected server-side (not prompt-dependent), and users
are told they interact with an AI system (Art. 50 EU AI Act).

**If you deploy it, you are the operator and solely responsible** for compliance with
applicable law and for the content your instance generates. Before any production use:
a licensed attorney/tax advisor must review the golden set and the disclaimer wording.
This repository is a **reference implementation**, currently **alpha / pre-production**.

---

## What it is

OPUS PRIME EX answers questions across **seven legal domains** with EU/Germany focus:
**tax law · commercial/trade law · finance · GDPR · EU AI Act · Data Act · trademark law.**

It is built on a **"Perfect Twin" discipline**: a frozen specification (`spec/`) is the
single source of truth, and every module traces back to it — enforced by a CI-blocking
`spec_lint`. The LLM never does math or invents citations; those are handled by
deterministic tools and validated against the retrieved sources.

### Architecture

```
          user question
               │
        ┌──────▼───────┐   deterministic risk score (no "vibes")
        │   Router     │   → Haiku (triage) · Sonnet (standard) · Fable (complex)
        └──────┬───────┘
               │
      ┌────────▼─────────┐  pre-guardrails: scope filter (G2), PII (G5), jurisdiction (G7)
      │   Orchestrator   │
      └────────┬─────────┘
               │ mandatory retrieval before any citation
        ┌──────▼───────┐   BM25 (+ optional dense) over 3000+ live-law chunks,
        │   Retrieval  │   metadata-filtered by domain & legal date, reference graph
        └──────┬───────┘
               │
        ┌──────▼───────┐   real Anthropic models (your key)
        │    Model     │
        └──────┬───────┘
               │ post-guardrails: citation validator (G3), number provenance (G4),
        ┌──────▼───────┐  stale warning (G6), disclaimer injection (G1), audit trail (G8)
        │  Guardrails  │
        └──────┬───────┘
               ▼
     answer + sources + risk label
```

### Key properties

- **Deterministic legal tools** — tax math (VAT, trade tax incl. § 35 EStG, small-business
  threshold), statutory deadlines (§ 108 AO weekend/holiday shifts per federal state,
  GDPR 72h, trademark opposition), document drafts (filing is blocked). The LLM only
  relays results; it never computes.
- **Live legal corpus** — source adapters fetch and normalize the *real* published XML:
  `gesetze-im-internet.de` (German statutes) and **EUR-Lex Formex-4 via CELLAR**
  (EU regulations). A single `--live` ingest builds ~3000 chunks with a citation graph.
- **Eight guardrails (G1–G8)** — disclaimer injection, RDG/StBerG scope filter, citation
  validator, number-provenance check, Art.-9 PII filter, staleness warning, jurisdiction
  gate, PII-free audit trail. Covered by adversarial tests.
- **Reference web UI** — a stdlib-only chat interface (no framework, no CDN, no external
  calls; binds to `127.0.0.1`). The full pipeline is visible per answer even *without*
  API credits.
- **Typed & tested** — `mypy --strict`, `ruff`, 170+ tests, CI-blocking `spec_lint`.

> **Honest status.** The deterministic pipeline (routing, retrieval, guardrails, tools)
> runs today. Producing the *model's* formulated answer needs **your own API key with
> credits**. Dense embeddings are pluggable but default to **BM25-only** until you wire
> an EU-hosted embedding model. Corpus coverage is currently **97 / 124** curated
> must-have norms (case law, administrative circulars, and DBA sources still pending).

---

## Quickstart (bring your own key)

**Requirements:** Python 3.12+, an [Anthropic API key](https://platform.claude.com/settings/keys)
with credits.

```bash
git clone <your-fork-url> opus-prime-ex
cd opus-prime-ex
python -m pip install -e ".[dev]"

# 1. Add your key (the file is gitignored; never commit it)
cp .env.example .env
#   → edit .env and paste your key behind ANTHROPIC_API_KEY=

# 2. Build the live corpus from public primary sources (network)
python scripts/ingest.py --live --coverage

# 3. Launch the reference web UI  →  http://127.0.0.1:8848
python apps/web/server.py
```

Or ask a single question end-to-end from the CLI:

```bash
python scripts/demo.py "Muss ich als Kleinunternehmer Umsatzsteuer ausweisen?"
```

**No key / no credits?** Everything except the model's final text still runs — you see
routing, the retrieved statute sections, and the guardrail events, with a clear notice
instead of the answer. That is intentional, so you can inspect the machine first.

---

## Configuration

| What | Where |
|---|---|
| API key, region, retention | `.env` (see `.env.example`) |
| Model routing & per-route params | `config/models.yaml` |
| Guardrail toggles (G1–G8) | `config/guardrails.yaml` |
| Corpus sources & update cycles | `config/sources.yaml` |
| Live-ingest sources (statute slugs, CELEX ids) | `config/korpus_quellen.yaml` |

Model IDs are pinned and verified against the current Anthropic API. Route A/B send **no**
`temperature` (rejected by Sonnet 5 / Fable 5) and steer via adaptive thinking; Route C
uses `temperature 0.0` for classification.

---

## Project structure

```
spec/          Frozen specification — the single source of truth (Perfect Twin)
src/
  router/      Deterministic risk score + domain classifier
  orchestrator/  Tool loop + guardrail pipeline
  guardrails/  G1–G8
  tools/       steuer_rechner, fristen_kalender, dokument_generator, … (+ versioned params)
  rag/         chunker, hybrid retrieval, vector store, ingest, verweisgraph
    sources/   gii (gesetze-im-internet) + eurlex (Formex-4/CELLAR) adapters
  gateway/     Anthropic API client, prompt builder, config
apps/web/      stdlib reference web UI
evals/         golden set (140 cases) + scoring harness
scripts/       ingest, demo, spec_lint
tests/         unit · guardrail · routing · ingest · web (170+)
docs/          AI-Act self-assessment, …
```

---

## Development

```bash
python -m ruff check .        # lint
python -m mypy                # type-check (strict), incl. apps/
python -m pytest -q           # tests
python scripts/spec_lint.py   # spec ↔ implementation consistency (CI-blocking)
python -m evals.harness.run --smoke   # guardrail/eval smoke (fake model, no key)
```

CI runs `lint → typecheck → unit → ingest-fixtures → guardrail-tests → spec_lint → eval-smoke`.

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for the workflow and **[SECURITY.md](SECURITY.md)**
for reporting vulnerabilities.

---

## Roadmap (honest open items)

- [ ] EU-hosted embedding model → dense retrieval (removes BM25 same-number noise)
- [ ] Live evaluation against the ≥95 % citation-accuracy gate (needs key + reviewer)
- [ ] Remaining must-have norms: case law (BFH/EuGH), BMF circulars, DBA texts
- [ ] BMF administrative-practice monitor
- [ ] Refine `gueltig_ab` from statute metadata; expand classifier keywords
- [ ] G5 PII: technical redaction (currently advisory)
- [ ] Human review of golden set + disclaimer wording before any production use

---

## License

[MIT](LICENSE) — for the **software**. The MIT grant does not cover the legal
responsibility of operating a legal-information service; see *Scope & Legal Notice* above.
Statute texts are public primary sources retrieved at runtime, not redistributed here.

---
---

## 🇩🇪 Deutsch

> Ein spezifikationsgetriebener, guardrail-gesicherter **Rechts- & Steuerinformations-Agent
> für deutsches/EU-Recht** — RAG über *live* geladene Gesetze, deterministische
> Rechen-Tools und Claude-Modelle; jede Antwort läuft durch acht Compliance-Guardrails.

**Eigenen Anthropic-API-Key verwenden.** Klonen, Key eintragen, starten — der Korpus wird
zur Ingest-Zeit aus öffentlichen Primärquellen (Bundesrecht + EUR-Lex) aufgebaut.

### ⚖️ Geltungsbereich & Rechtshinweis (bitte zuerst lesen)

OPUS PRIME EX liefert **allgemeine Rechts- und Steuer*information*** — **keine** Rechts-
oder Steuer*beratung* im Einzelfall. Er ersetzt **keine** zugelassene anwaltliche oder
steuerliche Beratung und ist so ausgelegt, **keine** den Berufsträgern vorbehaltenen
Leistungen zu erbringen (§ 2 RDG, §§ 2–5 StBerG). Jede fachliche Antwort trägt einen
serverseitig injizierten Pflicht-Disclaimer; Nutzer werden über die KI-Interaktion
informiert (Art. 50 EU AI Act).

**Wer ihn betreibt, ist Betreiber und allein verantwortlich** für die Einhaltung
geltenden Rechts und die von der Instanz erzeugten Inhalte. Vor jedem Produktivbetrieb:
Prüfung des Golden Sets und des Disclaimer-Wortlauts durch zugelassene RA/StB. Dieses
Repository ist eine **Referenzimplementierung**, derzeit **Alpha / Pre-Produktion**.

### Was es ist

Sieben Domänen (EU/DE-Fokus): **Steuerrecht · Gewerberecht · Finanzen · DSGVO ·
EU AI Act · Data Act · Markenrecht.** Aufgebaut nach dem **„Perfect-Twin"-Prinzip**:
Die eingefrorene Spezifikation (`spec/`) ist die einzige Wahrheitsquelle; jedes Modul
verweist darauf zurück, erzwungen durch ein CI-blockierendes `spec_lint`. Das LLM
rechnet nie und erfindet keine Fundstellen — dafür sorgen deterministische Tools, die
gegen die abgerufenen Quellen validiert werden.

### Kerneigenschaften

- **Deterministische Tools** — Steuerberechnungen, Fristen (§ 108 AO je Bundesland,
  DSGVO 72h, Marken-Widerspruch), Dokument-Entwürfe (Einreichung gesperrt). Das LLM
  übernimmt nur Ergebnisse.
- **Live-Rechtskorpus** — Quell-Adapter holen und normalisieren das *echte* XML:
  `gesetze-im-internet.de` und **EUR-Lex Formex-4 via CELLAR**. Ein `--live`-Ingest baut
  ~3000 Chunks samt Verweisgraph.
- **Acht Guardrails (G1–G8)** — Disclaimer, RDG/StBerG-Scope-Filter, Zitat-Validator,
  Zahlen-Provenienz, Art.-9-PII-Filter, Stale-Warnung, Jurisdiktions-Gate, Audit-Trail.
- **Referenz-Web-UI** — reine Standardbibliothek (kein Framework/CDN/externe Calls, nur
  `127.0.0.1`); die volle Pipeline ist je Antwort sichtbar — auch **ohne** Guthaben.

> **Ehrlicher Stand.** Die deterministische Pipeline läuft heute. Der *formulierte*
> Antworttext braucht **deinen eigenen Key mit Guthaben**. Dense-Embeddings sind
> pluggbar, laufen aber standardmäßig **BM25-only** bis ein EU-gehostetes Embedding-Modell
> angebunden ist. Korpus-Abdeckung aktuell **97 / 124** Muss-Normen.

### Schnellstart

```bash
git clone <dein-fork> opus-prime-ex && cd opus-prime-ex
python -m pip install -e ".[dev]"
cp .env.example .env          # Key hinter ANTHROPIC_API_KEY= eintragen (gitignored!)
python scripts/ingest.py --live --coverage   # Live-Korpus aus Primärquellen (Netz)
python apps/web/server.py     # → http://127.0.0.1:8848
```

**Kein Key/Guthaben?** Alles außer dem finalen Modelltext läuft trotzdem — Routing,
gefundene Normen, Guardrail-Ereignisse sind sichtbar, mit klarem Hinweis statt Antwort.

### Lizenz

[MIT](LICENSE) — für die **Software**. Die Lizenz deckt nicht die rechtliche
Verantwortung des Betriebs; siehe Rechtshinweis oben. Gesetzestexte sind öffentliche
Primärquellen, zur Laufzeit geladen, hier nicht mitverbreitet.
