def test_list_players_and_pagination(client):
    r = client.get("/api/players", params={"page_size": 10})
    assert r.status_code == 200
    data = r.json()
    assert data["total"] > 10 and len(data["items"]) == 10 and data["pages"] >= 2
    page2 = client.get("/api/players", params={"page_size": 10, "page": 2}).json()
    assert {i["player_id"] for i in data["items"]}.isdisjoint({i["player_id"] for i in page2["items"]})


def test_filters_combine(client):
    r = client.get("/api/players", params={"position": "Attack", "age_max": 30, "minutes_min": 500,
                                           "sort_by": "goals", "sort_dir": "desc", "page_size": 100})
    items = r.json()["items"]
    assert items
    assert all(i["position"] == "Attack" and i["age"] <= 30 and i["minutes"] >= 500 for i in items)
    goals = [i["goals"] for i in items]
    assert goals == sorted(goals, reverse=True)


def test_search_by_name(client):
    first = client.get("/api/players", params={"page_size": 1}).json()["items"][0]
    r = client.get("/api/players", params={"q": first["name"]})
    assert any(i["player_id"] == first["player_id"] for i in r.json()["items"])


def test_invalid_filters(client):
    assert client.get("/api/players", params={"sort_by": "salary"}).status_code == 422
    assert client.get("/api/players", params={"age_min": 30, "age_max": 20}).status_code == 422
    assert client.get("/api/players", params={"position": "Libero"}).status_code == 422
    assert client.get("/api/players", params={"season": 1990}).status_code == 409


def test_profile_and_missing_player(client):
    pid = client.get("/api/players", params={"page_size": 1, "minutes_min": 1000}).json()["items"][0]["player_id"]
    r = client.get(f"/api/players/{pid}")
    assert r.status_code == 200
    body = r.json()
    assert body["player"]["id"] == pid
    assert body["seasons"] and body["position_comparison"]["metrics"]
    assert "Remates" in body["unavailable_metrics"]
    assert client.get("/api/players/999999").status_code == 404


def test_compare_two_players(client):
    items = client.get("/api/players", params={"position": "Attack", "page_size": 2,
                                               "minutes_min": 900}).json()["items"]
    ids = [i["player_id"] for i in items]
    r = client.post("/api/players/compare", json={"player_ids": ids})
    assert r.status_code == 200
    body = r.json()
    assert body["same_position"] is True
    goals = next(m for m in body["metrics"] if m["metric"] == "goals")
    a, b = goals["values"]
    diff = goals["diff_vs_first"][1]
    if a > 0:
        assert diff["type"] == "percent" and abs(diff["value"] - round((b - a) / a * 100, 1)) < 0.11
    else:
        assert diff is None  # no hay % válido sobre una base 0
    assert len(body["radar"]["percentiles"]) == 2


def test_compare_validation(client):
    assert client.post("/api/players/compare", json={"player_ids": [1]}).status_code == 422
    assert client.post("/api/players/compare", json={"player_ids": [1, 2, 3, 4, 5]}).status_code == 422
    assert client.post("/api/players/compare", json={"player_ids": [1, 1]}).status_code == 422
    assert client.post("/api/players/compare", json={"player_ids": [1, 999999]}).status_code == 404


def test_global_search_and_meta(client):
    r = client.get("/api/search", params={"q": "Synthetic"})
    assert r.status_code == 200 and r.json()["teams"]
    meta = client.get("/api/meta").json()
    assert meta["data"]["imported"] is True
    assert any(m["key"] == "goals_p90" for m in meta["metrics"])


def test_overview_kpis_are_computed(client, session):
    from app.models import PlayerSeasonStats
    body = client.get("/api/overview").json()
    n = session.query(PlayerSeasonStats).filter(PlayerSeasonStats.season == body["season"]).count()
    assert body["kpis"]["players"] == n
    assert sum(p["players"] for p in body["positions"]) == n
