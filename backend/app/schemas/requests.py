"""Esquemas de entrada de la API (validación con Pydantic)."""
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.services.metrics import METRICS
from app.services.opportunities import COMPONENTS, DEFAULT_WEIGHTS

Position = Literal["Goalkeeper", "Defender", "Midfield", "Attack"]


class CompareRequest(BaseModel):
    player_ids: list[int] = Field(min_length=2, max_length=4, description="Entre 2 y 4 ids de jugador")
    season: int | None = Field(None, description="Temporada común; si no se indica, la última de cada jugador")


class ScoutingRequest(BaseModel):
    position: Position | None = None
    max_age: float | None = Field(None, ge=15, le=45)
    max_budget_eur: float | None = Field(None, ge=0)
    league_ids: list[int] = Field(default_factory=list)
    nationality: str | None = None
    min_minutes: int = Field(900, ge=0, le=5000)
    metrics: dict[str, float] = Field(
        min_length=1, description="Métrica -> peso relativo (0 a 10)",
        examples=[{"assists_p90": 3, "goals_p90": 2, "minutes_share": 1}])
    season: int | None = None
    limit: int = Field(25, ge=1, le=100)

    @field_validator("metrics")
    @classmethod
    def _check_metrics(cls, v: dict[str, float]) -> dict[str, float]:
        unknown = [k for k in v if k not in METRICS]
        if unknown:
            raise ValueError(f"métricas desconocidas: {unknown}; válidas: {list(METRICS)}")
        if any(not 0 <= w <= 10 for w in v.values()):
            raise ValueError("cada peso tiene que estar entre 0 y 10")
        if sum(v.values()) <= 0:
            raise ValueError("al menos un peso tiene que ser mayor que 0")
        return v


class OpportunityRequest(BaseModel):
    weights: dict[str, float] = Field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    position: Position | None = None
    league_ids: list[int] = Field(default_factory=list)
    max_age: float | None = Field(None, ge=15, le=45)
    max_value_eur: float | None = Field(None, ge=0)
    min_minutes: int = Field(900, ge=0, le=5000)
    sort_by: Literal["score", "age", "market_value_eur", "rating", "minutes"] = "score"
    sort_dir: Literal["asc", "desc"] = "desc"
    season: int | None = None
    limit: int = Field(50, ge=1, le=200)

    @field_validator("weights")
    @classmethod
    def _check_weights(cls, v: dict[str, float]) -> dict[str, float]:
        unknown = [k for k in v if k not in COMPONENTS]
        if unknown:
            raise ValueError(f"componentes desconocidos: {unknown}; válidos: {list(COMPONENTS)}")
        if any(w < 0 for w in v.values()) or sum(v.values()) <= 0:
            raise ValueError("los pesos tienen que ser >= 0 y sumar más que 0")
        return v


class MatchPredictRequest(BaseModel):
    home_team_id: int
    away_team_id: int
    neutral: bool = Field(False, description="Cancha neutral: promedia las dos localías")

    @model_validator(mode="after")
    def _different(self):
        if self.home_team_id == self.away_team_id:
            raise ValueError("los equipos tienen que ser distintos")
        return self


class ValueProfile(BaseModel):
    age: float = Field(ge=15, le=45)
    position: Position
    sub_position: str | None = None
    league_name: str | None = None
    foot: Literal["right", "left", "both"] | None = None
    height_cm: float | None = Field(None, ge=150, le=210)
    matches: int = Field(ge=0, le=60)
    minutes: int = Field(ge=0, le=6000)
    goals: int = Field(0, ge=0, le=80)
    assists: int = Field(0, ge=0, le=60)
    yellow_cards: int = Field(0, ge=0, le=30)
    red_cards: int = Field(0, ge=0, le=10)
    team_matches: int | None = Field(None, ge=1, le=60, description="Partidos de liga del club en la temporada")
    team_goals_for: int | None = Field(None, ge=0)
    team_goals_against: int | None = Field(None, ge=0)
    team_points: int | None = Field(None, ge=0)
    clean_sheets: int | None = Field(None, ge=0)
    matches_60: int | None = Field(None, ge=0)

    @model_validator(mode="after")
    def _consistent(self):
        if self.minutes > self.matches * 130:
            raise ValueError("los minutos no son compatibles con la cantidad de partidos")
        if self.team_matches is not None and self.matches > self.team_matches:
            raise ValueError("jugó más partidos que su club")
        return self


class ValueEstimateRequest(BaseModel):
    player_id: int | None = None
    season: int | None = None
    profile: ValueProfile | None = None

    @model_validator(mode="after")
    def _one_subject(self):
        if (self.player_id is None) == (self.profile is None):
            raise ValueError("indicá player_id o profile (uno de los dos)")
        return self
