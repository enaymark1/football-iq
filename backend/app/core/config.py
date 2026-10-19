"""Configuración central leída de variables de entorno (o de un archivo .env)."""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = PROJECT_ROOT / "backend"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BACKEND_ROOT / ".env"),
        env_prefix="FIQ_",
        extra="ignore",
    )

    app_name: str = "Football IQ"
    # Cualquier URL que entienda SQLAlchemy. Para PostgreSQL:
    # postgresql+psycopg://usuario:clave@host:5432/football_iq
    database_url: str = f"sqlite:///{(BACKEND_ROOT / 'football_iq.db').as_posix()}"
    models_dir: Path = BACKEND_ROOT / "artifacts"
    raw_data_dir: Path = PROJECT_ROOT / "datasets" / "raw"
    sample_data_dir: Path = PROJECT_ROOT / "datasets" / "sample"
    reports_dir: Path = PROJECT_ROOT / "datasets" / "reports"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    # Primera temporada de estadísticas de jugadores que se importa.
    first_player_season: int = 2019

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
