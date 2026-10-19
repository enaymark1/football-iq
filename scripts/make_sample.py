"""Genera la muestra REAL y redistribuible de datasets/sample a partir del dataset completo.

No inventa nada: filtra transfermarkt-datasets (CC0) a 3 ligas y temporadas recientes.
Uso (desde la raíz, con el dataset completo ya descargado en datasets/raw):
    python scripts/make_sample.py
"""
import sys

import _bootstrap  # noqa: F401
import pandas as pd

from app.core.config import get_settings
from app.data.sources import transfermarkt

LEAGUES = ["GB1", "ES1", "ARG1"]  # Premier League, LaLiga y Liga Profesional (esta última solo trae resultados)
FIRST_SEASON = 2022


def main() -> int:
    settings = get_settings()
    src = settings.raw_data_dir / transfermarkt.SOURCE_NAME
    dst = settings.sample_data_dir / transfermarkt.SOURCE_NAME
    if not transfermarkt.available(src):
        print(f"Falta el dataset completo en {src}. Corré antes: python scripts/import_data.py --download")
        return 1
    raw = transfermarkt.read(src)
    games = raw["games"][raw["games"]["competition_id"].isin(LEAGUES) & (raw["games"]["season"] >= FIRST_SEASON)]
    apps = raw["appearances"][raw["appearances"]["game_id"].isin(games["game_id"])]
    clubs_ids = set(games["home_club_id"]) | set(games["away_club_id"])
    players = raw["players"][raw["players"]["player_id"].isin(apps["player_id"])]
    sample = {
        "competitions": raw["competitions"][raw["competitions"]["competition_id"].isin(LEAGUES)],
        "clubs": raw["clubs"][raw["clubs"]["club_id"].isin(clubs_ids)],
        "players": players,
        "games": games,
        "appearances": apps,
        "player_valuations": raw["player_valuations"][raw["player_valuations"]["player_id"].isin(players["player_id"])],
    }
    dst.mkdir(parents=True, exist_ok=True)
    for name, df in sample.items():
        df.to_csv(dst / f"{name}.csv.gz", index=False, compression="gzip")
        print(f"{name:18s} {len(df):>8,d} filas")
    print(f"Muestra guardada en {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
