"""Acceso a datos de jugadores. Las consultas son SQLAlchemy puro (portables a PostgreSQL)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

import pandas as pd
from sqlalchemy import Select, and_, asc, desc, func, select
from sqlalchemy.orm import Session, aliased

from app.models import League, Player, PlayerSeasonStats, Team, Valuation
from app.repositories.meta import cached

SORTABLE = {
    "name": Player.name, "age": PlayerSeasonStats.age, "minutes": PlayerSeasonStats.minutes,
    "matches": PlayerSeasonStats.matches, "goals": PlayerSeasonStats.goals,
    "assists": PlayerSeasonStats.assists, "goals_p90": PlayerSeasonStats.goals_p90,
    "assists_p90": PlayerSeasonStats.assists_p90, "goal_contrib_p90": PlayerSeasonStats.goal_contrib_p90,
    "market_value_eur": Player.market_value_eur, "rating": PlayerSeasonStats.rating,
}


@dataclass
class PlayerFilters:
    season: int
    q: str | None = None
    position: str | None = None
    league_id: int | None = None
    team_id: int | None = None
    nationality: str | None = None
    age_min: float | None = None
    age_max: float | None = None
    value_min: float | None = None
    value_max: float | None = None
    minutes_min: int | None = None
    goals_min: int | None = None
    assists_min: int | None = None
    rating_min: float | None = None


def _base_query() -> Select:
    return (
        select(PlayerSeasonStats, Player, Team.name.label("team_name"), League.name.label("league_name"),
               Team.image_url.label("team_image_url"))
        .join(Player, Player.id == PlayerSeasonStats.player_id)
        .outerjoin(Team, Team.id == PlayerSeasonStats.team_id)
        .outerjoin(League, League.id == PlayerSeasonStats.league_id)
    )


def _apply_filters(stmt: Select, f: PlayerFilters) -> Select:
    conds = [PlayerSeasonStats.season == f.season]
    if f.q:
        conds.append(Player.name.ilike(f"%{f.q.strip()}%"))
    if f.position:
        conds.append(Player.position == f.position)
    if f.league_id is not None:
        conds.append(PlayerSeasonStats.league_id == f.league_id)
    if f.team_id is not None:
        conds.append(PlayerSeasonStats.team_id == f.team_id)
    if f.nationality:
        conds.append(Player.nationality == f.nationality)
    if f.age_min is not None:
        conds.append(PlayerSeasonStats.age >= f.age_min)
    if f.age_max is not None:
        conds.append(PlayerSeasonStats.age <= f.age_max)
    if f.value_min is not None:
        conds.append(Player.market_value_eur >= f.value_min)
    if f.value_max is not None:
        conds.append(Player.market_value_eur <= f.value_max)
    if f.minutes_min is not None:
        conds.append(PlayerSeasonStats.minutes >= f.minutes_min)
    if f.goals_min is not None:
        conds.append(PlayerSeasonStats.goals >= f.goals_min)
    if f.assists_min is not None:
        conds.append(PlayerSeasonStats.assists >= f.assists_min)
    if f.rating_min is not None:
        conds.append(PlayerSeasonStats.rating >= f.rating_min)
    return stmt.where(and_(*conds))


def list_player_seasons(session: Session, f: PlayerFilters, sort_by: str, sort_dir: str,
                        page: int, page_size: int) -> tuple[list, int]:
    stmt = _apply_filters(_base_query(), f)
    total = session.scalar(select(func.count()).select_from(stmt.subquery()))
    col = SORTABLE[sort_by]
    order = desc(col) if sort_dir == "desc" else asc(col)
    # los nulos van siempre al final, sin importar el sentido
    stmt = stmt.order_by(col.is_(None), order, Player.id).offset((page - 1) * page_size).limit(page_size)
    return session.execute(stmt).all(), int(total or 0)


def nationalities(session: Session, season: int) -> list[str]:
    stmt = (select(Player.nationality).join(PlayerSeasonStats, PlayerSeasonStats.player_id == Player.id)
            .where(PlayerSeasonStats.season == season, Player.nationality.is_not(None))
            .distinct().order_by(Player.nationality))
    return list(session.scalars(stmt))


def get_player(session: Session, player_id: int) -> tuple[Player, str | None, str | None] | None:
    cur_team = aliased(Team)
    row = session.execute(
        select(Player, cur_team.name, League.name, cur_team.image_url)
        .outerjoin(cur_team, cur_team.id == Player.current_team_id)
        .outerjoin(League, League.id == cur_team.league_id)
        .where(Player.id == player_id)
    ).first()
    return tuple(row) if row else None


def player_seasons(session: Session, player_id: int) -> list:
    stmt = _base_query().where(PlayerSeasonStats.player_id == player_id).order_by(PlayerSeasonStats.season)
    return session.execute(stmt).all()


def valuations(session: Session, player_id: int) -> list[tuple[date, float]]:
    rows = session.execute(select(Valuation.date, Valuation.value_eur)
                           .where(Valuation.player_id == player_id).order_by(Valuation.date))
    return [(r[0], r[1]) for r in rows]


def search(session: Session, q: str, limit: int) -> list:
    stmt = (select(Player.id, Player.name, Player.position, Team.name, Player.image_url)
            .outerjoin(Team, Team.id == Player.current_team_id)
            .where(Player.name.ilike(f"%{q}%"))
            .order_by(Player.market_value_eur.is_(None), desc(Player.market_value_eur)).limit(limit))
    return session.execute(stmt).all()


# --- Tabla de una temporada en memoria, para los cálculos analíticos -------------------


def season_frame(session: Session, season: int) -> pd.DataFrame:
    """Estadísticas de una temporada + datos del jugador, como DataFrame (cacheado por versión de datos)."""
    return cached(session, "season_frame", lambda: _load_season_frame(session, season), season)


def _load_season_frame(session: Session, season: int) -> pd.DataFrame:
    stmt = (
        select(PlayerSeasonStats, Player.name, Player.position, Player.sub_position, Player.nationality,
               Player.market_value_eur, Player.market_value_date, Player.date_of_birth, Player.height_cm,
               Player.foot, Player.image_url, Team.name.label("team_name"), League.name.label("league_name"),
               Team.image_url.label("team_image_url"))
        .join(Player, Player.id == PlayerSeasonStats.player_id)
        .outerjoin(Team, Team.id == PlayerSeasonStats.team_id)
        .outerjoin(League, League.id == PlayerSeasonStats.league_id)
        .where(PlayerSeasonStats.season == season)
    )
    rows = session.execute(stmt).all()
    stat_cols = [c.key for c in PlayerSeasonStats.__table__.columns]
    records = []
    for r in rows:
        s = r[0]
        rec = {c: getattr(s, c) for c in stat_cols}
        rec.update(name=r.name, position=r.position, sub_position=r.sub_position, nationality=r.nationality,
                   market_value_eur=r.market_value_eur, market_value_date=r.market_value_date,
                   date_of_birth=r.date_of_birth, height_cm=r.height_cm, foot=r.foot,
                   team_name=r.team_name, league_name=r.league_name, image_url=r.image_url,
                   team_image_url=r.team_image_url)
        records.append(rec)
    df = pd.DataFrame.from_records(records, columns=stat_cols + [
        "name", "position", "sub_position", "nationality", "market_value_eur", "market_value_date",
        "date_of_birth", "height_cm", "foot", "team_name", "league_name", "image_url", "team_image_url"])
    if not df.empty:
        df = df.set_index("player_id", drop=False)
    return df


def players_frame(session: Session, player_ids: list[int], season: int | None = None) -> pd.DataFrame:
    """Última temporada de cada jugador pedido (o la temporada indicada)."""
    stmt = select(PlayerSeasonStats.player_id, func.max(PlayerSeasonStats.season)).where(
        PlayerSeasonStats.player_id.in_(player_ids))
    if season is not None:
        stmt = stmt.where(PlayerSeasonStats.season == season)
    pairs = session.execute(stmt.group_by(PlayerSeasonStats.player_id)).all()
    frames = []
    for pid, s in pairs:
        frame = season_frame(session, s)
        frames.append(frame.loc[[pid]])
    return pd.concat(frames) if frames else pd.DataFrame()

