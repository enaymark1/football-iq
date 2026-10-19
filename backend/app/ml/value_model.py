"""Estimador de valor de mercado a partir del perfil y el rendimiento de la temporada.

Objetivo: valor registrado en Transfermarkt al terminar la temporada.
A propósito NO usa historial de valores (valor anterior, valor máximo): la idea es
estimar qué valor "sugieren" la edad, la posición, la liga y las estadísticas.
Como referencia se informa cuánto acierta repetir el valor del inicio de temporada.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from app.ml.evaluation import regression_metrics

MODEL_KEY = "market_value"
NUMERIC = ["age", "minutes", "matches", "minutes_share", "goals", "assists", "goals_p90", "assists_p90",
           "goal_involvement_share", "team_ppm", "team_ga_pm", "clean_sheet_rate", "cards_p90", "height_cm"]
CATEGORICAL = ["position", "sub_position", "league_name", "foot"]
FEATURES = NUMERIC + CATEGORICAL
MIN_MINUTES = 90


def training_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Filas utilizables: con valor objetivo, posición y edad."""
    out = df[df["market_value_end_eur"].notna() & df["position"].notna() & df["age"].notna()
             & (df["minutes"] >= MIN_MINUTES)].copy()
    return out


def _pipeline() -> Pipeline:
    pre = ColumnTransformer([
        ("num", "passthrough", NUMERIC),
        ("cat", OneHotEncoder(handle_unknown="ignore", min_frequency=20, sparse_output=False), CATEGORICAL),
    ])
    model = HistGradientBoostingRegressor(max_iter=600, learning_rate=0.05, max_leaf_nodes=31,
                                          min_samples_leaf=30, l2_regularization=1.0, random_state=42)
    return Pipeline([("pre", pre), ("model", model)])


def _prep(df: pd.DataFrame) -> pd.DataFrame:
    X = df[FEATURES].copy()
    for c in CATEGORICAL:
        X[c] = X[c].astype(object).where(X[c].notna(), "desconocido").astype(str)
    for c in NUMERIC:
        X[c] = pd.to_numeric(X[c], errors="coerce")
    return X


def train_and_evaluate(df: pd.DataFrame) -> tuple[dict, dict]:
    data = training_frame(df)
    seasons = sorted(data["season"].unique())
    if len(seasons) < 2 or len(data) < 500:
        raise ValueError("No hay suficientes jugadores con valor de mercado para entrenar y evaluar.")
    test_season = seasons[-1]
    train, test = data[data["season"] < test_season], data[data["season"] == test_season]

    pipe = _pipeline().fit(_prep(train), np.log1p(train["market_value_end_eur"]))
    pred = np.expm1(pipe.predict(_prep(test)))
    y = test["market_value_end_eur"].to_numpy()

    # Baseline 1: mediana de entrenamiento por liga + posición (+ tramo de edad).
    def bucket(d):
        return d["league_name"].astype(str) + "|" + d["position"].astype(str) + "|" + \
            pd.cut(d["age"], [0, 21, 24, 27, 30, 50]).astype(str)
    med = train.groupby(bucket(train))["market_value_end_eur"].median()
    base = bucket(test).map(med).fillna(train["market_value_end_eur"].median()).to_numpy()

    metrics = {"model": regression_metrics(y, pred), "baseline_group_median": regression_metrics(y, base)}
    has_start = test["market_value_start_eur"].notna().to_numpy()
    metrics["reference_previous_value"] = {
        **regression_metrics(y[has_start], test["market_value_start_eur"].to_numpy()[has_start]),
        "note": "Repite el valor registrado al inicio de la temporada. Usa historial de valores, "
                "que el modelo excluye a propósito: es una referencia, no un competidor directo.",
    }
    # rango típico de error (en el set de evaluación) para mostrar junto a cada estimación
    ratio = np.log(pred) - np.log(y)
    band = {"p10_ratio": round(float(np.exp(np.percentile(ratio, 10))), 3),
            "p90_ratio": round(float(np.exp(np.percentile(ratio, 90))), 3)}
    metrics["error_band"] = band
    by_pos = {}
    for pos, g in test.assign(pred=pred).groupby("position"):
        by_pos[pos] = regression_metrics(g["market_value_end_eur"], g["pred"])
    metrics["by_position"] = by_pos
    metrics["split"] = {"train_seasons": [int(seasons[0]), int(test_season - 1)], "test_season": int(test_season)}

    league_counts = train["league_name"].value_counts().to_dict()
    artifact = {"pipeline": pipe, "features": FEATURES, "train_max_season": int(test_season - 1),
                "error_band": band, "league_counts": league_counts,
                "value_range": [float(train["market_value_end_eur"].min()), float(train["market_value_end_eur"].max())]}
    return artifact, {"n_train": int(len(train)), "n_test": int(len(test)), "metrics": metrics}


def predict_frame(artifact: dict, df: pd.DataFrame) -> np.ndarray:
    """Valor estimado (EUR) para cada fila. Filas sin posición o edad -> NaN."""
    ok = df["position"].notna() & df["age"].notna()
    out = np.full(len(df), np.nan)
    if ok.any():
        out[ok.to_numpy()] = np.expm1(artifact["pipeline"].predict(_prep(df[ok])))
    return out


def confidence_notes(artifact: dict, row: pd.Series) -> list[str]:
    notes = []
    if row.get("minutes", 0) < 900:
        notes.append("Menos de 900 minutos: las estadísticas de la temporada son una muestra chica.")
    if artifact["league_counts"].get(row.get("league_name"), 0) < 300:
        notes.append("Liga con pocas observaciones de entrenamiento.")
    if row.get("season", 0) <= artifact["train_max_season"]:
        notes.append("Esta temporada se usó para entrenar el modelo: la estimación no es una predicción "
                     "fuera de muestra y tiende a parecerse al valor real.")
    return notes
