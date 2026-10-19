"""Consultas generales: temporadas, ligas, versión de los datos e informes."""
from collections.abc import Callable
from threading import Lock

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import DataUnavailableError
from app.models import ImportReport, League, PlayerSeasonStats, Season


def data_version(session: Session) -> int:
    """Id del último informe de importación. Cambia con cada importación (sirve para invalidar cachés)."""
    return session.scalar(select(func.max(ImportReport.id))) or 0


_CACHE: dict[tuple, object] = {}
_CACHE_LOCK = Lock()


def cached(session: Session, name: str, loader: Callable[[], object], *parts) -> object:
    """Cachea en memoria un resultado de lectura hasta que cambie la versión de los datos."""
    key = (str(session.get_bind().url), data_version(session), name, *parts)
    with _CACHE_LOCK:
        if key in _CACHE:
            return _CACHE[key]
    value = loader()
    with _CACHE_LOCK:
        if len(_CACHE) > 32:
            _CACHE.clear()
        _CACHE[key] = value
    return value


def latest_import_report(session: Session) -> ImportReport | None:
    return session.scalar(select(ImportReport).order_by(ImportReport.id.desc()).limit(1))


def player_seasons(session: Session) -> list[int]:
    return list(session.scalars(select(PlayerSeasonStats.season).distinct().order_by(PlayerSeasonStats.season)))


def latest_player_season(session: Session) -> int:
    season = session.scalar(select(func.max(PlayerSeasonStats.season)))
    if season is None:
        raise DataUnavailableError("No hay estadísticas de jugadores importadas. Corré scripts/import_data.py.")
    return season


def resolve_season(session: Session, season: int | None) -> int:
    if season is None:
        return latest_player_season(session)
    if season not in player_seasons(session):
        raise DataUnavailableError(f"No hay estadísticas de jugadores para la temporada {season}.")
    return season


def season_labels(session: Session) -> dict[int, str]:
    return {s.year: s.label for s in session.scalars(select(Season))}


def leagues_with_counts(session: Session) -> list[dict]:
    player_counts = dict(session.execute(
        select(PlayerSeasonStats.league_id, func.count(func.distinct(PlayerSeasonStats.player_id)))
        .group_by(PlayerSeasonStats.league_id)).all())
    from app.models import Match
    match_rows = session.execute(
        select(Match.league_id, func.count(), func.min(Match.season), func.max(Match.season))
        .group_by(Match.league_id)).all()
    match_info = {r[0]: r[1:] for r in match_rows}
    out = []
    for lg in session.scalars(select(League).order_by(League.name)):
        n_matches, first, last = match_info.get(lg.id, (0, None, None))
        out.append({
            "id": lg.id, "name": lg.name, "country": lg.country, "confederation": lg.confederation,
            "players": int(player_counts.get(lg.id, 0)), "matches": int(n_matches),
            "first_season": first, "last_season": last,
            "has_player_stats": bool(player_counts.get(lg.id, 0)), "image_url": lg.image_url,
        })
    return out
