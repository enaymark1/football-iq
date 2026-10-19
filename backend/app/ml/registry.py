"""Guardar y cargar artefactos entrenados (joblib). Se cargan una vez y se reutilizan."""
from __future__ import annotations

from pathlib import Path
from threading import Lock

import joblib

from app.core.config import get_settings
from app.core.errors import ModelNotTrainedError

_CACHE: dict[str, tuple[float, object]] = {}
_LOCK = Lock()


def artifact_path(key: str, models_dir: Path | None = None) -> Path:
    return (models_dir or get_settings().models_dir) / f"{key}.joblib"


def save(key: str, artifact: object, models_dir: Path | None = None) -> Path:
    path = artifact_path(key, models_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, path, compress=3)
    with _LOCK:
        _CACHE.pop(str(path), None)
    return path


def load(key: str, models_dir: Path | None = None):
    """Carga el artefacto; si el archivo cambió (re-entrenamiento) lo vuelve a leer."""
    path = artifact_path(key, models_dir)
    if not path.exists():
        raise ModelNotTrainedError(f"El modelo '{key}' no está entrenado. Corré scripts/train_models.py.")
    mtime = path.stat().st_mtime
    with _LOCK:
        cached = _CACHE.get(str(path))
        if cached and cached[0] == mtime:
            return cached[1]
    artifact = joblib.load(path)
    with _LOCK:
        _CACHE[str(path)] = (mtime, artifact)
    return artifact


def try_load(key: str, models_dir: Path | None = None):
    try:
        return load(key, models_dir)
    except ModelNotTrainedError:
        return None
