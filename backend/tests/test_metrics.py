import numpy as np
import pandas as pd

from app.services.metrics import add_derived_metrics, compute_ratings, per90, percentile_against, reliability


def test_per90_basic_and_zero_minutes():
    out = per90(pd.Series([9, 3, 0]), pd.Series([810, 0, 90]))
    assert out[0] == 1.0
    assert np.isnan(out[1])  # sin minutos no hay tasa (no se inventa un 0)
    assert out[2] == 0.0
    assert per90(2, 180) == 1.0


def test_percentile_direction_ties_and_missing():
    ref = pd.Series([1.0, 2.0, 3.0, 4.0])
    up = percentile_against(pd.Series([4.0, 2.5, np.nan]), ref, higher_is_better=True)
    assert up.iloc[0] == 87.5  # 3 por debajo + medio empate = 3.5 / 4
    assert up.iloc[1] == 50.0
    assert np.isnan(up.iloc[2])
    down = percentile_against(pd.Series([1.0]), ref, higher_is_better=False)
    assert down.iloc[0] == 87.5  # el más bajo es el mejor cuando "menos es mejor"


def test_derived_metrics_handle_missing_team_data():
    df = pd.DataFrame([{"goals": 3, "assists": 1, "minutes": 900, "yellow_cards": 2, "red_cards": 0,
                        "team_matches": 20, "team_goals_for": 0, "team_points": 20, "matches": 10,
                        "team_goals_against": 12, "clean_sheets": 3, "matches_60": 0}])
    out = add_derived_metrics(df).iloc[0]
    assert out["goals_p90"] == 0.3
    assert out["minutes_share"] == 0.5
    assert np.isnan(out["goal_involvement_share"])  # equipo sin goles: no hay proporción válida
    assert np.isnan(out["clean_sheet_rate"])
    assert out["team_ppm"] == 2.0


def test_rating_shrinks_low_minutes_towards_50():
    rows = []
    for i in range(20):
        rows.append({"season": 2023, "position": "Attack", "league_id": 1, "minutes": 2000 + i,
                     "goals_p90": i / 20, "assists_p90": 0.1, "goal_involvement_share": 0.2,
                     "minutes_share": 0.8, "team_ppm": 1.5})
    rows.append({"season": 2023, "position": "Attack", "league_id": 1, "minutes": 90, "goals_p90": 2.0,
                 "assists_p90": 1.0, "goal_involvement_share": 0.9, "minutes_share": 0.9, "team_ppm": 3.0})
    out = compute_ratings(pd.DataFrame(rows))
    short = out.iloc[-1]
    best_regular = out.iloc[19]
    assert short["rating_reliability"] < 0.2
    # producción extrema en 90 minutos no supera a un titular consistente
    assert short["rating"] < best_regular["rating"]
    assert 50 <= short["rating"] < 60
    assert reliability([600])[0] == 0.5
