"""Equipos: tabla por temporada, rendimiento local/visitante, forma, plantel y Elo."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.core.errors import DataUnavailableError, NotFoundError
from app.ml import match_model, registry
from app.repositories import meta as meta_repo
from app.repositories import players as players_repo
from app.repositories import teams as repo
from app.services.common import num


def list_teams(session: Session, league_id: int | None, q: str | None, active_only: bool) -> list[dict]:
    active_since = None
    if active_only:
        labels = meta_repo.season_labels(session)
        active_since = max(labels) if labels else None
    artifact = registry.try_load(match_model.MODEL_KEY)
    out = []
    for r in repo.list_teams(session, league_id, q, active_since):
        elo = artifact["teams"].get(r.id, {}).get("elo") if artifact else None
        out.append({"id": r.id, "name": r.name, "league_id": r.league_id, "league_name": r[3], "country": r[4],
                    "image_url": r.image_url, "league_image_url": r.league_image_url,
                    "last_season": r.last_season, "elo": round(elo, 1) if elo else None})
    return out


def _team_perspective(m: pd.DataFrame, team_id: int) -> pd.DataFrame:
    home = m["home_team_id"] == team_id
    out = pd.DataFrame({
        "match_id": m["id"], "date": pd.to_datetime(m["date"]), "season": m["season"], "league_name": m["league_name"],
        "venue": np.where(home, "home", "away"),
        "opponent_id": np.where(home, m["away_team_id"], m["home_team_id"]),
        "opponent": np.where(home, m["away_name"], m["home_name"]),
        "gf": np.where(home, m["home_goals"], m["away_goals"]),
        "ga": np.where(home, m["away_goals"], m["home_goals"]),
    })
    out["result"] = np.select([out["gf"] > out["ga"], out["gf"] == out["ga"]], ["W", "D"], "L")
    out["points"] = out["result"].map({"W": 3, "D": 1, "L": 0})
    return out


def _summary(df: pd.DataFrame) -> dict:
    n = len(df)
    return {"matches": n, "wins": int((df["result"] == "W").sum()), "draws": int((df["result"] == "D").sum()),
            "losses": int((df["result"] == "L").sum()), "goals_for": int(df["gf"].sum()),
            "goals_against": int(df["ga"].sum()), "points": int(df["points"].sum()),
            "points_per_match": round(float(df["points"].mean()), 2) if n else None,
            "goals_for_pm": round(float(df["gf"].mean()), 2) if n else None,
            "goals_against_pm": round(float(df["ga"].mean()), 2) if n else None}


def detail(session: Session, team_id: int) -> dict:
    found = repo.get_team(session, team_id)
    if not found:
        raise NotFoundError(f"No existe el equipo {team_id}.")
    team, league_name, country, league_image_url = found
    m = repo.team_matches(session, team_id)
    labels = meta_repo.season_labels(session)
    tp = _team_perspective(m, team_id) if not m.empty else pd.DataFrame()

    seasons = []
    if not tp.empty:
        for (season, league), g in tp.groupby(["season", "league_name"]):
            s = _summary(g)
            seasons.append({"season": int(season), "season_label": labels.get(int(season), str(season)),
                            "league_name": league, **s})
    latest = tp[tp["season"] == tp["season"].max()] if not tp.empty else tp
    splits = {"home": _summary(latest[latest["venue"] == "home"]), "away": _summary(latest[latest["venue"] == "away"])} \
        if not latest.empty else None
    recent = tp.tail(10).iloc[::-1] if not tp.empty else tp
    recent_list = [{"date": r.date.date(), "venue": r.venue, "opponent_id": int(r.opponent_id), "opponent": r.opponent,
                    "gf": int(r.gf), "ga": int(r.ga), "result": r.result} for r in recent.itertuples()]

    squad = []
    try:
        season = meta_repo.latest_player_season(session)
        frame = players_repo.season_frame(session, season)
        if not frame.empty:
            sq = frame[frame["team_id"] == team_id].sort_values("minutes", ascending=False)
            squad = [{"player_id": int(r.player_id), "name": r.name, "position": r.position, "age": num(r.age),
                      "image_url": r.image_url,
                      "minutes": int(r.minutes), "goals": int(r.goals), "assists": int(r.assists),
                      "rating": num(r.rating), "market_value_eur": num(r.market_value_eur)} for r in sq.itertuples()]
    except DataUnavailableError:  # todavía no hay estadísticas de jugadores importadas
        squad = []

    artifact = registry.try_load(match_model.MODEL_KEY)
    elo_history = None
    if artifact and team_id in artifact["elo_history"]:
        hist = artifact["elo_history"][team_id]
        elo_history = [{"date": d, "elo": e} for d, e in hist[-200:]]
    return {
        "team": {"id": team.id, "name": team.name, "league_id": team.league_id, "league_name": league_name,
                 "country": country, "stadium": team.stadium, "stadium_seats": team.stadium_seats,
                 "image_url": team.image_url, "league_image_url": league_image_url},
        "seasons": seasons, "latest_splits": splits, "recent_matches": recent_list, "squad": squad,
        "squad_note": None if squad else "No hay estadísticas de jugadores de este equipo en la última temporada "
                                         "(la fuente solo trae resultados para algunas ligas).",
        "elo_history": elo_history,
        "current_elo": round(artifact["teams"][team_id]["elo"], 1) if artifact and team_id in artifact["teams"] else None,
    }
