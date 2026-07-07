# BRAIN.md — Schema & Konventionen des Second Brain

> Diese Datei sagt jedem Agenten (und Menschen), **wie dieses Gehirn aufgebaut ist**.
> Muster: Andrej Karpathys „LLM-Wiki" (raw → wiki → schema). Ein geteilter Wissensspeicher,
> den Menschen und alle Agenten über MCP nutzen. Spec: `opus-deck/spec/SECOND_BRAIN.md`.

## Aufbau

```
brain/
  BRAIN.md      # DIESE Schema-/Konventionsdatei (zuerst lesen)
  raw/          # RAW: unveraenderliche Quellen. Agent LIEST, aendert NIE. Append-only.
  wiki/         # WIKI: agenten-gepflegte, kompilierte Seiten (Backlinks, Index). Review-gated.
```

## Konventionen

- **Format:** Markdown mit YAML-Frontmatter:
  ```
  ---
  titel: <Kurztitel>
  erstellt: <ISO-Datum>
  tags: [tag1, tag2]
  quelle: <Herkunft, optional>
  ---
  <Inhalt>
  ```
- **IDs:** relativer Pfad ab `brain/`, z. B. `raw/2026-07-07_notiz.md`, `wiki/kleinunternehmer.md`.
- **Backlinks (wiki):** `[[andere-seite]]` verlinkt Wiki-Seiten; INDEX.md wird gepflegt.
- **Provenienz:** jeder Write trägt `wer`/`wann`/`quellen`. Raw ist append-only, Wiki review-gated.

## Regeln für Agenten

1. **Raw nie ändern.** Nur `wiki/` wird kompiliert/gepflegt — und nur als **Vorschlag**
   (`propose_wiki` → Mensch gibt frei). Kein direktes Überschreiben.
2. **Zuerst Wiki, dann Raw:** eine Frage trifft zuerst die kompilierten Wiki-Seiten; deckt das
   Wiki es nicht, greift Hybrid-Retrieval auf `raw/`.
3. **Zitieren:** Wiki-Aussagen verweisen auf ihre `raw/`-Quellen (nachvollziehbar).
4. **Ehrlich:** keine erfundenen Fakten; Unsicheres kennzeichnen.

## MCP-Zugang (so nutzen Agenten das Gehirn)

Server `second-brain` (stdio) — Tools: `brain_search(query,k)`, `brain_read(id)`,
`brain_list(schicht?)`, `brain_add_raw(titel,inhalt,tags?)`. (Wiki-Write/`propose_wiki`
folgt in B2, review-gated.)
