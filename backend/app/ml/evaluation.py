"""Métricas de evaluación compartidas por los modelos."""
from __future__ import annotations

import numpy as np

OUTCOMES = ["home", "draw", "away"]


def multiclass_metrics(y: np.ndarray, probs: np.ndarray) -> dict:
    """Métricas para probabilidades de 1X2. `y` en {0: local, 1: empate, 2: visitante}."""
    y = np.asarray(y, dtype=int)
    p = np.clip(np.asarray(probs, dtype=float), 1e-12, 1.0)
    p = p / p.sum(axis=1, keepdims=True)
    onehot = np.eye(3)[y]
    log_loss = float(-np.mean(np.log(p[np.arange(len(y)), y])))
    brier = float(np.mean(np.sum((p - onehot) ** 2, axis=1)))
    # RPS: tiene en cuenta el orden local > empate > visitante (estándar en fútbol)
    rps = float(np.mean(np.sum((np.cumsum(p, axis=1) - np.cumsum(onehot, axis=1))[:, :2] ** 2, axis=1) / 2))
    pred = p.argmax(axis=1)
    accuracy = float(np.mean(pred == y))
    confusion = np.zeros((3, 3), dtype=int)
    for t, q in zip(y, pred):
        confusion[t, q] += 1
    return {
        "log_loss": round(log_loss, 4), "brier": round(brier, 4), "rps": round(rps, 4),
        "accuracy": round(accuracy, 4), "n": int(len(y)),
        "confusion_matrix": {"labels": OUTCOMES, "rows_true_cols_pred": confusion.tolist()},
        "calibration": calibration_curves(y, p),
    }


def calibration_curves(y: np.ndarray, p: np.ndarray, bins: int = 10) -> dict:
    """Probabilidad media predicha vs frecuencia observada, por clase y por tramo."""
    curves = {}
    edges = np.linspace(0, 1, bins + 1)
    for k, name in enumerate(OUTCOMES):
        pk = p[:, k]
        obs = (y == k).astype(float)
        idx = np.clip(np.digitize(pk, edges) - 1, 0, bins - 1)
        pts = []
        for b in range(bins):
            mask = idx == b
            if mask.sum() >= 20:  # tramos con pocos partidos no se muestran
                pts.append({"predicted": round(float(pk[mask].mean()), 4),
                            "observed": round(float(obs[mask].mean()), 4), "n": int(mask.sum())})
        curves[name] = pts
    return curves


def regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    err = y_pred - y_true
    log_err = np.log1p(y_pred) - np.log1p(y_true)
    return {
        "mae_eur": round(float(np.mean(np.abs(err)))),
        "rmse_eur": round(float(np.sqrt(np.mean(err ** 2)))),
        "median_ae_eur": round(float(np.median(np.abs(err)))),
        "median_abs_pct_error": round(float(np.median(np.abs(err) / y_true) * 100), 1),
        "rmse_log": round(float(np.sqrt(np.mean(log_err ** 2))), 4),
        "within_factor_1_5_pct": round(float(np.mean(np.abs(log_err) <= np.log(1.5)) * 100), 1),
        "n": int(len(y_true)),
    }
