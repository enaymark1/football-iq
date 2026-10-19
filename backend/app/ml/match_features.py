"""Variables previas a cada partido, calculadas en orden cronológico.

Cada fila usa SOLO partidos jugados antes (las estadísticas se actualizan
después de registrar la fila). Así no hay leakage del resultado.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

ELO_START = 1500.0
ELO_NEW_TEAM = 1450.0  # un equipo nuevo en las ligas importadas suele ser un ascendido
ELO_K = 20.0
ELO_HOME_ADV = 60.0
ELO_SEASON_CARRY = 0.8  # al cambiar de temporada, el Elo vuelve 20% hacia 1500
FORM_WINDOW = 10
POINTS_WINDOW = 5
LEAGUE_WINDOW = 380

FEATURES = ["elo_diff", "home_gf10", "home_ga10", "away_gf10", "away_ga10", "home_pts5", "away_pts5",
            "league_home_gpm", "league_away_gpm"]


@dataclass
class TeamState:
    elo: float = ELO_NEW_TEAM
    gf: deque = field(default_factory=lambda: deque(maxlen=FORM_WINDOW))
    ga: deque = field(default_factory=lambda: deque(maxlen=FORM_WINDOW))
    pts: deque = field(default_factory=lambda: deque(maxlen=POINTS_WINDOW))
    n: int = 0
    season: int | None = None
    league_id: int | None = None
    last_date: pd.Timestamp | None = None


@dataclass
class LeagueState:
    home: deque = field(default_factory=lambda: deque(maxlen=LEAGUE_WINDOW))
    away: deque = field(default_factory=lambda: deque(maxlen=LEAGUE_WINDOW))


def _mean(d: deque, default: float) -> float:
    return float(np.mean(d)) if d else default


def team_features(state: TeamState, prefix: str, league: LeagueState) -> dict[str, float]:
    # Sin historial se usa el promedio de la liga: ni ventaja ni castigo.
    avg = (_mean(league.home, 1.4) + _mean(league.away, 1.1)) / 2
    return {f"{prefix}_gf10": _mean(state.gf, avg), f"{prefix}_ga10": _mean(state.ga, avg),
            f"{prefix}_pts5": _mean(state.pts, 1.35)}


def pre_match_row(home: TeamState, away: TeamState, league: LeagueState) -> dict[str, float]:
    row = {"elo_diff": (home.elo - away.elo) / 100.0}
    row.update(team_features(home, "home", league))
    row.update(team_features(away, "away", league))
    row["league_home_gpm"] = _mean(league.home, 1.45)
    row["league_away_gpm"] = _mean(league.away, 1.15)
    return row


def elo_update(home_elo: float, away_elo: float, hg: int, ag: int) -> tuple[float, float]:
    expected_home = 1.0 / (1.0 + 10 ** ((away_elo - home_elo - ELO_HOME_ADV) / 400.0))
    result = 1.0 if hg > ag else 0.5 if hg == ag else 0.0
    margin = np.log(abs(hg - ag) + 1) + 1.0  # victorias amplias mueven más el Elo
    delta = ELO_K * margin * (result - expected_home)
    return home_elo + delta, away_elo - delta


def build(matches: pd.DataFrame) -> tuple[pd.DataFrame, dict[int, TeamState], dict[int, LeagueState], dict]:
    """Recorre los partidos en orden y devuelve variables previas, estados finales e historial de Elo."""
    m = matches.sort_values(["date", "id"]).reset_index(drop=True)
    teams: dict[int, TeamState] = {}
    leagues: dict[int, LeagueState] = {}
    elo_hist: dict[int, list] = {}
    rows = []
    for r in m.itertuples(index=False):
        h = teams.setdefault(r.home_team_id, TeamState())
        a = teams.setdefault(r.away_team_id, TeamState())
        lg = leagues.setdefault(r.league_id, LeagueState())
        for st in (h, a):
            if st.season is not None and st.season != r.season:
                st.elo = ELO_START + ELO_SEASON_CARRY * (st.elo - ELO_START)
        feats = pre_match_row(h, a, lg)
        feats.update(id=r.id, min_history=min(h.n, a.n), home_elo=h.elo, away_elo=a.elo)
        rows.append(feats)

        hg, ag = int(r.home_goals), int(r.away_goals)
        h.elo, a.elo = elo_update(h.elo, a.elo, hg, ag)
        for st, gf, ga in ((h, hg, ag), (a, ag, hg)):
            st.gf.append(gf)
            st.ga.append(ga)
            st.pts.append(3 if gf > ga else 1 if gf == ga else 0)
            st.n += 1
            st.season, st.league_id, st.last_date = r.season, r.league_id, r.date
        lg.home.append(hg)
        lg.away.append(ag)
        elo_hist.setdefault(r.home_team_id, []).append((r.date, round(h.elo, 1)))
        elo_hist.setdefault(r.away_team_id, []).append((r.date, round(a.elo, 1)))
    feats = pd.DataFrame(rows)
    out = m.merge(feats, on="id", how="left")
    out["outcome"] = np.select([out["home_goals"] > out["away_goals"], out["home_goals"] == out["away_goals"]],
                               [0, 1], 2)  # 0 local, 1 empate, 2 visitante
    return out, teams, leagues, elo_hist
