"""Scouting, mercado, predicción de partidos, equipos y rendimiento de modelos."""
from fastapi import APIRouter, Query

from app.api.deps import SessionDep
from app.ml import match_model, registry
from app.repositories import meta as meta_repo
from app.repositories import models as models_repo
from app.repositories import players as players_repo
from app.repositories import teams as teams_repo
from app.schemas.requests import MatchPredictRequest, OpportunityRequest, ScoutingRequest, ValueEstimateRequest
from app.schemas.responses import (MatchPredictionOut, ModelRunOut, OpportunityOut, ScoutingOut, TeamListItem,
                                   ValueEstimateOut)
from app.services import opportunities, scouting, valuation
from app.services import teams as teams_service

router = APIRouter(prefix="/api")


@router.post("/scouting/search", response_model=ScoutingOut, tags=["scouting"])
def scouting_search(body: ScoutingRequest, session: SessionDep):
    season = meta_repo.resolve_season(session, body.season)
    frame = players_repo.season_frame(session, season)
    res = scouting.run_scouting(frame, scouting.ScoutingCriteria(
        position=body.position, metrics=body.metrics, max_age=body.max_age, max_budget_eur=body.max_budget_eur,
        league_ids=body.league_ids, min_minutes=body.min_minutes, nationality=body.nationality, limit=body.limit))
    return {**res, "season": season}


@router.post("/market/opportunities", response_model=OpportunityOut, tags=["market"])
def market_opportunities(body: OpportunityRequest, session: SessionDep):
    season = meta_repo.resolve_season(session, body.season)
    frame = players_repo.season_frame(session, season)
    res = opportunities.compute(frame, opportunities.OpportunityQuery(
        weights=body.weights, position=body.position, league_ids=body.league_ids, max_age=body.max_age,
        max_value_eur=body.max_value_eur, min_minutes=body.min_minutes, sort_by=body.sort_by,
        sort_dir=body.sort_dir, limit=body.limit), valuation.predicted_values(frame))
    return {**res, "season": season, "methodology": opportunities.__doc__}


@router.post("/market/value-estimate", response_model=ValueEstimateOut, tags=["market"])
def value_estimate(body: ValueEstimateRequest, session: SessionDep):
    return valuation.estimate(session, body.player_id, body.season,
                              body.profile.model_dump() if body.profile else None)


@router.post("/matches/predict", response_model=MatchPredictionOut, tags=["matches"])
def predict_match(body: MatchPredictRequest, session: SessionDep):
    artifact = registry.load(match_model.MODEL_KEY)
    res = match_model.predict(artifact, body.home_team_id, body.away_team_id, body.neutral)
    teams = {}
    for key, tid in (("home_team", body.home_team_id), ("away_team", body.away_team_id)):
        row = teams_repo.get_team(session, tid)
        teams[key] = {"id": tid, "name": row[0].name if row else None, "league_name": row[1] if row else None,
                      "image_url": row[0].image_url if row else None}
    run = models_repo.latest_run(session, match_model.MODEL_KEY)
    quality = None
    if run:
        p, b = run.metrics["poisson"], run.metrics["baseline"]
        quality = {"log_loss": p["log_loss"], "baseline_log_loss": b["log_loss"], "accuracy": p["accuracy"],
                   "baseline_accuracy": b["accuracy"], "test_matches": run.n_test}
    return {**res, **teams, "model_quality": quality}


@router.get("/teams", response_model=list[TeamListItem], tags=["teams"])
def list_teams(session: SessionDep, league_id: int | None = None,
               q: str | None = Query(None, max_length=60),
               active_only: bool = Query(True, description="Solo equipos con partidos en la última temporada")):
    return teams_service.list_teams(session, league_id, q, active_only)


@router.get("/teams/{team_id}", tags=["teams"])
def team_detail(team_id: int, session: SessionDep):
    return teams_service.detail(session, team_id)


@router.get("/models/performance", response_model=list[ModelRunOut], tags=["models"])
def models_performance(session: SessionDep):
    """Resultados guardados de la última evaluación de cada modelo."""
    return models_repo.latest_runs(session)
