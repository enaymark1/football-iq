"""Limpieza y normalización: tablas crudas de la fuente -> tablas internas.

Pasos: validar columnas (lo hace la fuente), limpiar texto y tipos, controlar
faltantes, detectar duplicados, asignar ids internos, agregar estadísticas por
jugador y temporada, y armar un informe de calidad con todo lo que se descartó.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from app.data.sources import transfermarkt
from app.services.metrics import add_derived_metrics, compute_ratings

LEAGUE_NAMES = {
    "GB1": "Premier League", "ES1": "LaLiga", "IT1": "Serie A", "L1": "Bundesliga", "FR1": "Ligue 1",
    "PO1": "Liga Portugal", "NL1": "Eredivisie", "BE1": "Jupiler Pro League", "TR1": "Süper Lig",
    "SC1": "Scottish Premiership", "RU1": "Premier Liga (RUS)", "UKR1": "Premier Liga (UKR)",
    "GR1": "Super League 1", "DK1": "Superliga (DEN)", "ARG1": "Liga Profesional (ARG)",
    "BRA1": "Brasileirão Série A", "MLS1": "MLS", "MEX1": "Liga MX", "SA1": "Saudi Pro League",
    "A1": "Bundesliga (AUT)", "C1": "Super League (SUI)", "JAP1": "J1 League", "RSK1": "K League 1",
    "KR1": "SuperSport HNL", "NO1": "Eliteserien", "SE1": "Allsvenskan", "PL1": "Ekstraklasa",
    "RO1": "SuperLiga (ROU)", "SER1": "Super Liga Srbije", "TS1": "Chance Liga", "AUS1": "A-League Men",
}
POSITION_MAP = {"Goalkeeper": "Goalkeeper", "Defender": "Defender", "Midfield": "Midfield", "Attack": "Attack"}


@dataclass
class ImportResult:
    tables: dict[str, pd.DataFrame]
    report: dict = field(default_factory=dict)


def clean_text(s: pd.Series) -> pd.Series:
    """Saca espacios duros y espacios repetidos; vacío -> None."""
    out = s.astype("string").str.replace(" ", " ", regex=False).str.strip()
    out = out.str.replace(re.compile(r"\s+"), " ", regex=True)
    return out.where(out.notna() & (out != ""), None)


def _missing_pct(df: pd.DataFrame, cols: list[str]) -> dict[str, float]:
    return {c: round(float(df[c].isna().mean() * 100), 2) for c in cols if c in df.columns}


def season_label(year: int, calendar_year: bool = False) -> str:
    return str(year) if calendar_year else f"{year}/{str(year + 1)[-2:]}"


def build(raw: dict[str, pd.DataFrame], *, source: str, first_player_season: int) -> ImportResult:
    report: dict = {"source": source, "tables": {}, "dropped": {}, "coverage": {}, "missing_pct": {}}

    # 1. Ligas: solo ligas domésticas de primera división.
    comps = raw["competitions"]
    leagues = comps[comps["type"] == "domestic_league"].drop_duplicates("competition_id").copy()
    leagues["source_id"] = leagues["competition_id"].astype(str)
    leagues["name"] = [
        LEAGUE_NAMES.get(cid, str(n).replace("-", " ").title())
        for cid, n in zip(leagues["source_id"], leagues["name"])
    ]
    leagues = leagues.sort_values("source_id").reset_index(drop=True)
    leagues["id"] = np.arange(1, len(leagues) + 1)
    leagues["country"] = clean_text(leagues["country_name"])
    leagues["confederation"] = clean_text(leagues["confederation"])
    leagues["tier"] = clean_text(leagues["sub_type"])
    leagues["source"] = source
    leagues["image_url"] = [transfermarkt.competition_logo(c) for c in leagues["source_id"]]
    league_map = dict(zip(leagues["source_id"], leagues["id"]))

    # 2. Partidos de esas ligas.
    games = raw["games"].copy()
    n_games_raw = len(games)
    games = games[games["competition_id"].isin(league_map)]
    dup_games = int(games["game_id"].duplicated().sum())
    games = games.drop_duplicates("game_id")
    games["date"] = pd.to_datetime(games["date"], errors="coerce")
    bad = games["date"].isna() | games["home_club_goals"].isna() | games["away_club_goals"].isna() \
        | games["home_club_id"].isna() | games["away_club_id"].isna() | (games["home_club_id"] == games["away_club_id"])
    report["dropped"]["matches_invalid"] = int(bad.sum())
    report["dropped"]["matches_duplicated"] = dup_games
    games = games[~bad].copy()
    games["season"] = games["season"].astype(int)
    for c in ("home_club_id", "away_club_id", "home_club_goals", "away_club_goals"):
        games[c] = games[c].astype(int)
    games["league_id"] = games["competition_id"].map(league_map)

    # 3. Equipos: los que jugaron algún partido de liga.
    clubs = raw["clubs"].drop_duplicates("club_id").set_index("club_id")
    side = pd.concat([
        games[["home_club_id", "home_club_name", "league_id", "date", "season"]]
        .set_axis(["club_id", "name", "league_id", "date", "season"], axis=1),
        games[["away_club_id", "away_club_name", "league_id", "date", "season"]]
        .set_axis(["club_id", "name", "league_id", "date", "season"], axis=1),
    ])
    latest = side.sort_values("date").groupby("club_id").tail(1).set_index("club_id")
    teams = pd.DataFrame(index=latest.index)
    teams["name"] = clean_text(clubs["name"].reindex(teams.index).fillna(latest["name"]))
    teams["name"] = teams["name"].fillna(clean_text(latest["name"])).fillna(pd.Series("Club " + teams.index.astype(str), index=teams.index))
    teams["league_id"] = latest["league_id"]  # liga del último partido jugado
    teams["stadium"] = clean_text(clubs["stadium_name"].reindex(teams.index))
    teams["stadium_seats"] = pd.to_numeric(clubs["stadium_seats"].reindex(teams.index), errors="coerce")
    teams = teams.reset_index().rename(columns={"club_id": "source_id"}).sort_values("source_id").reset_index(drop=True)
    teams["id"] = np.arange(1, len(teams) + 1)
    teams["source"] = source
    teams["image_url"] = [transfermarkt.club_crest(c) for c in teams["source_id"]]
    team_map = dict(zip(teams["source_id"], teams["id"]))
    teams["source_id"] = teams["source_id"].astype(str)

    games = games.sort_values(["date", "game_id"]).reset_index(drop=True)
    games["id"] = np.arange(1, len(games) + 1)
    games["home_team_id"] = games["home_club_id"].map(team_map)
    games["away_team_id"] = games["away_club_id"].map(team_map)

    # 4. Apariciones en esos partidos -> estadísticas por jugador y temporada.
    apps = raw["appearances"].copy()
    n_apps_raw = len(apps)
    apps = apps[apps["game_id"].isin(games["game_id"])]
    dup_apps = int(apps.duplicated(["game_id", "player_id"]).sum())
    apps = apps.drop_duplicates(["game_id", "player_id"])
    g = games.set_index("game_id")[["season", "date", "home_club_id", "away_club_id", "home_club_goals",
                                     "away_club_goals", "league_id"]]
    apps = apps.drop(columns=["date"]).join(g, on="game_id")  # la fecha válida es la del partido
    is_home = apps["player_club_id"] == apps["home_club_id"]
    is_away = apps["player_club_id"] == apps["away_club_id"]
    report["dropped"]["appearances_club_not_in_match"] = int((~(is_home | is_away)).sum())
    report["dropped"]["appearances_duplicated"] = dup_apps
    apps = apps[is_home | is_away].copy()
    is_home = apps["player_club_id"] == apps["home_club_id"]
    apps["minutes_played"] = pd.to_numeric(apps["minutes_played"], errors="coerce").fillna(0).clip(0, 130)
    report["dropped"]["appearances_zero_minutes"] = int((apps["minutes_played"] <= 0).sum())
    apps = apps[apps["minutes_played"] > 0]
    report["coverage"]["matches_with_appearances_pct"] = round(
        float(games["game_id"].isin(apps["game_id"]).mean() * 100), 2)
    # cobertura de apariciones por liga y temporada (para detectar huecos de la fuente)
    cov = games.assign(has=games["game_id"].isin(apps["game_id"])).groupby(["competition_id", "season"])["has"].mean()
    report["coverage"]["low_appearance_coverage"] = [
        {"league": k[0], "season": int(k[1]), "pct": round(float(v * 100), 1)} for k, v in cov.items() if v < 0.9
    ]
    apps = apps[apps["season"] >= first_player_season].copy()
    apps["gf"] = np.where(is_home.loc[apps.index], apps["home_club_goals"], apps["away_club_goals"])
    apps["ga"] = np.where(is_home.loc[apps.index], apps["away_club_goals"], apps["home_club_goals"])
    apps["points"] = np.select([apps["gf"] > apps["ga"], apps["gf"] == apps["ga"]], [3, 1], 0)
    apps["m60"] = (apps["minutes_played"] >= 60).astype(int)
    apps["cs"] = ((apps["ga"] == 0) & (apps["m60"] == 1)).astype(int)
    for c in ("goals", "assists", "yellow_cards", "red_cards"):
        apps[c] = pd.to_numeric(apps[c], errors="coerce").fillna(0).astype(int)

    # partidos de liga de cada club en cada temporada (para el % de minutos)
    club_season_matches = side.groupby(["club_id", "season"]).size()

    stint = apps.groupby(["player_id", "season", "player_club_id"]).agg(
        minutes=("minutes_played", "sum"), league_id=("league_id", "last")).reset_index()
    stint["club_matches"] = club_season_matches.reindex(
        pd.MultiIndex.from_frame(stint[["player_club_id", "season"]])).to_numpy()
    primary = stint.sort_values("minutes").groupby(["player_id", "season"]).tail(1).set_index(["player_id", "season"])
    stint_agg = stint.groupby(["player_id", "season"]).agg(
        teams_count=("player_club_id", "nunique"), team_matches=("club_matches", "sum"))

    stats = apps.groupby(["player_id", "season"]).agg(
        matches=("game_id", "count"), minutes=("minutes_played", "sum"), goals=("goals", "sum"),
        assists=("assists", "sum"), yellow_cards=("yellow_cards", "sum"), red_cards=("red_cards", "sum"),
        team_goals_for=("gf", "sum"), team_goals_against=("ga", "sum"), team_points=("points", "sum"),
        clean_sheets=("cs", "sum"), matches_60=("m60", "sum"),
        first_date=("date", "min"), last_date=("date", "max"),
    )
    stats = stats.join(stint_agg).join(primary[["player_club_id", "league_id"]])
    stats = stats.reset_index()
    stats["minutes"] = stats["minutes"].astype(int)

    # 5. Jugadores con al menos una temporada importada.
    players = raw["players"].drop_duplicates("player_id").copy()
    report["dropped"]["players_duplicated"] = int(raw["players"]["player_id"].duplicated().sum())
    players = players[players["player_id"].isin(stats["player_id"])].copy()
    report["dropped"]["stats_unknown_player"] = int((~stats["player_id"].isin(players["player_id"])).sum())
    stats = stats[stats["player_id"].isin(players["player_id"])]
    players = players.sort_values("player_id").reset_index(drop=True)
    players["id"] = np.arange(1, len(players) + 1)
    player_map = dict(zip(players["player_id"], players["id"]))
    players["name"] = clean_text(players["name"])
    players["date_of_birth"] = pd.to_datetime(players["date_of_birth"], errors="coerce")
    players["nationality"] = clean_text(players["country_of_citizenship"])
    players["country_of_birth"] = clean_text(players["country_of_birth"])
    players["position"] = players["position"].map(POSITION_MAP)
    players["sub_position"] = clean_text(players["sub_position"])
    players["foot"] = clean_text(players["foot"])
    players["height_cm"] = pd.to_numeric(players["height_in_cm"], errors="coerce").where(lambda x: x.between(140, 215))
    players["current_team_id"] = players["current_club_id"].map(team_map)
    players["highest_market_value_eur"] = pd.to_numeric(players["highest_market_value_in_eur"], errors="coerce")
    players["profile_url"] = clean_text(players["url"])
    players["image_url"] = [transfermarkt.player_image(u) for u in players["image_url"]]

    # 6. Valoraciones de mercado (historial).
    vals = raw["player_valuations"].copy()
    vals["date"] = pd.to_datetime(vals["date"], errors="coerce")
    vals["value_eur"] = pd.to_numeric(vals["market_value_in_eur"], errors="coerce")
    vals = vals[vals["player_id"].isin(player_map)]
    bad_vals = vals["date"].isna() | vals["value_eur"].isna() | (vals["value_eur"] <= 0)
    report["dropped"]["valuations_invalid"] = int(bad_vals.sum())
    vals = vals[~bad_vals]
    report["dropped"]["valuations_duplicated"] = int(vals.duplicated(["player_id", "date"]).sum())
    vals = vals.sort_values(["player_id", "date"]).drop_duplicates(["player_id", "date"], keep="last")

    last_val = vals.groupby("player_id").tail(1).set_index("player_id")
    players["market_value_eur"] = players["player_id"].map(last_val["value_eur"])
    players["market_value_date"] = players["player_id"].map(last_val["date"])

    # valor registrado al terminar y al empezar cada temporada (sin mirar el futuro para "start")
    stats = stats.sort_values("last_date")
    vs = vals.sort_values("date")[["player_id", "date", "value_eur"]]
    end = pd.merge_asof(
        stats.assign(key=stats["last_date"] + pd.Timedelta(days=45)).sort_values("key"),
        vs.rename(columns={"date": "vdate"}), left_on="key", right_on="vdate", by="player_id", direction="backward",
    )
    end_ok = (end["vdate"] >= end["last_date"] - pd.Timedelta(days=180))
    end["market_value_end_eur"] = end["value_eur"].where(end_ok)
    start = pd.merge_asof(
        end.drop(columns=["value_eur", "vdate", "key"]).sort_values("first_date"),
        vs.rename(columns={"date": "vdate"}), left_on="first_date", right_on="vdate", by="player_id",
        direction="backward",
    )
    start_ok = start["vdate"] >= start["first_date"] - pd.Timedelta(days=400)
    start["market_value_start_eur"] = start["value_eur"].where(start_ok)
    stats = start.drop(columns=["value_eur", "vdate"])

    dob = stats["player_id"].map(players.set_index("player_id")["date_of_birth"])
    stats["age"] = ((stats["last_date"] - dob).dt.days / 365.25).round(1)
    stats["position"] = stats["player_id"].map(players.set_index("player_id")["position"])
    stats["team_id"] = stats["player_club_id"].map(team_map)
    stats["player_id"] = stats["player_id"].map(player_map)
    stats = add_derived_metrics(stats)
    stats = compute_ratings(stats)
    stats = stats.sort_values(["season", "player_id"]).reset_index(drop=True)
    stats["id"] = np.arange(1, len(stats) + 1)

    vals["player_id"] = vals["player_id"].map(player_map)
    vals = vals.reset_index(drop=True)
    vals["id"] = np.arange(1, len(vals) + 1)

    calendar_leagues = {"ARG1", "BRA1", "MLS1", "JAP1", "RSK1", "NO1", "SE1"}
    season_years = sorted(set(games["season"]))
    seasons = pd.DataFrame({"year": season_years, "label": [season_label(y) for y in season_years]})

    players["source"] = source
    players["source_id"] = players["player_id"].astype(str)
    games["source"] = source
    games["source_id"] = games["game_id"].astype(str)
    games["round"] = clean_text(games["round"])

    tables = {
        "leagues": leagues[["id", "source", "source_id", "name", "country", "confederation", "tier", "image_url"]],
        "seasons": seasons,
        "teams": teams[["id", "source", "source_id", "name", "league_id", "stadium", "stadium_seats", "image_url"]],
        "players": players[["id", "source", "source_id", "name", "date_of_birth", "nationality", "country_of_birth",
                            "position", "sub_position", "foot", "height_cm", "current_team_id", "market_value_eur",
                            "market_value_date", "highest_market_value_eur", "profile_url", "image_url"]],
        "matches": games[["id", "source", "source_id", "league_id", "season", "date", "round", "home_team_id",
                          "away_team_id"]].assign(home_goals=games["home_club_goals"], away_goals=games["away_club_goals"]),
        "player_season_stats": stats[[
            "id", "player_id", "season", "team_id", "league_id", "teams_count", "age", "matches", "minutes", "goals",
            "assists", "yellow_cards", "red_cards", "team_matches", "team_goals_for", "team_goals_against",
            "team_points", "clean_sheets", "matches_60", "goals_p90", "assists_p90", "goal_contrib_p90", "cards_p90",
            "minutes_share", "goal_involvement_share", "team_ppm", "team_ga_pm", "clean_sheet_rate",
            "market_value_start_eur", "market_value_end_eur", "rating", "rating_reliability"]],
        "valuations": vals[["id", "player_id", "date", "value_eur"]],
    }
    for name in ("players", "matches", "valuations"):
        for col in ("date_of_birth", "market_value_date", "date"):
            if col in tables[name].columns:
                tables[name] = tables[name].assign(**{col: pd.to_datetime(tables[name][col]).dt.date})

    report["tables"] = {
        "matches": {"raw": n_games_raw, "imported": len(games)},
        "appearances": {"raw": n_apps_raw, "aggregated_rows": int(len(apps))},
        **{k: {"imported": len(v)} for k, v in tables.items() if k != "matches"},
    }
    report["missing_pct"] = {
        "players": _missing_pct(tables["players"], ["date_of_birth", "nationality", "position", "foot", "height_cm",
                                                    "market_value_eur", "current_team_id"]),
        "player_season_stats": _missing_pct(tables["player_season_stats"], ["age", "market_value_end_eur",
                                                                             "market_value_start_eur", "rating"]),
    }
    report["coverage"]["players_with_market_value_pct"] = round(float(players["market_value_eur"].notna().mean() * 100), 2)
    report["coverage"]["leagues"] = [
        {"league": LEAGUE_NAMES.get(cid, cid), "code": cid, "first_season": int(s.min()), "last_season": int(s.max()),
         "matches": int(len(s))}
        for cid, s in games.groupby("competition_id")["season"]
    ]
    report["calendar_year_leagues"] = sorted(calendar_leagues & set(league_map))
    report["date_range"] = {"first_match": str(games["date"].min().date()), "last_match": str(games["date"].max().date())}
    report["first_player_season"] = first_player_season
    return ImportResult(tables=tables, report=report)
