# OPUS PRIME EX — Backend-Image (Referenz-Web-UI + API) fuer Cloud Run (europe-west3).
#
# Datenresidenz/Sicherheit (bewusst):
#   - Korpus = eingecheckte Fixtures (data/fixtures). Der persoenliche Live-Snapshot
#     (korpus/snapshot.jsonl) ist gitignored und wird NICHT ins Image kopiert.
#   - Second Brain leer: brain/raw & brain/wiki sind gitignored -> KEIN persoenliches Wissen im Image.
#   - ANTHROPIC_API_KEY kommt zur LAUFZEIT aus Secret Manager (nie ins Image, nie ins Repo).
#   - Bind via PORT-Env (0.0.0.0:$PORT). Der Server hat KEINE eigene Auth -> Zugriffskontrolle
#     ueber die Cloud-Run-Exposition (privat/IAM empfohlen).
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Deps aus pyproject (Single Source) inkl. [vertex] fuer Gemini/Vertex-EU (der live nutzbare
# Provider). Manifest zuerst (Layer-Cache).
COPY pyproject.toml README.md ./
RUN pip install .[vertex]

# Laufzeit-Dateien (per _ROOT-relativem Pfad gelesen -> muessen im Arbeitsverzeichnis liegen).
# prompts/ = System-Prompt + Few-Shots (Request-Pfad!); review/ = coverage_matrix (Ingest).
COPY src ./src
COPY apps ./apps
COPY config ./config
COPY data ./data
COPY prompts ./prompts
COPY review ./review
COPY evals ./evals
COPY scripts ./scripts

# Gehirn: raw/wiki bleiben leer fuer PERSOENLICHES Wissen (gitignored, nie in die Cloud). Fuer die
# Demo-Suche NICHT-persoenliche Projekt-Seed-Karten einbacken (committet, Format via BrainStore).
RUN mkdir -p brain/raw brain/wiki && python scripts/seed_brain.py brain

# Cloud Run setzt PORT (Default hier 8080 fuer lokalen Container-Test)
ENV PORT=8080
EXPOSE 8080
CMD ["python", "apps/web/server.py"]
