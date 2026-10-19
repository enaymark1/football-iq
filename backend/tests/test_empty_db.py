"""Con la base vacía la API tiene que responder errores claros, no 500."""


def test_health_reports_no_data(empty_client):
    r = empty_client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["data_imported"] is False


def test_endpoints_explain_missing_data(empty_client):
    r = empty_client.get("/api/players")
    assert r.status_code == 409 and "import_data" in r.json()["message"]
    assert empty_client.get("/api/overview").status_code == 409
    assert empty_client.post("/api/scouting/search", json={"metrics": {"goals_p90": 1}}).status_code == 409
    assert empty_client.get("/api/teams").json() == []
    assert empty_client.get("/api/models/performance").json() == []


def test_models_not_trained(empty_client):
    r = empty_client.post("/api/matches/predict", json={"home_team_id": 1, "away_team_id": 2})
    assert r.status_code == 503 and "train_models" in r.json()["message"]
