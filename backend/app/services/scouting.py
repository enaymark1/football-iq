"""Scouting configurable: filtros obligatorios + puntaje ponderado de percentiles."""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from app.core.errors import InvalidRequestError
from app.services.metrics import METRICS, POSITION_ES, MIN_REFERENCE_MINUTES, percentile_against
from app.services.common import fmt_eur as _fmt_eur
from app.services.common import num as _num


@dataclass
class ScoutingCriteria:
    position: str | None
    metrics: dict[str, float]  # métrica -> peso relativo
    max_age: float | None = None
    max_budget_eur: float | None = None
    league_ids: list[int] = field(default_factory=list)
    min_minutes: int = 900
    nationality: str | None = None
    limit: int = 25


def run_scouting(frame: pd.DataFrame, c: ScoutingCriteria) -> dict:
    if not c.metrics:
        raise InvalidRequestError("Elegí al menos una métrica prioritaria.")
    bad = [k for k in c.metrics if k not in METRICS]
    if bad:
        raise InvalidRequestError(f"Métricas desconocidas: {bad}")
    if any(w < 0 for w in c.metrics.values()) or sum(c.metrics.values()) <= 0:
        raise InvalidRequestError("Los pesos tienen que ser positivos y sumar más que cero.")
    total_w = sum(c.metrics.values())
    weights = {k: w / total_w for k, w in c.metrics.items() if w > 0}

    # 1. Requisitos obligatorios (se informa cuántos quedan en cada paso).
    funnel = [{"step": "Jugadores en la temporada", "remaining": int(len(frame))}]
    pool = frame
    excluded_no_value = 0

    def step(label: str, mask):
        nonlocal pool
        pool = pool[mask]
        funnel.append({"step": label, "remaining": int(len(pool))})

    if c.position:
        step(f"Posición: {POSITION_ES.get(c.position, c.position)}", pool["position"] == c.position)
    if c.league_ids:
        step("Ligas seleccionadas", pool["league_id"].isin(c.league_ids))
    if c.nationality:
        step(f"Nacionalidad: {c.nationality}", pool["nationality"] == c.nationality)
    step(f"{c.min_minutes}+ minutos", pool["minutes"] >= c.min_minutes)
    if c.max_age is not None:
        step(f"Edad <= {c.max_age:g}", pool["age"] <= c.max_age)
    if c.max_budget_eur is not None:
        excluded_no_value = int(pool["market_value_eur"].isna().sum())
        step(f"Valor registrado <= {_fmt_eur(c.max_budget_eur)}", pool["market_value_eur"] <= c.max_budget_eur)

    if pool.empty:
        return {"candidates": [], "funnel": funnel, "weights": weights, "excluded_without_value": excluded_no_value,
                "reference": None}

    # 2-4. Percentil de cada métrica contra los jugadores de la misma posición (dirección incluida) y peso.
    pcts = pd.DataFrame(index=pool.index)
    for position, group in pool.groupby("position", dropna=False):
        ref = frame[(frame["position"] == position) & (frame["minutes"] >= MIN_REFERENCE_MINUTES)]
        for key in weights:
            pcts.loc[group.index, key] = percentile_against(group[key], ref[key], METRICS[key].higher_is_better)

    # 5. Puntaje: promedio ponderado de los percentiles disponibles.
    w = pd.Series(weights)
    avail = pcts.notna()
    score = (pcts.fillna(0) * w).sum(axis=1) / (avail * w).sum(axis=1).replace(0, np.nan)
    coverage = (avail * w).sum(axis=1)
    pool = pool.assign(score=score.round(1), coverage=coverage.round(3))

    # 6. Orden.
    pool = pool.sort_values(["score", "minutes"], ascending=[False, False]).head(c.limit)

    # 7. Explicación generada a partir de los datos.
    out_rows = []
    for pid, row in pool.iterrows():
        p = pcts.loc[pid]
        contrib = (p.fillna(0) * w).sort_values(ascending=False)
        strengths = [k for k in contrib.index if pd.notna(p[k]) and p[k] >= 70][:2]
        weak = [k for k in p.sort_values().index if pd.notna(p[k]) and p[k] < 40][:1]
        parts = []
        if strengths:
            parts.append("Destaca por " + " y ".join(
                f"{METRICS[k].label.lower()} (percentil {p[k]:.0f} de su posición)" for k in strengths))
        else:
            parts.append("No sobresale en ninguna métrica pero no tiene puntos muy bajos")
        reqs = []
        if c.max_budget_eur is not None:
            reqs.append(f"su valor registrado ({_fmt_eur(row['market_value_eur'])}) entra en el presupuesto")
        if c.max_age is not None:
            reqs.append(f"tiene {row['age']:.0f} años (máximo {c.max_age:g})")
        reqs.append(f"jugó {int(row['minutes'])} minutos")
        text = parts[0] + "; " + ", ".join(reqs) + "."
        if weak:
            text += f" Punto más flojo entre lo pedido: {METRICS[weak[0]].label.lower()} (percentil {p[weak[0]]:.0f})."
        if row["coverage"] < 0.999:
            missing = [k for k in weights if pd.isna(p[k])]
            text += f" Sin dato en {', '.join(METRICS[k].label for k in missing)}: no se tuvo en cuenta."
        out_rows.append({
            "player_id": int(pid), "name": row["name"], "position": row["position"], "image_url": row.get("image_url"),
            "team_image_url": row.get("team_image_url"),
            "sub_position": row["sub_position"], "team_name": row["team_name"], "league_name": row["league_name"],
            "age": _num(row["age"]), "minutes": int(row["minutes"]), "market_value_eur": _num(row["market_value_eur"]),
            "rating": _num(row["rating"]), "score": _num(row["score"]), "data_coverage": _num(row["coverage"]),
            "percentiles": {k: _num(p[k]) for k in weights},
            "values": {k: _num(row[k]) for k in weights},
            "explanation": text,
        })
    return {
        "candidates": out_rows, "funnel": funnel, "weights": weights, "excluded_without_value": excluded_no_value,
        "reference": f"Percentiles contra jugadores de la misma posición con {MIN_REFERENCE_MINUTES}+ minutos "
                     "en la temporada (todas las ligas con estadísticas).",
    }
