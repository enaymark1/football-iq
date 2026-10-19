"""DATOS SINTÉTICOS SOLO PARA TESTS AUTOMATIZADOS.

Genera tablas con el mismo formato que transfermarkt-datasets para probar el
pipeline, los servicios y los modelos sin descargar nada. Ningún dato de acá
se usa en la aplicación ni representa jugadores o partidos reales.
"""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

LEAGUES = [("SYN1", "synthetic-league-one", "Testland"), ("SYN2", "synthetic-league-two", "Mockland")]
TEAMS_PER_LEAGUE = 8
SEASONS = [2021, 2022, 2023]
SQUAD = ["Goalkeeper"] * 2 + ["Defender"] * 5 + ["Midfield"] * 5 + ["Attack"] * 4


def make_raw(seed: int = 7) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    competitions = pd.DataFrame([
        {"competition_id": cid, "name": name, "type": "domestic_league", "sub_type": "first_tier",
         "country_name": country, "confederation": "europa"} for cid, name, country in LEAGUES
    ] + [{"competition_id": "SYNCUP", "name": "synthetic-cup", "type": "domestic_cup", "sub_type": "cup",
          "country_name": "Testland", "confederation": "europa"}])

    clubs, players, team_strength = [], [], {}
    pid = 1000
    for li, (cid, _, _) in enumerate(LEAGUES):
        for t in range(TEAMS_PER_LEAGUE):
            club_id = 100 + li * 50 + t
            team_strength[club_id] = rng.normal(0, 0.35)
            clubs.append({"club_id": club_id, "name": f"Synthetic FC {cid}-{t}", "domestic_competition_id": cid,
                          "stadium_name": f"Test Arena {t}", "stadium_seats": 20000 + t * 1000})
            for pos in SQUAD:
                pid += 1
                players.append({
                    "player_id": pid, "name": f"Test Player {pid}", "image_url": None,
                    "date_of_birth": f"{rng.integers(1990, 2004)}-0{rng.integers(1, 9)}-15",
                    "country_of_citizenship": rng.choice(["Testland", "Mockland", "Fakeland"]),
                    "country_of_birth": "Testland", "position": pos, "sub_position": pos,
                    "foot": rng.choice(["right", "left"]), "height_in_cm": float(rng.integers(168, 196)),
                    "current_club_id": club_id, "market_value_in_eur": None,
                    "highest_market_value_in_eur": None, "url": None, "_club": club_id,
                    "_skill": rng.normal(0, 1),
                })
    players_df = pd.DataFrame(players)

    games, apps = [], []
    gid = 1
    for (cid, _, _), season in itertools.product(LEAGUES, SEASONS):
        club_ids = [c["club_id"] for c in clubs if c["domestic_competition_id"] == cid]
        day = pd.Timestamp(f"{season}-08-01")
        for h, a in itertools.permutations(club_ids, 2):
            lam_h = np.exp(0.35 + team_strength[h] - team_strength[a])
            lam_a = np.exp(0.10 + team_strength[a] - team_strength[h])
            hg, ag = int(rng.poisson(lam_h)), int(rng.poisson(lam_a))
            games.append({"game_id": gid, "competition_id": cid, "season": season, "round": "1. Matchday",
                          "date": day.strftime("%Y-%m-%d"), "home_club_id": h, "away_club_id": a,
                          "home_club_goals": hg, "away_club_goals": ag, "home_club_name": None,
                          "away_club_name": None, "competition_type": "domestic_league"})
            for club, goals in ((h, hg), (a, ag)):
                squad = players_df[players_df["_club"] == club]
                starters = squad.sample(11, random_state=int(rng.integers(1e9)))
                scorers = rng.choice(starters["player_id"], size=goals) if goals else []
                for _, p in starters.iterrows():
                    apps.append({"game_id": gid, "player_id": p["player_id"], "player_club_id": club,
                                 "date": day.strftime("%Y-%m-%d"), "yellow_cards": int(rng.random() < 0.12),
                                 "red_cards": 0, "goals": int(np.sum(scorers == p["player_id"])),
                                 "assists": int(rng.random() < 0.05 + 0.02 * max(p["_skill"], 0)),
                                 "minutes_played": int(rng.choice([90, 90, 90, 75, 60, 30]))})
            gid += 1
            day += pd.Timedelta(days=2)

    vals = []
    for _, p in players_df.iterrows():
        base = np.exp(14 + 0.8 * p["_skill"] + rng.normal(0, 0.3))
        for season in SEASONS:
            vals.append({"player_id": p["player_id"], "date": f"{season + 1}-06-01",
                         "market_value_in_eur": round(base * (1 + 0.1 * (season - 2021)), -4)})
    players_df = players_df.drop(columns=["_club", "_skill"])
    return {
        "competitions": competitions, "clubs": pd.DataFrame(clubs), "players": players_df,
        "games": pd.DataFrame(games), "appearances": pd.DataFrame(apps), "player_valuations": pd.DataFrame(vals),
    }
