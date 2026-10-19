"""Predictor de partidos: Poisson (principal), logística multinomial (comparación) y baseline.

Validación cronológica: se entrena con temporadas viejas y se evalúa con las
más recientes. Las variables de cada partido usan solo partidos anteriores.
"""
from __future__ import annotations

from datetime import date

import numpy as np
import pandas as pd
from scipy.stats import poisson
from sklearn.linear_model import LogisticRegression, PoissonRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from app.core.errors import InvalidRequestError, NotFoundError
from app.ml import match_features as mf
from app.ml.evaluation import multiclass_metrics

MAX_GOALS = 10
MIN_HISTORY = 5
MODEL_KEY = "match_predictor"


def outcome_probs(lam_home: np.ndarray, lam_away: np.ndarray) -> np.ndarray:
    """Probabilidades 1X2 suponiendo goles Poisson independientes."""
    goals = np.arange(MAX_GOALS + 1)
    ph = poisson.pmf(goals[None, :], np.asarray(lam_home)[:, None])
    pa = poisson.pmf(goals[None, :], np.asarray(lam_away)[:, None])
    grid = ph[:, :, None] * pa[:, None, :]
    home = np.tril(np.ones((MAX_GOALS + 1, MAX_GOALS + 1)), -1)
    p_home = (grid * home).sum(axis=(1, 2))
    p_draw = np.trace(grid, axis1=1, axis2=2)
    p_away = (grid * home.T).sum(axis=(1, 2))
    probs = np.stack([p_home, p_draw, p_away], axis=1)
    return probs / probs.sum(axis=1, keepdims=True)


def _fit(train: pd.DataFrame) -> dict:
    X = train[mf.FEATURES].to_numpy()
    pois_home = make_pipeline(StandardScaler(), PoissonRegressor(alpha=1e-4, max_iter=1000)).fit(X, train["home_goals"])
    pois_away = make_pipeline(StandardScaler(), PoissonRegressor(alpha=1e-4, max_iter=1000)).fit(X, train["away_goals"])
    logit = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000, C=1.0)).fit(X, train["outcome"])
    baseline = np.bincount(train["outcome"], minlength=3) / len(train)
    return {"poisson_home": pois_home, "poisson_away": pois_away, "logit": logit, "baseline": baseline}


def _predict_all(models: dict, X: np.ndarray) -> dict[str, np.ndarray]:
    lam_h = models["poisson_home"].predict(X)
    lam_a = models["poisson_away"].predict(X)
    return {
        "poisson": outcome_probs(lam_h, lam_a),
        "logistic": models["logit"].predict_proba(X),
        "baseline": np.tile(models["baseline"], (len(X), 1)),
        "lam_home": lam_h, "lam_away": lam_a,
    }


def train_and_evaluate(matches: pd.DataFrame, test_seasons: int = 3) -> tuple[dict, dict]:
    if matches.empty:
        raise ValueError("No hay partidos importados.")
    feats, teams, leagues, elo_hist = mf.build(matches)
    usable = feats[feats["min_history"] >= MIN_HISTORY]
    seasons = sorted(usable["season"].unique())
    if len(seasons) < 2:
        raise ValueError("Hacen falta al menos 2 temporadas para separar entrenamiento y evaluación.")
    n_test = min(test_seasons, max(1, len(seasons) // 3))  # con pocas temporadas, se entrena con la mayoría
    test_from = seasons[-n_test]
    train, test = usable[usable["season"] < test_from], usable[usable["season"] >= test_from]

    models = _fit(train)
    preds = _predict_all(models, test[mf.FEATURES].to_numpy())
    y = test["outcome"].to_numpy()
    metrics = {name: multiclass_metrics(y, preds[name]) for name in ("poisson", "logistic", "baseline")}
    metrics["poisson"]["goals_mae_home"] = round(float(np.mean(np.abs(preds["lam_home"] - test["home_goals"]))), 4)
    metrics["poisson"]["goals_mae_away"] = round(float(np.mean(np.abs(preds["lam_away"] - test["away_goals"]))), 4)
    metrics["split"] = {"train_seasons": [int(seasons[0]), int(test_from - 1)],
                        "test_seasons": [int(test_from), int(seasons[-1])],
                        "test_outcome_rates": [round(float(v), 4) for v in np.bincount(y, minlength=3) / len(y)]}

    # Modelo final: misma configuración, reentrenado con todos los partidos disponibles.
    final = _fit(usable)
    artifact = {
        **final,
        "features": mf.FEATURES,
        "teams": {tid: {"elo": s.elo, "gf": list(s.gf), "ga": list(s.ga), "pts": list(s.pts), "n": s.n,
                        "league_id": s.league_id, "season": s.season,
                        "last_date": s.last_date.date() if s.last_date is not None else None}
                  for tid, s in teams.items()},
        "leagues": {lid: {"home": list(s.home), "away": list(s.away)} for lid, s in leagues.items()},
        "elo_history": {tid: [(d.date(), e) for d, e in h] for tid, h in elo_hist.items()},
        "data_end": feats["date"].max().date(),
    }
    info = {"n_train": int(len(train)), "n_test": int(len(test)), "metrics": metrics,
            "coefficients": _coefficients(final)}
    return artifact, info


def _coefficients(models: dict) -> dict:
    def coefs(pipe):
        return {f: round(float(c), 4) for f, c in zip(mf.FEATURES, pipe[-1].coef_)}
    return {"poisson_home": coefs(models["poisson_home"]), "poisson_away": coefs(models["poisson_away"])}


def _state(artifact: dict, team_id: int) -> mf.TeamState:
    t = artifact["teams"].get(team_id)
    if t is None:
        raise NotFoundError(f"El equipo {team_id} no tiene partidos de liga importados.")
    st = mf.TeamState(elo=t["elo"], n=t["n"], season=t["season"], league_id=t["league_id"])
    st.gf.extend(t["gf"])
    st.ga.extend(t["ga"])
    st.pts.extend(t["pts"])
    return st


def _league_state(artifact: dict, league_ids: list[int]) -> mf.LeagueState:
    lg = mf.LeagueState()
    for lid in league_ids:
        s = artifact["leagues"].get(lid, {"home": [], "away": []})
        lg.home.extend(s["home"][-mf.LEAGUE_WINDOW // len(league_ids):])
        lg.away.extend(s["away"][-mf.LEAGUE_WINDOW // len(league_ids):])
    return lg


def _single(artifact: dict, home_id: int, away_id: int) -> dict:
    h, a = _state(artifact, home_id), _state(artifact, away_id)
    lg = _league_state(artifact, sorted({h.league_id, a.league_id}))
    X = np.array([[mf.pre_match_row(h, a, lg)[f] for f in mf.FEATURES]])
    p = _predict_all(artifact, X)
    lam_h, lam_a = float(p["lam_home"][0]), float(p["lam_away"][0])
    return {"poisson": p["poisson"][0], "logistic": p["logistic"][0], "baseline": p["baseline"][0],
            "lam_home": lam_h, "lam_away": lam_a}


def predict(artifact: dict, home_id: int, away_id: int, neutral: bool = False) -> dict:
    if home_id == away_id:
        raise InvalidRequestError("Elegí dos equipos distintos.")
    res = _single(artifact, home_id, away_id)
    if neutral:
        # cancha neutral: promedio de las dos localías posibles
        rev = _single(artifact, away_id, home_id)
        for k in ("poisson", "logistic", "baseline"):
            res[k] = (res[k] + rev[k][::-1]) / 2
        res["lam_home"], res["lam_away"] = (res["lam_home"] + rev["lam_away"]) / 2, (res["lam_away"] + rev["lam_home"]) / 2

    goals = np.arange(MAX_GOALS + 1)
    grid = np.outer(poisson.pmf(goals, res["lam_home"]), poisson.pmf(goals, res["lam_away"]))
    flat = np.argsort(-grid, axis=None)[:8]
    scorelines = [{"home": int(i // (MAX_GOALS + 1)), "away": int(i % (MAX_GOALS + 1)),
                   "probability": round(float(grid.flat[i]), 4)} for i in flat]

    th, ta = artifact["teams"][home_id], artifact["teams"][away_id]
    warnings = []
    if th["league_id"] != ta["league_id"]:
        warnings.append("Los equipos juegan en ligas distintas: el Elo y la forma se miden dentro de cada liga, "
                        "así que la comparación entre ligas no es confiable.")
    data_end: date = artifact["data_end"]
    for t, label in ((th, "local"), (ta, "visitante")):
        if t["n"] < 15:
            warnings.append(f"El equipo {label} tiene solo {t['n']} partidos en los datos: predicción poco confiable.")
        if t["last_date"] and (data_end - t["last_date"]).days > 200:
            warnings.append(f"El equipo {label} no juega en las ligas importadas desde {t['last_date']} "
                            "(posible descenso): su estado puede estar desactualizado.")
    return {
        "probabilities": {k: dict(zip(["home", "draw", "away"], np.round(res[k], 4).tolist()))
                          for k in ("poisson", "logistic", "baseline")},
        "expected_goals": {"home": round(res["lam_home"], 2), "away": round(res["lam_away"], 2)},
        "scorelines": scorelines,
        "team_context": {
            "home": {"elo": round(th["elo"], 1), "matches": th["n"], "last_match": th["last_date"],
                     "recent_gf": round(float(np.mean(th["gf"])), 2) if th["gf"] else None,
                     "recent_ga": round(float(np.mean(th["ga"])), 2) if th["ga"] else None,
                     "recent_points": th["pts"]},
            "away": {"elo": round(ta["elo"], 1), "matches": ta["n"], "last_match": ta["last_date"],
                     "recent_gf": round(float(np.mean(ta["gf"])), 2) if ta["gf"] else None,
                     "recent_ga": round(float(np.mean(ta["ga"])), 2) if ta["ga"] else None,
                     "recent_points": ta["pts"]},
        },
        "neutral": neutral, "data_as_of": data_end, "warnings": warnings,
    }
