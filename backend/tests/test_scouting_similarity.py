import numpy as np
import pandas as pd
import pytest

from app.core.errors import InvalidRequestError
from app.services.scouting import ScoutingCriteria, run_scouting
from app.services.similarity import find_similar, similarity_matrix


def _frame(rows):
    df = pd.DataFrame(rows)
    defaults = {"sub_position": None, "team_name": "T", "league_name": "L", "league_id": 1, "nationality": "X",
                "rating": 50.0, "market_value_eur": 1e6}
    for k, v in defaults.items():
        if k not in df:
            df[k] = v
    return df.set_index("player_id", drop=False)


def test_cosine_similarity_math():
    sims = similarity_matrix(np.array([1.0, 0.0]), np.array([[2.0, 0.0], [0.0, 3.0], [-1.0, 0.0], [0.0, 0.0]]))
    assert sims.tolist() == [1.0, 0.0, -1.0, 0.0]


def test_similar_excludes_self_and_other_positions():
    rows = [{"player_id": i, "name": f"P{i}", "position": "Attack" if i < 15 else "Defender", "minutes": 2000,
             "age": 20 + i % 10, "goals_p90": i / 30, "assists_p90": 0.1 + (i % 3) / 10,
             "goal_involvement_share": 0.2, "minutes_share": 0.7, "cards_p90": 0.1} for i in range(1, 25)]
    res = find_similar(_frame(rows), 5, k=10)
    ids = [r["player_id"] for r in res["results"]]
    assert 5 not in ids
    assert all(i < 15 for i in ids)  # solo atacantes
    sims = [r["similarity"] for r in res["results"]]
    assert sims == sorted(sims, reverse=True)
    assert all(-1 <= s <= 1 for s in sims)


def test_similar_handles_missing_values():
    rows = [{"player_id": i, "name": f"P{i}", "position": "Attack", "minutes": 2000, "age": 25,
             "goals_p90": i / 30, "assists_p90": np.nan if i == 3 else 0.2, "goal_involvement_share": 0.3,
             "minutes_share": 0.8, "cards_p90": 0.1} for i in range(1, 12)]
    res = find_similar(_frame(rows), 1, k=5)
    imputed = [r for r in res["results"] if r["player_id"] == 3]
    assert not imputed or imputed[0]["imputed_features"] == ["assists_p90"]
    # si el jugador elegido no tiene el dato, esa variable no se usa y se avisa
    res2 = find_similar(_frame(rows), 3, k=5)
    assert "assists_p90" not in res2["features"] and res2["warnings"]


def test_similar_rejects_invalid_features():
    rows = [{"player_id": i, "name": f"P{i}", "position": "Attack", "minutes": 2000, "age": 25,
             "goals_p90": i / 10, "assists_p90": 0.1, "goal_involvement_share": 0.1, "minutes_share": 0.5,
             "cards_p90": 0.1} for i in range(1, 5)]
    with pytest.raises(InvalidRequestError):
        find_similar(_frame(rows), 1, features=["salary", "goals_p90"])


def _scout_frame():
    rows = []
    for i in range(1, 41):
        rows.append({"player_id": i, "name": f"P{i}", "position": "Midfield", "minutes": 500 + i * 60,
                     "age": 18 + i % 15, "market_value_eur": i * 5e5 if i != 7 else np.nan,
                     "assists_p90": i / 100, "cards_p90": (40 - i) / 100, "goals_p90": 0.1})
    return _frame(rows)


def test_scouting_filters_and_ranking():
    frame = _scout_frame()
    res = run_scouting(frame, ScoutingCriteria(position="Midfield", max_age=25, max_budget_eur=1.5e7,
                                               min_minutes=900, metrics={"assists_p90": 1}))
    cands = res["candidates"]
    assert cands
    assert all(c["age"] <= 25 and c["market_value_eur"] <= 1.5e7 and c["minutes"] >= 900 for c in cands)
    assert [c["score"] for c in cands] == sorted([c["score"] for c in cands], reverse=True)
    assert "presupuesto" in cands[0]["explanation"]
    assert res["funnel"][0]["remaining"] == 40


def test_scouting_lower_is_better_direction():
    frame = _scout_frame()
    res = run_scouting(frame, ScoutingCriteria(position=None, metrics={"cards_p90": 1}, min_minutes=0, limit=5))
    # menos tarjetas = mejor: los primeros son los de id alto (menos tarjetas)
    assert res["candidates"][0]["player_id"] == 40


def test_scouting_requires_metrics():
    with pytest.raises(InvalidRequestError):
        run_scouting(_scout_frame(), ScoutingCriteria(position=None, metrics={}))


def test_scouting_api_validation(client):
    r = client.post("/api/scouting/search", json={"metrics": {"made_up": 1}})
    assert r.status_code == 422
    r = client.post("/api/scouting/search", json={"metrics": {"goals_p90": 2, "assists_p90": 1},
                                                  "position": "Attack", "min_minutes": 500})
    assert r.status_code == 200 and r.json()["candidates"]


def test_similar_api(client):
    pid = client.get("/api/players", params={"position": "Defender", "minutes_min": 400,
                                             "page_size": 1}).json()["items"][0]["player_id"]
    r = client.get(f"/api/players/{pid}/similar", params={"k": 5, "min_minutes": 200})
    assert r.status_code == 200
    body = r.json()
    assert len(body["results"]) == 5 and all(x["player_id"] != pid for x in body["results"])
    assert "no una probabilidad" in body["index_note"]
