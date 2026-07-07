"""Dense-Embedding-Provider fuer das Hybrid-Retrieval (BM25 + Dense).

Erfuellt das Embedder-Protokoll aus src/rag/store.py. Produktive Wahl ist ein
**lokal** laufendes Modell (sentence-transformers): Die Inferenz erfolgt auf der
Maschine des Betreibers — es verlassen KEINE Anfrage-/Dokumenttexte den Rechner.
Das ist die datenschutzstaerkste Variante (staerker als "EU-gehostet": kein
Drittlandtransfer, keine Auftragsverarbeitung fuer das Embedding). Die Modellgewichte
werden einmalig vom Model-Hub geladen; danach ist der Betrieb offline moeglich.

Standardmaessig DEAKTIVIERT (BM25-only laeuft dependency-frei). Aktivierung ueber
config/embeddings.yaml; das Modell ist ein optionales Extra ("pip install .[embeddings]").

# SPEC: KNOWLEDGE_ARCHITECTURE.md §4.2 (Hybrid Retrieval BM25 + Dense, 0.5/0.5);
# PROJECT_INSTRUCTIONS EU-first/DSGVO (lokale Inferenz -> kein Datenabfluss)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from src.rag.store import Embedder
from src.shared.exceptions import ToolInputError

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_DEFAULT_CONFIG = _REPO_ROOT / "config" / "embeddings.yaml"
# Symmetrisches, mehrsprachiges Modell (inkl. Deutsch), CPU-tauglich. Konfigurierbar.
_DEFAULT_MODELL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class SentenceTransformerEmbedder:
    """Lokaler Embedder auf Basis von sentence-transformers (lazy geladen).

    Das Modell wird erst beim ersten embed()-Aufruf geladen, damit der Provider ohne
    installierte Schwergewichts-Abhaengigkeit konstruiert (und getestet) werden kann.
    """

    def __init__(self, modell: str = _DEFAULT_MODELL) -> None:
        self.modell = modell
        self._model: Any | None = None

    def _ensure_model(self) -> Any:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:  # optionales Extra [embeddings]
                raise ToolInputError(
                    'Dense-Embeddings benoetigen "sentence-transformers" '
                    '(pip install ".[embeddings]").'
                ) from exc
            self._model = SentenceTransformer(self.modell)
        return self._model

    def embed(self, text: str) -> tuple[float, ...]:
        vektor = self._ensure_model().encode(text, normalize_embeddings=True)
        return tuple(float(x) for x in vektor)


def load_embedding_config(pfad: Path = _DEFAULT_CONFIG) -> dict[str, Any]:
    """Read the embeddings config; empty dict if the file is absent."""
    if not pfad.exists():
        return {}
    daten = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    return daten if isinstance(daten, dict) else {}


def build_embedder(config: dict[str, Any] | None) -> Embedder | None:
    """Return a configured Embedder, or None when dense retrieval is disabled.

    Erwartet die geparste embeddings-Config. Fehlt sie oder ist enabled=false, laeuft
    das Retrieval als reines BM25 (kein Modell, keine Abhaengigkeit).
    """
    if not config or not config.get("enabled"):
        return None
    modell = str(config.get("modell") or _DEFAULT_MODELL)
    return SentenceTransformerEmbedder(modell)
