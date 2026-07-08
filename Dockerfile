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

# Deps aus pyproject (Single Source): pyyaml + anthropic. Manifest zuerst (Layer-Cache).
COPY pyproject.toml README.md ./
RUN pip install .

# Laufzeit-Dateien (per _ROOT-relativem Pfad gelesen -> muessen im Arbeitsverzeichnis liegen)
COPY src ./src
COPY apps ./apps
COPY config ./config
COPY data ./data
COPY evals ./evals

# Leeres Gehirn (persoenliche Inhalte bleiben lokal/gitignored)
RUN mkdir -p brain/raw brain/wiki

# Cloud Run setzt PORT (Default hier 8080 fuer lokalen Container-Test)
ENV PORT=8080
EXPOSE 8080
CMD ["python", "apps/web/server.py"]
