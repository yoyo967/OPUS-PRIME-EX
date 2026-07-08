# Deploy — OPUS PRIME EX Backend auf Cloud Run (europe-west3)

> Runbook für das Backend-Image (Referenz-Web-UI + `/api/*`). Stand: 2026-07-08.
> Entscheidung „erst Backend + Fundament" (funktionsfähig + sicher, bevor öffentlich).

## Sicherheits- & Datenresidenz-Haltung (nicht verhandelbar)

- **Privat deployt** (`--no-allow-unauthenticated`): Zugriff nur mit Google-Identity-Token.
  Unauthentifiziert → **HTTP 403**. Der Server selbst hat **keine** eigene Auth.
- **Kein persönliches Wissen im Image:** Korpus = eingecheckte Fixtures (`data/fixtures`), der
  persönliche `korpus/snapshot.jsonl` ist gitignored und **nicht** im Image. Second Brain **leer**
  (`brain/raw|wiki` gitignored). Verifiziert: `/api/brain/list` → `{"docs": []}`.
- **Secret nie im Image/Repo:** `ANTHROPIC_API_KEY` liegt in **Secret Manager**
  (`anthropic-api-key`, user-managed Replikation **europe-west3**), zur Laufzeit via
  `--set-secrets` injiziert. Der Wert wird beim Anlegen aus `.env` gepiped, **nie ausgegeben**.
- **EU-first:** Region `europe-west3`, Gemini über Vertex AI in derselben Region.

## Live (Stand 2026-07-08) — **dauerhaft sicher (privat + Single-Origin-Proxy)**

Architektur: der Browser spricht **nur** mit der Workbench (ein Origin). Deren Node-Backend
(`@opus-deck/api-proxy`) leitet `/api/*` mit **Google-Identity-Token** ans **private** Backend
weiter. Kein Client-Token, kein CORS, keine oeffentliche LLM-API, kein offenes Terminal im Netz.

**Backend** `opus-prime-ex-backend` · `europe-west3` · Image `:v5` (Seed-Gehirn)
- `--no-allow-unauthenticated` → **privat** (unauth → 403). Nur die Workbench-Runtime-SA hat
  `roles/run.invoker`. `ANTHROPIC_API_KEY` aus Secret Manager. Kein `OPUS_API_TOKEN` mehr.

**Workbench** `opus-deck-workbench` · `europe-west3` · Image `:v5`
- `--no-allow-unauthenticated` → **privat**. Env `OPUS_BACKEND_URL` = Backend-URL. Panels
  same-origin (`/api`). `--port=3333 --session-affinity --cpu-boost`.

**Zugriff (owner-authentifiziert, kein oeffentlicher Link):**
```bash
gcloud run services proxy opus-deck-workbench --region=europe-west3 --port=8899
# -> http://localhost:8899 im Browser oeffnen (authentifiziert als dein gcloud-Konto)
```
**End-to-End verifiziert (durch den Tunnel):** unauth → 403; Panels laden 9 Modelle; Brain-Seed-
Suche liefert Treffer; Gemini antwortet durch die Guardrail-Pipeline.

> **Gotcha:** `--no-allow-unauthenticated` beim Redeploy entfernt eine bestehende `allUsers`-
> Invoker-Bindung aus einem frueheren Public-Deploy; IAM-Propagation dauert ~1 min (kurz noch 200).
> Pruefen: `gcloud run services get-iam-policy <svc> --region=europe-west3`.

### Offene Haertung (spaeter)
- Oeffentlicher Zugang mit Login (statt Tunnel) → **Voll-IAP + Load Balancer + agenticum.xyz**
  (Domain-DNS + OAuth-Consent). Bindet die offene Domain-Aufgabe ein.
- Dedizierte Least-Privilege-SA fuer die Workbench (statt Default-Editor-SA) — Defense-in-Depth.

## Build & Deploy (reproduzierbar)

```bash
# 1) Image bauen + nach Artifact Registry pushen
docker build -t opus-prime-ex-backend:v2 .
IMG=europe-west3-docker.pkg.dev/leadmachines-prod/opus/opus-prime-ex-backend:v2
docker tag opus-prime-ex-backend:v2 "$IMG" && docker push "$IMG"

# 2) Secret (einmalig; Wert aus .env, ohne Ausgabe)
gcloud secrets create anthropic-api-key --replication-policy=user-managed --locations=europe-west3
grep '^ANTHROPIC_API_KEY=' .env | sed 's/^ANTHROPIC_API_KEY=//' | tr -d '\r\n"' \
  | gcloud secrets versions add anthropic-api-key --data-file=-
gcloud secrets add-iam-policy-binding anthropic-api-key \
  --member="serviceAccount:805048455261-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

# 3) Privat deployen
gcloud run deploy opus-prime-ex-backend --image="$IMG" --region=europe-west3 \
  --no-allow-unauthenticated --set-secrets="ANTHROPIC_API_KEY=anthropic-api-key:latest" \
  --port=8080 --memory=1Gi --cpu=1 --max-instances=2 --min-instances=0
```

Hinweis Vertex: die Runtime-SA (`…-compute@`) hat `roles/editor` → Vertex-Zugriff inklusive.

## Verifikation

```bash
URL=https://opus-prime-ex-backend-805048455261.europe-west3.run.app
curl -s -o /dev/null -w '%{http_code}\n' "$URL/api/models"                 # -> 403 (privat)
TOK=$(gcloud auth print-identity-token)
curl -s -H "Authorization: Bearer $TOK" "$URL/api/models"                  # -> 9 Modelle
```

## Offen (bewusst als nächste Entscheidung)

- **Öffentliche Exposition / Browser-Auth-Schicht:** Damit die OPUS-DECK-Panels (Browser) das
  Backend erreichen, braucht es entweder öffentliche Exposition (dann **App-Auth-Schicht** gegen
  Missbrauch — Kostenschutz für den Secret-Key) oder IAP / einen authentifizierenden Proxy.
  **Nicht** einfach `--allow-unauthenticated` ohne Schutz. Bewusste, separate Entscheidung.
- Korpus-Tiefe in der Cloud (aktuell Fixtures) — echter Korpus nur mit geklärter Datenresidenz.
- Cloud-GPU-Gemma-Endpoint (`$GEMMA_REMOTE_HOST`) — separater Infra-Schritt.
