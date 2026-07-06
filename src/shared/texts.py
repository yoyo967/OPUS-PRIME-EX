"""Loader for UI/output strings (German canonical, English fallback).

# SPEC: CLAUDE.md §6 (German UI/output strings live in src/shared/i18n/de.yaml;
# English fallback file maintained in parallel)
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml

_I18N_DIR = Path(__file__).parent / "i18n"


@lru_cache(maxsize=4)
def _load(sprache: str) -> dict[str, str]:
    pfad = _I18N_DIR / f"{sprache}.yaml"
    with pfad.open(encoding="utf-8") as handle:
        loaded: dict[str, str] = yaml.safe_load(handle)
    return loaded


def text(key: str, sprache: str = "de") -> str:
    """Return the localized string; fall back to English, then raise KeyError."""
    strings = _load(sprache)
    if key in strings:
        return strings[key]
    return _load("en")[key]
