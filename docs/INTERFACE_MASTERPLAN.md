# INTERFACE-MASTERPLAN — Agent-Workbench für OPUS PRIME EX (und weitere Agenten)

> **Arbeitstitel des Produkts:** **OPUS DECK** (die „Kommandobrücke", von der aus Menschen
> Agenten steuern). Alternativen zur Entscheidung: *OPUS BRIDGE*, *AGENT HAVEN*, *ATRIUM*.
> **Status:** Masterplan v0.1 (ENTWURF, 2026-07-07). Semi-atomar: Phasen → Meilensteine →
> atomare Work-Items (WI) mit Akzeptanzkriterien. Kein Code-Vertrag, sondern Bauplan.
>
> **Nicht-Ziel dieses Dokuments:** nichts beschönigen. Wo etwas schwer, riskant oder eine
> offene Entscheidung ist, steht es explizit drin (Abschnitt 12 + 13).

---

## 0. Vision & North Star

Ein **weltklasse, VS-Code-gebrandetes Interface**, das

1. **OPUS PRIME EX ein Zuhause gibt** — Menschen steuern den Agenten visuell, sehen die
   deterministische Pipeline (Routing, Retrieval, Guardrails), Quellen, Artefakte.
2. **generisch ein Zuhause für beliebige Agenten** wird — über den offenen **Agent Client
   Protocol (ACP)** kann jeder ACP-fähige Agent (Claude Code, Gemini CLI, Codex, eigene)
   angedockt werden. OPUS PRIME EX ist der erste, nicht der einzige Mieter.
3. **den vollen Funktionsumfang** liefert, den Nutzer:innen von Claude.ai und Google
   Antigravity kennen — Projekte anlegen, Dateien hochladen/erstellen/bearbeiten/
   herunterladen, Artefakte, Multi-Agent-Orchestrierung („Mission Control"), Terminal,
   Editor — **ohne Auslassung**.

**North-Star-Metrik:** „Time-to-First-Verified-Outcome" — wie schnell ein Mensch von
„leerem Projekt" zu einem **verifizierten, herunterladbaren Ergebnis** eines Agenten kommt.

---

## 1. Design- & Bau-Prinzipien (Non-Negotiables)

| # | Prinzip | Konsequenz |
|---|---------|-----------|
| 1 | **VS-Code-Designsprache** | Activity Bar · Side Bar · Editor Groups · Panel · Status Bar · Command Palette · Codicons · Theming-Tokens. Look & Feel = VS Code, Marke = unsere. |
| 2 | **Agent-agnostisch (ACP-first)** | Der Workbench ist ein **ACP-Client**; Agenten sind austauschbare ACP-*Server*. Kein Hardcoding auf OPUS PRIME EX. |
| 3 | **EU-first / DSGVO** | GCP `europe-west3`, Daten-Residency EU, kein Tracking ohne Consent, lokale/EU-Inferenz bevorzugt. Erbt die Haltung von OPUS PRIME EX. |
| 4 | **Security by design** | Jeder Agent + jede Tool-Ausführung läuft **sandboxed** (Container/gVisor); Least-Privilege; Datei-/Netz-Zugriff explizit gated. |
| 5 | **Ehrlich vor Über-Behauptung** | Keine erfundenen Fähigkeiten in der UI; Agent-Grenzen (z. B. RA/StB-Vorbehalt von OPUS PRIME EX) bleiben sichtbar. |
| 6 | **Spec-driven / Perfect-Twin** | Wie OPUS PRIME EX: Spec zuerst, Traceability, vier Gates grün vor Merge. |
| 7 | **Barrierefrei & mehrsprachig** | WCAG 2.2 AA, Tastatur-vollständig, i18n (DE/EN) ab Tag 1. |
| 8 | **Lokal-fähig** | Läuft als Desktop-App **und** im Browser; Kernfunktionen offline nutzbar (PWA/Electron). |

---

## 2. Referenz-Analyse — was wir übernehmen (mit Quellen)

| Vorbild | Was wir übernehmen | Was wir bewusst anders machen |
|---------|--------------------|-------------------------------|
| **VS Code** | Workbench-Layout, Monaco-Editor, Command Palette, Theming-System, Extension-Modell, Keybindings | Eigene Marke/Branding; kein MS-Telemetrie-Stack; auf Agenten zugeschnittene Surfaces |
| **Google Antigravity** | **Manager Surface / Mission Control** (mehrere async Agenten spawnen/beobachten), **Artifacts** (Pläne, Screenshots, Recordings) mit Inline-Feedback, Subagents, Hooks, Scheduled Tasks, 4 Oberflächen (App/CLI/SDK/IDE) | Nicht an ein einzelnes Modell (Gemini) gebunden; ACP-offen statt geschlossen |
| **Claude.ai** | **Projects** (System-Instruktionen + Knowledge), **Knowledge-Files**, **Artifacts** (Live-Preview-Seitenpanel, persistente Speicherung, MCP-Anbindung), Web-Search-Toggle, Research-Mode, Memory, Skills | Multi-Agent statt Single-Model; volle Datei-/IDE-Fähigkeiten |
| **Zed / ACP** | **Agent Client Protocol** als Anbindungsstandard (JSON-RPC über stdio; „LSP für Agenten"), ACP-Registry (Claude Code, Gemini CLI, Codex …) | Wir sind ACP-*Client-Host* + liefern OPUS PRIME EX als ACP-*Agent* |
| **Eclipse Theia** | **Fundament**: Framework für eigene IDEs (Monaco, modular, white-label, Web+Desktop, VS-Code-Extension-kompatibel) | — (siehe Architektur-Entscheidung §3.1) |

Quellen: [Antigravity (Google Devs Blog)](https://developers.googleblog.com/build-with-google-antigravity-our-new-agentic-development-platform/) ·
[Antigravity 2.0](https://mcp.directory/blog/antigravity-2-launch-google-io-2026) ·
[Agent Client Protocol](https://agentclientprotocol.com/get-started/introduction) ·
[Zed ACP](https://zed.dev/acp) ·
[Eclipse Theia](https://theia-ide.org/) ·
[Theia: Build your own IDE](https://theia-ide.org/docs/composing_applications/) ·
[Claude Projects](https://www.anthropic.com/news/projects) ·
[Claude Artifacts](https://support.claude.com/en/articles/9487310-what-are-artifacts-and-how-do-i-use-them).

---

## 3. Architektur

### 3.1 Fundament-Entscheidung (Build vs. Buy)

| Option | Pro | Contra | Urteil |
|--------|-----|--------|--------|
| **A. Eclipse Theia** (empfohlen) | Monaco + VS-Code-Look „for free"; **voll white-label** (Marke frei); VS-Code-Extension-kompatibel; **Web + Desktop** aus einer Codebase; EU-nahe Eclipse-Foundation-Governance; modular (jedes Teil ersetzbar) | Eigene Lernkurve; kleineres Ökosystem als VS Code | **GEWÄHLT** |
| B. VS-Code-Fork (wie Antigravity/Cursor/Windsurf) | Exakter VS-Code-Stack, größtes Ökosystem | Fork-Wartungslast; Marken-/Marketplace-Lizenzfragen (MS); schwerer „unser" | Verworfen (Branding/Recht) |
| C. code-server / openvscode-server | VS Code im Browser, schnell | Weniger Custom-Freiheit; an VS-Code-Release gekoppelt | Verworfen (zu wenig Kontrolle) |
| D. From scratch (Monaco + eigenes Workbench) | Maximale Kontrolle | Riesiger Aufwand, Rad-Neuerfindung | Verworfen (Aufwand) |

**Entscheidung:** **Theia** als Workbench-Shell; Marke/Theme = unser; agentische Surfaces
als **Theia-Extensions**. (Diese Entscheidung ist reversibel bis P1-Ende; sie ist die
größte offene Wette — siehe §13.)

### 3.2 Schichten (High-Level)

```
┌───────────────────────────────────────────────────────────────┐
│  PRESENTATION  — Theia-Workbench (Monaco, Surfaces, Theming)   │
│  Surfaces: Editor · Agent/Chat · Manager · Projects · Artifacts│
├───────────────────────────────────────────────────────────────┤
│  ORCHESTRATION — Agent-Host (ACP-Client) · Session/Thread-Mgr  │
│  MCP-Tool-Broker · Artifact-Store · Event-Bus (WebSocket)      │
├───────────────────────────────────────────────────────────────┤
│  AGENT RUNTIME — je Agent isolierter Prozess/Container (ACP)   │
│  OPUS PRIME EX (ACP-Wrapper) · beliebige ACP-Agenten           │
├───────────────────────────────────────────────────────────────┤
│  PLATFORM — Auth/OIDC · Tenancy · Storage (Projekte/Dateien)   │
│  Secrets · Sandbox (gVisor/Container) · Audit · Billing-Hooks  │
├───────────────────────────────────────────────────────────────┤
│  INFRA — GCP europe-west3 (Cloud Run/GKE) · DB · Object Store  │
└───────────────────────────────────────────────────────────────┘
```

### 3.3 Interop-Standards (Kern der Multi-Agent-Idee)

- **ACP (Agent Client Protocol)** — Anbindung *Editor ↔ Agent*. Der Workbench ist ACP-Host;
  jeder Agent ist ein ACP-Server (lokaler Subprozess über JSON-RPC/stdio **oder** remote).
  → **OPUS PRIME EX bekommt einen dünnen ACP-Wrapper** (`apps/acp-adapter`), der seine
  bestehende Orchestrator-Pipeline als ACP-Session exponiert.
- **MCP (Model Context Protocol)** — Anbindung *Agent ↔ Tools/Datenquellen*. Der Workbench
  betreibt einen **MCP-Tool-Broker**; Agenten deklarieren benötigte Tools, der Host gated
  Freigaben (Permission-Prompts).
- **LSP** — Sprachintelligenz im Editor (aus Theia).

### 3.4 Frontend/Backend-Stack (Vorschlag)

- **Frontend:** TypeScript, Theia-Extensions (React für Custom-Views), Monaco, Codicons,
  eigenes Theme-Paket (Design-Tokens aus `identity.json`-Analogon).
- **Backend:** Python (wiederverwendet OPUS-PRIME-EX-Kern) + ein schlanker **Gateway**
  (FastAPI/ASGI) für Auth, Projekt-/Datei-API, Artifact-Store, Event-Bus; Agenten laufen
  je in eigenem Sandbox-Prozess.
- **Transport:** WebSocket (Live-Streaming von Agent-Events/Tokens) + REST (CRUD).
- **Deploy:** GCP `europe-west3` — Cloud Run (Gateway/Frontend) + GKE/Sandbox-Pool für
  Agent-Runtimes; Object Storage (Dateien/Artefakte), Postgres (Metadaten), Secret Manager.

---

## 4. Produkt-Surfaces (die „Oberflächen" wie bei Antigravity)

| Surface | Zweck | Kernelemente |
|---------|-------|--------------|
| **S1 Workbench/Editor** | Dateien ansehen/bearbeiten | Monaco, Tabs, Editor-Groups, Diff, Minimap, Breadcrumbs |
| **S2 Explorer** | Projekt-/Dateibaum | Upload, Drag&Drop, Neu/Umbenennen/Löschen, Download, Kontextmenü |
| **S3 Agent/Chat-Panel** | 1:1 mit einem Agenten arbeiten | Streaming-Antworten, Quellen-/Guardrail-Anzeige (OPUS-PRIME-spezifisch), Tool-Calls sichtbar, „stop/redirect" |
| **S4 Agent Manager / Mission Control** | Mehrere Agenten async orchestrieren | Agent-Liste, Status (läuft/wartet/Feedback nötig), spawn/pause/kill, Vergleich, „Inbox" für Rückfragen |
| **S5 Projects & Knowledge** | Kontext bündeln | Projekt = System-Instruktion + Knowledge-Files + Einstellungen; pro Projekt eigener Agent-Satz |
| **S6 Artifacts** | Verifizierbare Ergebnisse | Live-Preview (Code/HTML/SVG/Mermaid/Markdown/PDF), Versionierung, Inline-Feedback, **Download/Export** |
| **S7 Terminal** | Shell-Zugriff (sandboxed) | Mehrere Terminals, Agent-getriebene Kommandos sichtbar & bestätigbar |
| **S8 Command Palette** | Alles per Tastatur | Fuzzy-Command-Suche, Agent-Aktionen, Datei-Sprung |
| **S9 Settings/Themes** | Personalisierung | Theme-Wechsel (Dark/Light/High-Contrast), Keybindings, Agent-Defaults, Sprache |
| **S10 Timeline/Audit** | Nachvollziehbarkeit | Wer/welcher Agent hat was wann getan; Export (DSGVO-Auskunft) |

---

## 5. Capability-Matrix — alles, was Nutzer:innen können müssen

> Anspruch: **nichts auslassen.** Diese Matrix ist die Abnahme-Checkliste für „Feature-Parität
> mit Claude.ai + Antigravity + IDE-Grundfunktionen".

**Projekte**
- [ ] Projekt anlegen/umbenennen/duplizieren/archivieren/löschen
- [ ] Projekt-System-Instruktion + Custom Instructions setzen
- [ ] Knowledge-Files hinzufügen/entfernen; pro-Projekt-Kontext
- [ ] Projekt teilen/berechtigen (RBAC), exportieren/importieren

**Dateien**
- [ ] **Hochladen** (Einzeln, Multi, Ordner, Drag&Drop, große Dateien/Chunked)
- [ ] **Erstellen** (neue Datei/Ordner, aus Vorlage, per Agent)
- [ ] **Bearbeiten** (Monaco, Diff, Auto-Save, Konfliktauflösung)
- [ ] **Herunterladen** (Datei, Ordner-als-ZIP, Artefakt, ganzer Workspace)
- [ ] Vorschau (PDF, Bild, Markdown, CSV/Tabelle, Notebook)
- [ ] Versionierung/History; Git-Integration (optional)

**Agenten**
- [ ] Agent aus Registry wählen/hinzufügen (ACP); eigenen Agent registrieren
- [ ] Mit Agent chatten (Streaming); Tool-Calls sehen & freigeben
- [ ] Mehrere Agenten parallel (Mission Control); Aufgaben zuweisen
- [ ] Subagents spawnen; Hooks; **Scheduled Tasks** (zeitgesteuert)
- [ ] Agent-Antwort verifizieren (Artifacts) + Inline-Feedback
- [ ] Agent-Grenzen/Compliance sichtbar (z. B. OPUS-PRIME-Disclaimer/Guardrails)

**Wissen & Suche**
- [ ] Web-Search-Toggle · Research-Mode (Multi-Quelle) · projektweite Suche
- [ ] MCP-Server anbinden (Tools/Datenquellen) mit Permission-Gate

**Ausgabe & Zusammenarbeit**
- [ ] Artifacts (Code/Doc/Diagramm/interaktiv) mit Live-Preview + Export
- [ ] Kommentare/Feedback; Freigabe-Workflows; Präsentationsmodus
- [ ] Teilen per Link (berechtigt), Kollaboration (später Realtime)

**Plattform/Konto**
- [ ] Login (OIDC/SSO), Profil, Team/Tenant, Rollen & Rechte
- [ ] Nutzung/Kosten sichtbar (Billing-Hooks), Kontingente
- [ ] DSGVO: Datenexport, Löschung, Consent-Management, Audit-Log

---

## 6. Multi-Agent-Plattformschicht („Zuhause für andere Agenten")

- **Agent-Registry** — Katalog verfügbarer Agenten (Name, Fähigkeiten, benötigte Tools/
  Permissions, Modell-/Kosten-Info, Herkunft/Signatur). ACP-Registry-kompatibel.
- **Agent-Lifecycle** — install → configure → start (sandboxed) → session → stop → uninstall.
- **Isolation** — jeder Agent in eigenem Container (gVisor/Firecracker); Datei-/Netz-/Tool-
  Zugriff nur über gebrokerte, gegateste Kanäle. Kein Agent sieht fremde Projekte.
- **Permission-Modell** — feingranular (Datei lesen/schreiben, Netz, Tool X, Ausgaben senden);
  Just-in-time-Prompts; auditiert.
- **Agent-SDK/Contract** — dünnes SDK, um einen beliebigen Agenten ACP-konform „einzuhausen"
  (Referenz: der OPUS-PRIME-EX-Adapter dient als Blaupause).
- **Marktplatz (später)** — kuratierte Agenten-/MCP-Server-Distribution; Review/Signatur.

---

## 7. Querschnitts-Themen (bewusst nicht ausgelassen)

| Thema | Anforderung |
|-------|-------------|
| **Security/Sandbox** | gVisor/Firecracker je Agent; Secrets nie im Agent-Kontext; egress-Filter; Supply-Chain-Signaturen (ACP/MCP-Server) |
| **Auth/Identity** | OIDC/OAuth2, SSO, MFA-fähig, Session-Härtung |
| **Tenancy** | Mandantentrennung (Daten, Compute, Audit); Fair-Use-Kontingente |
| **DSGVO/EU** | Daten-Residency EU; DPA-Vorlagen; Auskunft/Löschung/Portabilität; Consent-Layer; kein Tracking ohne Einwilligung |
| **Theming/Branding** | Design-Tokens (Farben/Typo) als SSoT; Dark/Light/High-Contrast; „white-label" pro Tenant |
| **Accessibility** | WCAG 2.2 AA; Tastatur-vollständig; Screenreader; reduzierte Bewegung |
| **i18n/L10n** | DE/EN ab Start; RTL-fähig; Zahlen-/Datumsformate |
| **Command Palette & Keybindings** | Jede Aktion per Palette erreichbar; anpassbare Keymaps (VS-Code-kompatibel) |
| **Telemetrie** | Opt-in, anonymisiert, EU-gehostet; klarer Consent |
| **Offline/Resilienz** | PWA/Desktop-Cache; graceful degradation ohne Agent/Netz |
| **Performance** | Editor-Latenz < 50 ms; Agent-Token-Streaming; Virtualisierung großer Bäume/Logs |
| **State/Persistence** | Projekt-/Session-/Layout-Persistenz; Wiederaufnahme nach Reload |
| **Observability** | strukturierte Logs, Traces, Health, SLOs; kein PII in Logs (erbt OPUS-PRIME-Regel) |

---

## 8. Tech-Stack & Repo-Struktur (Vorschlag)

**Neues Repo** (empfohlen — die Plattform ist größer als OPUS PRIME EX): `opus-deck`.
OPUS PRIME EX bleibt eigenes Repo und wird als **ACP-Agent** eingebunden.

```
opus-deck/
  apps/
    workbench/        # Theia-App (Frontend-Shell, Branding, Surfaces)
    gateway/          # ASGI-Gateway: Auth, Projekt-/Datei-API, Event-Bus
    acp-host/         # ACP-Client-Host + Session/Thread-Manager
    mcp-broker/       # MCP-Tool-Broker + Permission-Gate
  packages/
    ui-kit/           # Theme-Tokens, Codicon-Set, React-Views
    agent-sdk/        # „Einhausungs"-SDK (ACP-Konformität) + Referenz-Adapter
    artifacts/        # Artifact-Store + Renderer (Code/HTML/SVG/Mermaid/PDF)
  infra/              # GCP europe-west3 (Terraform/Cloud Run/GKE), CI/CD
  spec/               # Perfect-Twin-Specs (analog OPUS PRIME EX)
  docs/               # dieses Dokument + ADRs
```

**Gates (wie OPUS PRIME EX):** Lint · Typecheck (TS strict + mypy) · Unit/Integration ·
E2E (Playwright) · a11y-Check · spec_lint · CI grün vor Merge.

---

## 9. Semi-atomarer Meilensteinplan (Phasen → WI mit Akzeptanzkriterien)

> Jedes Work-Item (WI) ist klein, testbar, einzeln mergebar (analog M1…M18 in OPUS PRIME EX).
> „AK" = Akzeptanzkriterium.

### Phase P0 — Fundament & Skelett
- **WI-0.1** Repo `opus-deck`, CI-Kette, Lint/Typecheck/Test-Gates. *AK:* leerer Build grün in CI.
- **WI-0.2** Theia-App bootet mit Monaco + leerem Workbench. *AK:* App startet Web + Desktop.
- **WI-0.3** Branding/Theme-Paket (Design-Tokens, Dark/Light, Codicons, Logo). *AK:* Theme umschaltbar, Marke sichtbar.
- **WI-0.4** ADR-Prozess + Spec-Ordner (Perfect-Twin). *AK:* ADR-0001 „Theia als Fundament".

### Phase P1 — Editor & Dateien (IDE-Grundfähigkeit)
- **WI-1.1** Explorer mit Baum, Neu/Umbenennen/Löschen. *AK:* CRUD auf Dateien/Ordner.
- **WI-1.2** Upload (Einzel/Multi/Drag&Drop/Chunked). *AK:* 1 GB-Datei chunked hochladbar.
- **WI-1.3** Download (Datei, Ordner→ZIP, Workspace). *AK:* Ordner als ZIP herunterladbar.
- **WI-1.4** Monaco-Editing (Tabs, Diff, Auto-Save, Konflikt). *AK:* paralleles Edit + Diff.
- **WI-1.5** Vorschau-Renderer (PDF/Bild/Markdown/CSV). *AK:* PDF/CSV rendern read-only.

### Phase P2 — Gateway, Auth, Projekte
- **WI-2.1** Gateway (ASGI) + Object/DB-Storage. *AK:* Datei-/Projekt-CRUD persistent.
- **WI-2.2** Auth (OIDC), Session, RBAC-Grundgerüst. *AK:* Login + rollenbasierter Zugriff.
- **WI-2.3** Projekte (anlegen/…/löschen, System-Instruktion, Knowledge-Files). *AK:* Projekt mit Knowledge nutzbar.
- **WI-2.4** Multi-Tenancy + Mandantentrennung. *AK:* Tenant A sieht Tenant B nicht (Test).

### Phase P3 — Agent-Anbindung (ACP) + erster Agent
- **WI-3.1** ACP-Host (Client) + Session/Thread-Manager. *AK:* Dummy-ACP-Agent antwortet.
- **WI-3.2** **OPUS-PRIME-EX-ACP-Adapter** (`apps/acp-adapter` im OPUS-Repo). *AK:* Pipeline (Routing/Retrieval/Guardrails) über ACP sichtbar.
- **WI-3.3** Agent/Chat-Panel (S3): Streaming, Tool-Calls, Quellen/Guardrails. *AK:* echte OPUS-Antwort inkl. Disclaimer/Quellen im Panel.
- **WI-3.4** Permission-Gate für Tool-/Datei-Zugriff. *AK:* Just-in-time-Prompt + Audit.

### Phase P4 — Sandbox & Sicherheit
- **WI-4.1** Agent-Runtime je Container (gVisor/Firecracker). *AK:* Agent isoliert, kein Fremdprojekt-Zugriff.
- **WI-4.2** Secrets/Egress-Broker; Least-Privilege. *AK:* Agent ohne Freigabe kein Netz.
- **WI-4.3** MCP-Broker + Permission-UI. *AK:* MCP-Tool nur nach Freigabe nutzbar.

### Phase P5 — Artifacts & Verifizierbarkeit
- **WI-5.1** Artifact-Store + Versionierung. *AK:* Artefakt persistent + versioniert.
- **WI-5.2** Renderer (Code/HTML/SVG/Mermaid/Markdown/PDF) + Live-Preview. *AK:* Live-Preview + Export/Download.
- **WI-5.3** Inline-Feedback auf Artefakten → Agent. *AK:* Feedback fließt in Folgeschritt.

### Phase P6 — Mission Control (Multi-Agent)
- **WI-6.1** Agent-Registry + Lifecycle (install/start/stop). *AK:* zweiter Agent (z. B. Gemini/Claude CLI via ACP) andockbar.
- **WI-6.2** Manager-Surface (S4): mehrere async Agenten, Status, Inbox. *AK:* 2 Agenten parallel, Rückfragen-Inbox.
- **WI-6.3** Subagents · Hooks · **Scheduled Tasks**. *AK:* zeitgesteuerte Agent-Aufgabe läuft.
- **WI-6.4** Terminal (S7, sandboxed) + bestätigte Agent-Kommandos. *AK:* Agent-Shell-Kommando erst nach Bestätigung.

### Phase P7 — Plattform-Reife
- **WI-7.1** Billing-Hooks/Kontingente + Nutzungsanzeige. *AK:* Kosten je Tenant sichtbar.
- **WI-7.2** DSGVO-Toolkit (Export/Löschung/Consent/Audit-Export). *AK:* Datenauskunft + Löschung End-to-End.
- **WI-7.3** a11y (WCAG 2.2 AA) + i18n (DE/EN) vollständig. *AK:* a11y-Audit grün, UI zweisprachig.
- **WI-7.4** Command Palette + Keybinding-Editor vollständig. *AK:* jede Kernaktion per Palette.

### Phase P8 — GA & Marktplatz
- **WI-8.1** Agent-/MCP-Marktplatz (kuratiert, signiert). *AK:* dritter Agent aus Marktplatz installierbar.
- **WI-8.2** Realtime-Kollaboration (Mehrbenutzer-Projekt). *AK:* zwei Nutzer:innen gleichzeitig.
- **WI-8.3** Härtung, Last-/Pen-Test, SLOs, Runbooks. *AK:* Lasttest + Security-Review bestanden.
- **WI-8.4** Öffentliches GA (Docs, Onboarding, Demo-Tenant). *AK:* neuer Nutzer → verifiziertes Ergebnis in < 10 min.

---

## 10. Testing / QA / Definition of Done

- **Unit** (TS/py), **Integration** (Gateway/ACP/MCP), **E2E** (Playwright: „Projekt→Upload→
  Agent→Artefakt→Download"), **a11y** (axe), **Visual Regression** (Theme/Layout),
  **Security** (Sandbox-Escape-Tests, Permission-Fuzzing), **Load** (k6).
- **DoD je WI:** Spec aktualisiert · Tests grün · a11y unberührt · keine PII in Logs ·
  Demo-Pfad manuell verifiziert · gepusht mit grünen Gates.

---

## 11. Design-System / Branding (VS-Code-Sprache, eigene Marke)

- **Tokens als SSoT** (Analogon zu `identity.json`): Farben (inkl. VS-Code-Token-Mapping),
  Typografie (Grotesk + Mono), Spacing, Radius, Elevation, Motion.
- **Themes:** Dark (default), Light, High-Contrast; pro Tenant überschreibbar (white-label).
- **Icons:** Codicon-Set + eigene Agent-/Domain-Icons.
- **Motion:** dezent, `prefers-reduced-motion` respektiert.
- **Voice/Tone:** ruhig, präzise, ehrlich (erbt OPUS-PRIME-Haltung).

---

## 12. Risiken & Härtefälle (ehrlich)

| Risiko | Auswirkung | Gegenmaßnahme |
|--------|-----------|---------------|
| **Theia-Wette** falsch | Rebuild der Shell | Fundament-Entscheidung bis P1-Ende reversibel; ADR + Spike zuerst |
| **Sandbox-Escape** | Sicherheits-GAU | gVisor/Firecracker, Egress-Filter, Pen-Test-Gate vor GA |
| **ACP/MCP noch jung** | Breaking Changes | Adapter-Schicht kapseln; Version-Pinning; Contract-Tests |
| **Scope-Explosion** | Nie fertig | Strikte WI-Atomisierung; jede Phase liefert nutzbaren Stand |
| **Kosten (LLM/Compute)** | Unrentabel | Billing-Hooks/Kontingente ab P7; lokale/EU-Modelle bevorzugen |
| **DSGVO bei Multi-Tenant** | Rechtliches Risiko | Daten-Residency EU, DPA, Löschkonzept, Audit; Rechts-Review |
| **Feature-Parität „nichts auslassen"** | Überforderung | Capability-Matrix (§5) als Abnahme; Parität = P8-Ziel, nicht P1 |

---

## 13. Entscheidungen (Owner)

**Entschieden (Owner Yahya, 2026-07-07):**
1. ✅ **Fundament: Eclipse Theia** (bestätigt) — nächster Schritt Theia-Spike + Branding.
2. ✅ **Repo/Name: neues Repo `opus-deck`** (Arbeitstitel OPUS DECK); OPUS PRIME EX bleibt
   eigenes Repo und wird als ACP-Agent eingebunden.
3. ✅ **Web zuerst** — Browser-App (Cloud Run, EU); Desktop später aus derselben Theia-Codebase.

**Noch offen:**
4. **Hosting-Modell:** Self-hosted (on-prem/EU-Cloud) vs. SaaS-Multi-Tenant zuerst?
5. **Erste Fremd-Agenten:** welche ACP-Agenten neben OPUS PRIME EX (Claude Code, Gemini CLI …)?
6. **Monetarisierung:** intern (Tooling) vs. Produkt (Billing/Marktplatz) — beeinflusst P7/P8.

---

## 14. Nächster Schritt (konkret)

1. **ADR-0001** „Theia als Fundament" + **Spike** (WI-0.2: Theia bootet, Branding-Theme) —
   die einzige Wette, die vor allem anderen validiert gehört.
2. **ADR-0002** „ACP als Agent-Anbindung" + **OPUS-PRIME-EX-ACP-Adapter-Skizze** (WI-3.2).
3. Owner-Entscheidungen §13 klären → Phasen P0/P1 einplanen.

> **Ehrliche Einordnung:** Dies ist ein Plattform-Vorhaben (Monate, nicht Tage). Der Plan ist
> so geschnitten, dass **jede Phase einen real nutzbaren Stand** liefert — von „Editor+Dateien"
> (P1) über „OPUS PRIME EX visuell steuerbar" (P3) bis „Multi-Agent-Mission-Control" (P6).
> Nichts hier ist Marketing; alles ist als atomare, testbare Arbeit formuliert.
