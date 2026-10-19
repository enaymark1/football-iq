"""Evaluación del buscador de similares: "auto-recuperación" entre temporadas.

Idea: el perfil de un jugador en la temporada S debería parecerse a su propio
perfil en S+1 más que al de la mayoría. Para cada jugador con 900+ minutos en
ambas temporadas y la misma posición, se busca su perfil de S entre todos los
perfiles de S+1 de su posición y se mira en qué puesto aparece él mismo.
No mide si los similares "sirven" para fichar; mide estabilidad del perfil.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.services.metrics import POSITION_FEATURES
from app.services.similarity import similarity_matrix

MIN_MINUTES = 900


def evaluate(prev: pd.DataFrame, curr: pd.DataFrame, exclude_age: bool = True) -> dict:
    ranks, pool_sizes = [], []
    per_position = {}
    for position, feats in POSITION_FEATURES.items():
        # la edad sube exactamente 1 año: se excluye para no regalar aciertos
        feats = [f for f in feats if not (exclude_age and f == "age")]
        q = prev[(prev["position"] == position) & (prev["minutes"] >= MIN_MINUTES)]
        pool = curr[(curr["position"] == position) & (curr["minutes"] >= MIN_MINUTES)]
        both = q.index.intersection(pool.index)
        if len(both) < 10:
            continue
        P = pool[feats].astype(float)
        P = P.fillna(P.median())
        mu, sd = P.mean(), P.std(ddof=0).replace(0, np.nan)
        Z = ((P - mu) / sd).fillna(0).to_numpy()
        pos_ranks = []
        for pid in both:
            zq = ((q.loc[pid, feats].astype(float).fillna(P.median()) - mu) / sd).fillna(0).to_numpy()
            sims = similarity_matrix(zq, Z)
            self_sim = sims[pool.index.get_loc(pid)]
            pos_ranks.append(int((sims > self_sim).sum()) + 1)
        per_position[position] = {
            "queries": len(pos_ranks), "pool_size": int(len(pool)),
            "hit_at_10": round(float(np.mean(np.array(pos_ranks) <= 10)), 4),
            "median_rank": float(np.median(pos_ranks)),
            "random_hit_at_10": round(10 / len(pool), 4),
        }
        ranks += pos_ranks
        pool_sizes += [len(pool)] * len(pos_ranks)
    if not ranks:
        return {"queries": 0}
    ranks_arr, pools = np.array(ranks), np.array(pool_sizes)
    return {
        "queries": int(len(ranks)),
        "hit_at_1": round(float(np.mean(ranks_arr == 1)), 4),
        "hit_at_10": round(float(np.mean(ranks_arr <= 10)), 4),
        "median_rank": float(np.median(ranks_arr)),
        "median_percentile_rank": round(float(np.median(ranks_arr / pools) * 100), 2),
        "random_hit_at_10": round(float(np.mean(10 / pools)), 4),
        "by_position": per_position,
        "age_excluded": exclude_age,
    }
