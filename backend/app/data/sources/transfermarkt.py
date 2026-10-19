"""Fuente: transfermarkt-datasets (David Cariboo), licencia CC0 1.0.

Repositorio: https://github.com/dcaribou/transfermarkt-datasets
Kaggle:      https://www.kaggle.com/datasets/davidcariboo/player-scores

Los archivos son CSV comprimidos y públicos; no hace falta clave de API.
Para cambiar de fuente alcanza con escribir otro módulo que devuelva las mismas
tablas normalizadas que espera `app.data.pipeline`.
"""
from __future__ import annotations

import logging
import urllib.request
from pathlib import Path

import pandas as pd

log = logging.getLogger(__name__)

SOURCE_NAME = "transfermarkt"
BASE_URL = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data"
LICENSE = "CC0 1.0 (dominio público)"
HOMEPAGE = "https://github.com/dcaribou/transfermarkt-datasets"

# Columnas obligatorias de cada tabla. Si falta alguna, la importación se detiene.
REQUIRED_COLUMNS: dict[str, list[str]] = {
    "competitions": ["competition_id", "name", "type", "sub_type", "country_name", "confederation"],
    "clubs": ["club_id", "name", "domestic_competition_id", "stadium_name", "stadium_seats"],
    "players": ["player_id", "name", "image_url", "date_of_birth", "country_of_citizenship", "country_of_birth",
                "position", "sub_position", "foot", "height_in_cm", "current_club_id",
                "market_value_in_eur", "highest_market_value_in_eur", "url"],
    "games": ["game_id", "competition_id", "season", "round", "date", "home_club_id", "away_club_id",
              "home_club_goals", "away_club_goals", "home_club_name", "away_club_name", "competition_type"],
    "appearances": ["game_id", "player_id", "player_club_id", "date", "yellow_cards", "red_cards",
                    "goals", "assists", "minutes_played"],
    "player_valuations": ["player_id", "date", "market_value_in_eur"],
}


class SourceError(RuntimeError):
    pass


# --- Imágenes --------------------------------------------------------------------------
# Las fotos de jugadores vienen en el dataset (columna image_url). Los escudos y logos se
# arman con el patrón público del CDN de Transfermarkt. Las imágenes NO son parte de la
# licencia CC0: se muestran enlazadas (no se descargan ni redistribuyen) y tienen derechos
# de sus dueños. El frontend puede desactivarlas con VITE_SHOW_IMAGES=false.
IMAGE_CDN = "https://tmssl.akamaized.net/images"


def player_image(url: str | None) -> str | None:
    if not isinstance(url, str) or not url.startswith("https://") or "default" in url:
        return None  # sin foto real: el frontend muestra iniciales
    return url


def club_crest(club_id) -> str:
    return f"{IMAGE_CDN}/wappen/head/{int(club_id)}.png"


def competition_logo(competition_id: str) -> str:
    return f"{IMAGE_CDN}/logo/header/{competition_id.lower()}.png"


def download(target_dir: Path, *, force: bool = False, timeout: int = 120) -> list[Path]:
    """Descarga las tablas a `target_dir`. Si ya están, no las vuelve a bajar (salvo `force`)."""
    target_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for table in REQUIRED_COLUMNS:
        path = target_dir / f"{table}.csv.gz"
        if path.exists() and path.stat().st_size > 0 and not force:
            log.info("Ya existe %s, no se descarga", path.name)
        else:
            url = f"{BASE_URL}/{table}.csv.gz"
            log.info("Descargando %s", url)
            tmp = path.with_suffix(".part")
            try:
                with urllib.request.urlopen(url, timeout=timeout) as resp, open(tmp, "wb") as fh:
                    while chunk := resp.read(1 << 20):
                        fh.write(chunk)
            except Exception as exc:  # se informa con contexto, no se oculta
                tmp.unlink(missing_ok=True)
                raise SourceError(f"No se pudo descargar {url}: {exc}") from exc
            tmp.replace(path)
        paths.append(path)
    return paths


def available(source_dir: Path) -> bool:
    return all((source_dir / f"{t}.csv.gz").exists() for t in REQUIRED_COLUMNS)


def read(source_dir: Path) -> dict[str, pd.DataFrame]:
    """Lee y valida las tablas crudas."""
    tables: dict[str, pd.DataFrame] = {}
    for table, required in REQUIRED_COLUMNS.items():
        path = source_dir / f"{table}.csv.gz"
        if not path.exists():
            raise SourceError(f"Falta el archivo {path}")
        df = pd.read_csv(path, low_memory=False, encoding="utf-8")
        missing = [c for c in required if c not in df.columns]
        if missing:
            raise SourceError(f"{path.name}: faltan las columnas {missing}")
        tables[table] = df
        log.info("%s: %d filas", table, len(df))
    return tables
