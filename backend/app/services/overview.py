"""Dashboard: indicadores y agregados calculados sobre los datos importados."""
from __future__ import annotations

import pandas as pd
from sqlalchemy.orm import Session

from app.repositories import meta as meta_repo
from app.repositories import players as players_repo
from app.repositories import teams as teams_repo
from app.services.common import num

TOP_RATING_MIN_MINUTES = 1500


def _top(df: pd.DataFrame, col: str, n: int = 10) -> list[dict]:
    t = df[df[col].notna()].sort_values(col, ascending=False).head(n)
    return [{"player_id": int(r.player_id), "name": r.name, "team_name": r.team_name, "league_name": r.league_name,
             "image_url": r.image_url, "team_image_url": r.team_image_url,
             "position": r.position, "age": num(r.age), "minutes": int(r.minutes), "rating": num(r.rating),
             "market_value_eur": num(r.market_value_eur), "goals": int(r.goals), "assists": int(r.assists)}
            for r in t.itertuples()]


def overview(session: Session, season: int | None) -> dict:
    season = meta_repo.resolve_season(session, season)
    labels = meta_repo.season_labels(session)
    df = players_repo.season_frame(session, season)
    matches = teams_repo.matches_frame(session)
    season_matches = matches[matches["season"] == season]
    teams_in_season = pd.unique(pd.concat([season_matches["home_team_id"], season_matches["away_team_id"]]))
    valued = df["market_value_eur"].notna()

    kpis = {
        "players": int(len(df)), "teams": int(len(teams_in_season)),
        "teams_with_player_stats": int(df["team_id"].nunique()),
        "average_age": num(round(df["age"].mean(), 1)),
        "total_market_value_eur": num(df.loc[valued, "market_value_eur"].sum()),
        "players_with_market_value": int(valued.sum()),
        "matches": int(len(season_matches)), "leagues_with_player_stats": int(df["league_id"].nunique()),
    }

    positions = df["position"].fillna("Sin dato").value_counts()
    bins = list(range(15, 43, 2))
    age_hist = pd.cut(df["age"], bins=bins, right=False).value_counts().sort_index()

    league_images = {lg["id"]: lg["image_url"] for lg in meta_repo.leagues_with_counts(session)}
    leagues = []
    for (lid, lname), g in df.groupby(["league_id", "league_name"]):
        lm = season_matches[season_matches["league_id"] == lid]
        leagues.append({
            "league_id": int(lid), "league_name": lname, "players": int(len(g)),
            "image_url": league_images.get(int(lid)),
            "average_age": num(round(g["age"].mean(), 1)),
            "median_market_value_eur": num(g["market_value_eur"].median()),
            "total_market_value_eur": num(g["market_value_eur"].sum()),
            "goals_per_match": num(round((lm["home_goals"] + lm["away_goals"]).mean(), 2)) if len(lm) else None,
            "home_win_pct": num(round(float((lm["home_goals"] > lm["away_goals"]).mean() * 100), 1)) if len(lm) else None,
            "matches": int(len(lm)),
        })
    leagues.sort(key=lambda x: -(x["total_market_value_eur"] or 0))

    # Evolución temporal: goles por partido y % de victorias locales por temporada (ligas con 4+ temporadas).
    long_leagues = matches.groupby("league_id")["season"].nunique()
    hist = matches[matches["league_id"].isin(long_leagues[long_leagues >= 4].index)]
    evolution = []
    for s, g in hist.groupby("season"):
        evolution.append({"season": int(s), "season_label": labels.get(int(s), str(s)),
                          "goals_per_match": round(float((g["home_goals"] + g["away_goals"]).mean()), 3),
                          "home_win_pct": round(float((g["home_goals"] > g["away_goals"]).mean() * 100), 2),
                          "draw_pct": round(float((g["home_goals"] == g["away_goals"]).mean() * 100), 2),
                          "matches": int(len(g))})

    return {
        "season": season, "season_label": labels.get(season, str(season)),
        "available_seasons": [{"year": s, "label": labels.get(s, str(s))} for s in meta_repo.player_seasons(session)],
        "kpis": kpis,
        "positions": [{"position": k, "players": int(v)} for k, v in positions.items()],
        "age_distribution": [{"range": f"{int(iv.left)}-{int(iv.right) - 1}", "players": int(v)}
                             for iv, v in age_hist.items()],
        "top_market_value": _top(df, "market_value_eur"),
        "top_rating": _top(df[df["minutes"] >= TOP_RATING_MIN_MINUTES], "rating"),
        "top_rating_min_minutes": TOP_RATING_MIN_MINUTES,
        "leagues": leagues,
        "evolution": evolution,
        "evolution_note": "Partidos de las ligas con 4 o más temporadas en la fuente (mismo grupo de ligas cada año, "
                          "salvo ascensos y descensos).",
    }


def search(session: Session, q: str, limit: int = 8) -> dict:
    q = q.strip()
    if len(q) < 2:
        return {"players": [], "teams": []}
    players = [{"id": r[0], "name": r[1], "position": r[2], "team_name": r[3], "image_url": r[4]}
               for r in players_repo.search(session, q, limit)]
    teams = [{"id": r[0], "name": r[1], "league_name": r[2], "image_url": r[3]} for r in teams_repo.search(session, q, limit)]
    return {"players": players, "teams": teams}


def data_status(session: Session) -> dict:
    report = meta_repo.latest_import_report(session)
    return {
        "imported": report is not None,
        "imported_at": report.created_at if report else None,
        "source": report.report.get("source_label") if report else None,
        "source_url": report.report.get("source_url") if report else None,
        "source_license": report.report.get("source_license") if report else None,
        "date_range": report.report.get("date_range") if report else None,
        "report": report.report if report else None,
        "leagues": meta_repo.leagues_with_counts(session),
        "player_seasons": meta_repo.player_seasons(session),
        "season_labels": {str(k): v for k, v in meta_repo.season_labels(session).items()},
    }
