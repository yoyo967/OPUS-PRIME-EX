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

## Live (Stand 2026-07-08)

- Service: `opus-prime-ex-backend` · Region `europe-west3` · Projekt `leadmachines-prod`
- URL (privat): `https://opus-prime-ex-backend-805048455261.europe-west3.run.app`
- Image: `europe-west3-docker.pkg.dev/leadmachines-prod/opus/opus-prime-ex-backend:v2`
- Revision `…-00002-wvc`, `--memory=1Gi --max-instances=2 --min-instances=0` (skaliert auf 0).
- **End-to-End verifiziert:** authentifiziert → 9 Modelle; `/api/frage` mit `gemini-2.5-flash`
  liefert eine echte Antwort **durch die volle Guardrail-Pipeline** (G1/G3 feuern).
  Anthropic-Modelle: erst live, wenn Guthaben hinterlegt ist (Pipeline läuft trotzdem sichtbar).

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
