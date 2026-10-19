import pandas as pd
import pytest

from app.data import pipeline
from app.data.sources import transfermarkt


def test_build_cleans_duplicates_and_invalid_rows(raw_tables):
    raw = {k: v.copy() for k, v in raw_tables.items()}
    raw["games"] = pd.concat([raw["games"], raw["games"].head(3)])  # duplicados
    bad = raw["appearances"].head(1).copy()
    bad["player_club_id"] = 999999  # club que no jugó ese partido
    bad["player_id"] = 424242  # otro jugador, para que no se descarte antes como duplicado
    raw["appearances"] = pd.concat([raw["appearances"], bad])
    res = pipeline.build(raw, source="synthetic", first_player_season=2021)
    assert res.report["dropped"]["matches_duplicated"] == 3
    assert res.report["dropped"]["appearances_club_not_in_match"] == 1
    t = res.tables
    assert t["matches"]["source_id"].is_unique
    assert len(t["leagues"]) == 2  # la copa no es liga doméstica
    assert t["player_season_stats"][["player_id", "season"]].duplicated().sum() == 0
    assert (t["player_season_stats"]["minutes"] > 0).all()
    assert res.report["coverage"]["matches_with_appearances_pct"] == 100.0


def test_missing_columns_raise(tmp_path, raw_tables):
    for name, df in raw_tables.items():
        if name == "players":
            df = df.drop(columns=["position"])
        df.to_csv(tmp_path / f"{name}.csv.gz", index=False)
    with pytest.raises(transfermarkt.SourceError, match="position"):
        transfermarkt.read(tmp_path)


def test_internal_ids_do_not_reuse_source_ids(raw_tables):
    res = pipeline.build(raw_tables, source="synthetic", first_player_season=2021)
    players = res.tables["players"]
    assert players["id"].min() == 1
    assert set(players["source_id"]) <= {str(i) for i in raw_tables["players"]["player_id"]}
