"""Salud, metadatos, búsqueda global y dashboard."""
from fastapi import APIRouter, Query
from sqlalchemy import text

from app.api.deps import SessionDep
from app.core.config import get_settings
from app.ml import match_model, registry, value_model
from app.repositories import meta as meta_repo
from app.schemas.responses import HealthOut, LeagueOut
from app.services import overview as overview_service
from app.services.metrics import METRICS, POSITION_FEATURES, POSITIONS, RATING_WEIGHTS, metric_catalog
from app.services.opportunities import COMPONENTS, DEFAULT_WEIGHTS
from app.services.opportunities import __doc__ as OPPORTUNITY_DOC

router = APIRouter(prefix="/api", tags=["general"])


@router.get("/health", response_model=HealthOut)
def health(session: SessionDep):
    try:
        session.execute(text("SELECT 1"))
        db = "ok"
    except Exception as exc:  # el health check informa el error en lugar de romper
        db = f"error: {exc}"
    trained = [k for k in (match_model.MODEL_KEY, value_model.MODEL_KEY) if registry.try_load(k) is not None]
    imported = db == "ok" and meta_repo.latest_import_report(session) is not None
    return HealthOut(status="ok" if db == "ok" else "degraded", app=get_settings().app_name, database=db,
                     data_imported=imported, models_trained=trained)


@router.get("/leagues", response_model=list[LeagueOut])
def leagues(session: SessionDep):
    return meta_repo.leagues_with_counts(session)


@router.get("/meta")
def meta(session: SessionDep):
    """Catálogo de métricas, posiciones, temporadas y definiciones de índices propios."""
    return {
        "app_name": get_settings().app_name,
        "metrics": metric_catalog(),
        "positions": list(POSITIONS),
        "position_features": POSITION_FEATURES,
        "rating_weights": RATING_WEIGHTS,
        "rating_definition": "FIQ Rating (0-100): promedio ponderado de percentiles por posición dentro de su liga y "
                             "temporada (referencia: 450+ minutos), encogido hacia 50 según minutos: "
                             "confianza = minutos / (minutos + 600).",
        "opportunity_components": COMPONENTS,
        "opportunity_default_weights": DEFAULT_WEIGHTS,
        "opportunity_definition": OPPORTUNITY_DOC,
        "scouting_metrics": [k for k, m in METRICS.items() if k not in ("matches",)],
        "data": overview_service.data_status(session),
    }


@router.get("/search")
def search(session: SessionDep, q: str = Query(..., min_length=1, max_length=60),
           limit: int = Query(8, ge=1, le=25)):
    return overview_service.search(session, q, limit)


@router.get("/overview")
def overview(session: SessionDep, season: int | None = None):
    return overview_service.overview(session, season)
