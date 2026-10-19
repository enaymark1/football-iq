"""Esquemas de salida principales (documentan la API en /docs)."""
from datetime import date, datetime
from typing import Any

from pydantic import BaseModel


class HealthOut(BaseModel):
    status: str
    app: str
    database: str
    data_imported: bool
    models_trained: list[str]


class PlayerListItem(BaseModel):
    player_id: int
    name: str
    age: float | None
    nationality: str | None
    position: str | None
    sub_position: str | None
    team_id: int | None
    team_name: str | None
    league_id: int | None
    league_name: str | None
    season: int
    matches: int
    minutes: int
    goals: int
    assists: int
    goals_p90: float | None
    assists_p90: float | None
    market_value_eur: float | None
    rating: float | None
    rating_reliability: float | None
    image_url: str | None = None
    team_image_url: str | None = None


class PlayerListOut(BaseModel):
    items: list[PlayerListItem]
    total: int
    page: int
    page_size: int
    pages: int
    season: int


class PlayerProfileOut(BaseModel):
    player: dict[str, Any]
    seasons: list[dict[str, Any]]
    selected_season: int | None
    valuations: list[dict[str, Any]]
    position_comparison: dict[str, Any] | None
    strengths: list[dict[str, Any]]
    weaknesses: list[dict[str, Any]]
    similar: dict[str, Any] | None
    value_estimate: dict[str, Any] | None = None
    data_quality: dict[str, Any]
    unavailable_metrics: list[str]
    unavailable_reason: str


class SimilarOut(BaseModel):
    position: str
    features: list[str]
    pool_size: int
    min_minutes: int | None = None
    target_values: dict[str, float | None] | None = None
    results: list[dict[str, Any]]
    warnings: list[str]
    index_note: str = ("Índice de similitud coseno (-1 a 1) entre perfiles estandarizados de la misma posición. "
                       "Es una medida algorítmica, no una probabilidad.")


class CompareOut(BaseModel):
    players: list[dict[str, Any]]
    metrics: list[dict[str, Any]]
    radar: dict[str, Any]
    unavailable_metrics: list[str]
    unavailable_reason: str
    notes: list[str]
    same_position: bool


class ScoutingOut(BaseModel):
    candidates: list[dict[str, Any]]
    funnel: list[dict[str, Any]]
    weights: dict[str, float]
    excluded_without_value: int
    reference: str | None
    season: int


class OpportunityOut(BaseModel):
    results: list[dict[str, Any]]
    total: int
    weights: dict[str, float]
    components: dict[str, str]
    excluded_without_value: int
    notes: list[str]
    disclaimer: str
    season: int
    methodology: str


class MatchPredictionOut(BaseModel):
    home_team: dict[str, Any]
    away_team: dict[str, Any]
    probabilities: dict[str, dict[str, float]]
    expected_goals: dict[str, float]
    scorelines: list[dict[str, Any]]
    team_context: dict[str, Any]
    neutral: bool
    data_as_of: date
    warnings: list[str]
    model_quality: dict[str, Any] | None
    disclaimer: str = "Probabilidades estimadas por un modelo estadístico: no son certezas."


class ValueEstimateOut(BaseModel):
    subject: dict[str, Any]
    estimated_value_eur: float
    typical_range_eur: list[float]
    registered_value_eur: float | None
    difference_pct: float | None
    reliable: bool
    notes: list[str]
    model_metrics: dict[str, Any]
    explanation: str


class ModelRunOut(BaseModel):
    model_key: str
    name: str
    objective: str
    trained_at: datetime
    n_train: int
    n_test: int
    features: Any
    metrics: dict[str, Any]
    validation: str
    limitations: list[str]


class TeamListItem(BaseModel):
    id: int
    name: str
    league_id: int | None
    league_name: str | None
    country: str | None
    last_season: int | None
    elo: float | None
    image_url: str | None = None
    league_image_url: str | None = None


class LeagueOut(BaseModel):
    id: int
    name: str
    country: str | None
    confederation: str | None
    players: int
    matches: int
    first_season: int | None
    last_season: int | None
    has_player_stats: bool
    image_url: str | None = None
