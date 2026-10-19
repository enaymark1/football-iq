"""Jugadores: explorador, perfil, similares y comparador."""
from typing import Literal

from fastapi import APIRouter, Query

from app.api.deps import SessionDep
from app.core.errors import NotFoundError
from app.repositories import meta as meta_repo
from app.repositories import players as players_repo
from app.schemas.requests import CompareRequest
from app.schemas.responses import CompareOut, PlayerListOut, PlayerProfileOut, SimilarOut
from app.services import players as players_service
from app.services import similarity
from app.services.metrics import POSITIONS

router = APIRouter(prefix="/api/players", tags=["players"])
PositionQ = Literal["Goalkeeper", "Defender", "Midfield", "Attack"]


@router.get("", response_model=PlayerListOut)
def list_players(
    session: SessionDep,
    season: int | None = Query(None, description="Temporada (por defecto la última)"),
    q: str | None = Query(None, max_length=60, description="Buscar por nombre"),
    position: PositionQ | None = None,
    league_id: int | None = None,
    team_id: int | None = None,
    nationality: str | None = Query(None, max_length=80),
    age_min: float | None = Query(None, ge=14, le=50),
    age_max: float | None = Query(None, ge=14, le=50),
    value_min: float | None = Query(None, ge=0),
    value_max: float | None = Query(None, ge=0),
    minutes_min: int | None = Query(None, ge=0),
    goals_min: int | None = Query(None, ge=0),
    assists_min: int | None = Query(None, ge=0),
    rating_min: float | None = Query(None, ge=0, le=100),
    sort_by: str = Query("rating", description=f"Uno de {sorted(players_repo.SORTABLE)}"),
    sort_dir: Literal["asc", "desc"] = "desc",
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    filters = players_repo.PlayerFilters(
        season=meta_repo.resolve_season(session, season), q=q, position=position, league_id=league_id,
        team_id=team_id, nationality=nationality, age_min=age_min, age_max=age_max, value_min=value_min,
        value_max=value_max, minutes_min=minutes_min, goals_min=goals_min, assists_min=assists_min,
        rating_min=rating_min)
    return players_service.list_players(session, filters, sort_by, sort_dir, page, page_size)


@router.get("/filters")
def filter_options(session: SessionDep, season: int | None = None):
    """Valores posibles para los filtros del explorador."""
    season = meta_repo.resolve_season(session, season)
    return {"season": season, "positions": list(POSITIONS),
            "nationalities": players_repo.nationalities(session, season),
            "sortable": sorted(players_repo.SORTABLE)}


@router.post("/compare", response_model=CompareOut)
def compare(body: CompareRequest, session: SessionDep):
    return players_service.compare(session, body.player_ids, body.season)


@router.get("/{player_id}", response_model=PlayerProfileOut)
def profile(player_id: int, session: SessionDep, season: int | None = None):
    return players_service.profile(session, player_id, season)


@router.get("/{player_id}/similar", response_model=SimilarOut)
def similar(
    player_id: int, session: SessionDep,
    season: int | None = Query(None, description="Temporada del perfil (por defecto la última del jugador)"),
    features: list[str] | None = Query(None, description="Variables a usar (por defecto, según la posición)"),
    k: int = Query(10, ge=1, le=30),
    min_minutes: int = Query(similarity.DEFAULT_MIN_MINUTES, ge=0, le=4000),
):
    df = players_repo.players_frame(session, [player_id], season)
    if df.empty:
        raise NotFoundError("El jugador no existe o no tiene estadísticas en esa temporada.")
    frame = players_repo.season_frame(session, int(df.iloc[0]["season"]))
    return similarity.find_similar(frame, player_id, features=features, k=k, min_minutes=min_minutes)
