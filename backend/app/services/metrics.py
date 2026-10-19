"""Catálogo de métricas y cálculos derivados (por 90, porcentajes, rating).

Es la única definición de cada métrica: la usan el importador, la API y los
modelos, así no hay dos fórmulas distintas para lo mismo.
"""
from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

POSITIONS = ("Goalkeeper", "Defender", "Midfield", "Attack")
POSITION_ES = {"Goalkeeper": "arquero", "Defender": "defensor", "Midfield": "mediocampista", "Attack": "delantero"}
MIN_REFERENCE_MINUTES = 450  # minutos mínimos para formar parte del grupo de referencia
RELIABILITY_HALF_MINUTES = 600  # con estos minutos la confianza del rating es 0,5


@dataclass(frozen=True)
class Metric:
    key: str
    label: str
    description: str
    higher_is_better: bool
    scope: str  # individual | team_context | usage | profile
    unit: str  # count | p90 | ratio | per_match | years | eur


METRICS: dict[str, Metric] = {
    m.key: m
    for m in [
        Metric("matches", "Partidos", "Partidos de liga jugados.", True, "usage", "count"),
        Metric("minutes", "Minutos", "Minutos de liga disputados.", True, "usage", "count"),
        Metric("goals", "Goles", "Goles de liga.", True, "individual", "count"),
        Metric("assists", "Asistencias", "Asistencias de liga.", True, "individual", "count"),
        Metric("goals_p90", "Goles/90", "Goles cada 90 minutos.", True, "individual", "p90"),
        Metric("assists_p90", "Asist./90", "Asistencias cada 90 minutos.", True, "individual", "p90"),
        Metric("goal_contrib_p90", "G+A/90", "Goles más asistencias cada 90 minutos.", True, "individual", "p90"),
        Metric("cards_p90", "Tarjetas/90", "Amarillas y rojas cada 90 minutos (menos es mejor).", False, "individual", "p90"),
        Metric("minutes_share", "% minutos", "Minutos jugados sobre los minutos de liga de su club.", True, "usage", "ratio"),
        Metric("goal_involvement_share", "% goles del equipo",
               "Goles + asistencias sobre los goles del equipo en los partidos que jugó.", True, "individual", "ratio"),
        Metric("team_ppm", "Puntos/partido (equipo)",
               "Puntos del equipo por partido en los partidos que jugó. Contexto de equipo.", True, "team_context", "per_match"),
        Metric("team_ga_pm", "Goles recibidos/partido (equipo)",
               "Goles que recibió el equipo por partido en los partidos que jugó. Contexto de equipo; menos es mejor.",
               False, "team_context", "per_match"),
        Metric("clean_sheet_rate", "% vallas invictas",
               "Partidos sin goles en contra sobre los partidos en que jugó 60+ minutos. Contexto de equipo.",
               True, "team_context", "ratio"),
        Metric("age", "Edad", "Edad durante la temporada (menos es más proyección).", False, "profile", "years"),
        Metric("market_value_eur", "Valor de mercado", "Último valor registrado en Transfermarkt.", False, "profile", "eur"),
    ]
}

# Métricas de rendimiento por posición y su peso en el FIQ Rating.
RATING_WEIGHTS: dict[str, dict[str, float]] = {
    "Attack": {"goals_p90": 0.35, "assists_p90": 0.20, "goal_involvement_share": 0.20,
               "minutes_share": 0.15, "team_ppm": 0.10},
    "Midfield": {"assists_p90": 0.25, "goals_p90": 0.20, "goal_involvement_share": 0.15,
                 "minutes_share": 0.20, "team_ppm": 0.20},
    "Defender": {"clean_sheet_rate": 0.25, "team_ga_pm": 0.25, "minutes_share": 0.25,
                 "goal_contrib_p90": 0.15, "cards_p90": 0.10},
    "Goalkeeper": {"clean_sheet_rate": 0.35, "team_ga_pm": 0.35, "minutes_share": 0.30},
}

# Variables por defecto para similitud y comparación, según la posición.
POSITION_FEATURES: dict[str, list[str]] = {
    "Attack": ["goals_p90", "assists_p90", "goal_involvement_share", "minutes_share", "cards_p90", "age"],
    "Midfield": ["goals_p90", "assists_p90", "goal_involvement_share", "minutes_share", "team_ppm",
                 "cards_p90", "age"],
    "Defender": ["goal_contrib_p90", "clean_sheet_rate", "team_ga_pm", "minutes_share", "cards_p90", "age"],
    "Goalkeeper": ["clean_sheet_rate", "team_ga_pm", "minutes_share", "team_ppm", "age"],
}

PERFORMANCE_METRICS = [k for k, m in METRICS.items() if m.unit in ("p90", "ratio", "per_match")]


def metric_catalog() -> list[dict]:
    return [asdict(m) for m in METRICS.values()]


def per90(value: pd.Series | float, minutes: pd.Series | float):
    """Valor cada 90 minutos. Sin minutos no hay tasa: devuelve NaN (no 0)."""
    value = pd.Series(value, dtype=float) if not np.isscalar(value) else float(value)
    minutes_arr = np.asarray(minutes, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where(minutes_arr > 0, np.asarray(value, dtype=float) * 90.0 / minutes_arr, np.nan)
    return float(out) if np.ndim(out) == 0 else out


def safe_ratio(num, den):
    num = np.asarray(num, dtype=float)
    den = np.asarray(den, dtype=float)
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where(den > 0, num / den, np.nan)
    return float(out) if np.ndim(out) == 0 else out


def add_derived_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega las métricas derivadas a una tabla con los conteos de temporada."""
    out = df.copy()
    out["goals_p90"] = per90(out["goals"], out["minutes"])
    out["assists_p90"] = per90(out["assists"], out["minutes"])
    out["goal_contrib_p90"] = per90(out["goals"] + out["assists"], out["minutes"])
    out["cards_p90"] = per90(out["yellow_cards"] + out["red_cards"], out["minutes"])
    out["minutes_share"] = np.clip(safe_ratio(out["minutes"], out["team_matches"] * 90.0), 0, 1)
    out["goal_involvement_share"] = np.clip(
        safe_ratio(out["goals"] + out["assists"], out["team_goals_for"]), 0, 1
    )
    out["team_ppm"] = safe_ratio(out["team_points"], out["matches"])
    out["team_ga_pm"] = safe_ratio(out["team_goals_against"], out["matches"])
    out["clean_sheet_rate"] = safe_ratio(out["clean_sheets"], out["matches_60"])
    return out


def percentile_against(values: pd.Series, reference: pd.Series, higher_is_better: bool) -> pd.Series:
    """Percentil (0-100) de cada valor respecto de un grupo de referencia.

    Empates cuentan la mitad. NaN queda NaN: un faltante no se convierte en 0.
    """
    ref = np.sort(reference.dropna().to_numpy(dtype=float))
    vals = values.to_numpy(dtype=float)
    if not higher_is_better:
        ref = np.sort(-ref)
        vals = -vals
    if len(ref) == 0:
        return pd.Series(np.nan, index=values.index)
    below = np.searchsorted(ref, vals, side="left")
    equal_or_below = np.searchsorted(ref, vals, side="right")
    pct = (below + 0.5 * (equal_or_below - below)) / len(ref) * 100
    pct = np.where(np.isnan(vals), np.nan, pct)
    return pd.Series(pct, index=values.index)


def reliability(minutes) -> np.ndarray:
    m = np.asarray(minutes, dtype=float)
    return m / (m + RELIABILITY_HALF_MINUTES)


def compute_ratings(df: pd.DataFrame) -> pd.DataFrame:
    """FIQ Rating (0-100): percentil ponderado por posición, encogido hacia 50 con pocos minutos.

    Grupo de referencia: misma temporada, liga y posición, con 450+ minutos. Si en la liga
    hay menos de 8 jugadores de referencia, se usa la temporada y posición de todas las ligas.
    El rating es relativo a la liga: no corrige por la diferencia de nivel entre ligas.
    """
    out = df.copy()
    out["rating"] = np.nan
    out["rating_reliability"] = reliability(out["minutes"])
    for (season, position), group in out.groupby(["season", "position"], dropna=True):
        weights = RATING_WEIGHTS.get(position)
        if not weights:
            continue
        season_ref = group[group["minutes"] >= MIN_REFERENCE_MINUTES]
        for _, league_group in group.groupby("league_id", dropna=False):
            ref = league_group[league_group["minutes"] >= MIN_REFERENCE_MINUTES]
            if len(ref) < 8:
                ref = season_ref
            if ref.empty:
                continue
            score = pd.Series(0.0, index=league_group.index)
            total_w = pd.Series(0.0, index=league_group.index)
            for key, w in weights.items():
                pct = percentile_against(league_group[key], ref[key], METRICS[key].higher_is_better)
                score += pct.fillna(0) * w
                total_w += pct.notna() * w
            raw = score / total_w.replace(0, np.nan)
            rel = out.loc[league_group.index, "rating_reliability"]
            out.loc[league_group.index, "rating"] = 50 + (raw - 50) * rel
    out["rating"] = out["rating"].round(1)
    out["rating_reliability"] = out["rating_reliability"].round(3)
    return out
