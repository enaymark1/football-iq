import numpy as np
import pandas as pd

from app.ml import match_features, match_model


def _matches():
    rows = []
    teams = [1, 2, 3, 4]
    mid = 1
    day = pd.Timestamp("2022-08-01")
    for season in (2022, 2023):
        for h in teams:
            for a in teams:
                if h != a:
                    rows.append({"id": mid, "league_id": 1, "season": season, "date": day, "home_team_id": h,
                                 "away_team_id": a, "home_goals": (h + a + mid) % 4, "away_goals": (h * mid) % 3})
                    mid += 1
                    day += pd.Timedelta(days=3)
    return pd.DataFrame(rows)


def test_features_use_only_past_matches():
    m = _matches()
    feats, *_ = match_features.build(m)
    first = feats.iloc[0]
    assert first["min_history"] == 0 and first["elo_diff"] == 0
    # cambiar el resultado de un partido futuro no cambia las variables de los anteriores
    m2 = m.copy()
    m2.loc[m2.index[-1], "home_goals"] = 9
    feats2, *_ = match_features.build(m2)
    cols = match_features.FEATURES
    pd.testing.assert_frame_equal(feats[cols].iloc[:-1], feats2[cols].iloc[:-1])


def test_outcome_probs_sum_to_one():
    p = match_model.outcome_probs(np.array([1.5, 0.3]), np.array([1.1, 2.4]))
    assert np.allclose(p.sum(axis=1), 1)
    assert p[0, 0] > p[0, 2] and p[1, 2] > p[1, 0]


def test_predict_api(client):
    teams = client.get("/api/teams").json()
    a, b = teams[0]["id"], teams[1]["id"]
    r = client.post("/api/matches/predict", json={"home_team_id": a, "away_team_id": b})
    assert r.status_code == 200
    body = r.json()
    for model in ("poisson", "logistic", "baseline"):
        assert abs(sum(body["probabilities"][model].values()) - 1) < 1e-3
    assert body["expected_goals"]["home"] > 0 and body["scorelines"]
    neutral = client.post("/api/matches/predict", json={"home_team_id": a, "away_team_id": b, "neutral": True}).json()
    swapped = client.post("/api/matches/predict", json={"home_team_id": b, "away_team_id": a, "neutral": True}).json()
    assert abs(neutral["probabilities"]["poisson"]["home"] - swapped["probabilities"]["poisson"]["away"]) < 1e-3
    assert client.post("/api/matches/predict", json={"home_team_id": a, "away_team_id": a}).status_code == 422
    assert client.post("/api/matches/predict", json={"home_team_id": a, "away_team_id": 99999}).status_code == 404


def test_models_trained_and_reported(client):
    runs = client.get("/api/models/performance").json()
    keys = {r["model_key"] for r in runs}
    assert {"match_predictor", "market_value", "similarity"} <= keys
    match = next(r for r in runs if r["model_key"] == "match_predictor")
    for k in ("log_loss", "brier", "accuracy", "confusion_matrix", "calibration"):
        assert k in match["metrics"]["poisson"]
    value = next(r for r in runs if r["model_key"] == "market_value")
    assert value["metrics"]["model"]["mae_eur"] > 0 and value["metrics"]["model"]["rmse_eur"] > 0
    assert "baseline_group_median" in value["metrics"]


def test_value_estimate_api(client):
    pid = client.get("/api/players", params={"minutes_min": 900, "page_size": 1}).json()["items"][0]["player_id"]
    r = client.post("/api/market/value-estimate", json={"player_id": pid})
    assert r.status_code == 200
    body = r.json()
    lo, hi = body["typical_range_eur"]
    assert lo < body["estimated_value_eur"] < hi
    profile = {"age": 23, "position": "Attack", "matches": 30, "minutes": 2400, "goals": 10, "assists": 4}
    assert client.post("/api/market/value-estimate", json={"profile": profile}).status_code == 200
    bad = {**profile, "minutes": 9000}
    assert client.post("/api/market/value-estimate", json={"profile": bad}).status_code == 422
    assert client.post("/api/market/value-estimate", json={}).status_code == 422


def test_opportunities_api(client):
    r = client.post("/api/market/opportunities", json={"min_minutes": 500, "limit": 10})
    assert r.status_code == 200
    body = r.json()
    assert body["results"] and "no confirma" in body["disclaimer"]
    scores = [x["score"] for x in body["results"]]
    assert scores == sorted(scores, reverse=True)
    assert all(x["uncertainty"] in ("baja", "media", "alta") for x in body["results"])
    bad = client.post("/api/market/opportunities", json={"weights": {"vibes": 1}})
    assert bad.status_code == 422
