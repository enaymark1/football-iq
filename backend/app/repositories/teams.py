"""Acceso a datos de equipos y partidos."""
from __future__ import annotations

import pandas as pd
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, aliased

from app.models import League, Match, Team
from app.repositories.meta import cached


def matches_frame(session: Session, league_id: int | None = None) -> pd.DataFrame:
    """Todos los partidos (o los de una liga) ordenados por fecha. Cacheado por versión de datos."""
    return cached(session, "matches_frame", lambda: _load_matches(session, league_id), league_id)


def _load_matches(session: Session, league_id: int | None) -> pd.DataFrame:
    stmt = select(Match.id, Match.league_id, Match.season, Match.date, Match.home_team_id, Match.away_team_id,
                  Match.home_goals, Match.away_goals)
    if league_id is not None:
        stmt = stmt.where(Match.league_id == league_id)
    rows = session.execute(stmt.order_by(Match.date, Match.id)).all()
    df = pd.DataFrame(rows, columns=["id", "league_id", "season", "date", "home_team_id", "away_team_id",
                                     "home_goals", "away_goals"])
    df["date"] = pd.to_datetime(df["date"])
    return df


def list_teams(session: Session, league_id: int | None, q: str | None, active_since: int | None) -> list:
    last_season = (select(func.max(Match.season)).where(
        or_(Match.home_team_id == Team.id, Match.away_team_id == Team.id)).scalar_subquery())
    stmt = (select(Team.id, Team.name, Team.league_id, League.name, League.country, last_season.label("last_season"),
                   Team.image_url, League.image_url.label("league_image_url"))
            .outerjoin(League, League.id == Team.league_id))
    if league_id is not None:
        stmt = stmt.where(Team.league_id == league_id)
    if q:
        stmt = stmt.where(Team.name.ilike(f"%{q.strip()}%"))
    rows = session.execute(stmt.order_by(Team.name)).all()
    if active_since is not None:
        rows = [r for r in rows if r.last_season is not None and r.last_season >= active_since]
    return rows


def get_team(session: Session, team_id: int):
    return session.execute(select(Team, League.name, League.country, League.image_url).outerjoin(League, League.id == Team.league_id)
                           .where(Team.id == team_id)).first()


def team_matches(session: Session, team_id: int) -> pd.DataFrame:
    home, away = aliased(Team), aliased(Team)
    stmt = (select(Match.id, Match.date, Match.season, Match.league_id, League.name, Match.home_team_id,
                   home.name, Match.away_team_id, away.name, Match.home_goals, Match.away_goals)
            .join(home, home.id == Match.home_team_id).join(away, away.id == Match.away_team_id)
            .join(League, League.id == Match.league_id)
            .where(or_(Match.home_team_id == team_id, Match.away_team_id == team_id))
            .order_by(Match.date))
    df = pd.DataFrame(session.execute(stmt).all(), columns=[
        "id", "date", "season", "league_id", "league_name", "home_team_id", "home_name", "away_team_id",
        "away_name", "home_goals", "away_goals"])
    return df


def search(session: Session, q: str, limit: int) -> list:
    stmt = (select(Team.id, Team.name, League.name, Team.image_url).outerjoin(League, League.id == Team.league_id)
            .where(Team.name.ilike(f"%{q}%")).order_by(Team.name).limit(limit))
    return session.execute(stmt).all()
