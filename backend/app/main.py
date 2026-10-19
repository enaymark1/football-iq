"""Punto de entrada de la API: `uvicorn app.main:app --reload` desde la carpeta backend."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analysis, meta, players
from app.core.config import get_settings
from app.core.database import init_db
from app.core.errors import register_error_handlers


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()  # crea las tablas si la base está vacía (no borra nada)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        lifespan=lifespan,
        title=f"{settings.app_name} API",
        version="1.0.0",
        description="Análisis de fútbol, scouting y modelos predictivos sobre datos reales "
                    "(transfermarkt-datasets, CC0).",
    )
    app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=False,
                       allow_methods=["GET", "POST"], allow_headers=["*"])
    register_error_handlers(app)
    app.include_router(meta.router)
    app.include_router(players.router)
    app.include_router(analysis.router)

    return app


app = create_app()
