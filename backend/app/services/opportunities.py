"""Índice de Oportunidad Estadística (IOE) — métrica propia de Football IQ.

NO es una valoración oficial ni afirma que un jugador esté infravalorado en el
mercado. Combina, con pesos configurables (0-100 cada componente):

  performance  FIQ Rating: percentil por posición dentro de su liga, encogido hacia 50
               cuando hay pocos minutos.
  value        Percentil inverso del valor registrado dentro de su posición: más barato, más alto.
  model_gap    Percentil de log(valor estimado por el modelo / valor registrado). Solo
               para temporadas que el modelo no vio al entrenar.
  age          Juventud: 100 a los 18 años o menos, 0 a los 32 o más (lineal).
  minutes      % de los minutos de liga de su club que jugó.

Índice = suma ponderada x factor de confianza, con
confianza = min(1, minutos / 2000) y factor = 0,75 + 0,25 x confianza.
Así la falta de minutos resta, pero además queda marcada como incertidumbre.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from app.core.errors import InvalidRequestError
from app.services.common import fmt_eur, num
from app.services.metrics import MIN_REFERENCE_MINUTES, percentile_against

COMPONENTS = {
    "performance": "Rendimiento ajustado por posición (FIQ Rating)",
    "value": "Valor de mercado bajo dentro de su posición",
    "model_gap": "Valor estimado por el modelo por encima del registrado",
    "age": "Edad / proyección",
    "minutes": "Continuidad (minutos jugados)",
}
DEFAULT_WEIGHTS = {"performance": 0.40, "value": 0.25, "model_gap": 0.15, "age": 0.10, "minutes": 0.10}
FULL_CONFIDENCE_MINUTES = 2000
SORTABLE = {"score", "age", "market_value_eur", "rating", "minutes"}


@dataclass
class OpportunityQuery:
    weights: dict[str, float] = field(default_factory=lambda: dict(DEFAULT_WEIGHTS))
    position: str | None = None
    league_ids: list[int] = field(default_factory=list)
    max_age: float | None = None
    max_value_eur: float | None = None
    min_minutes: int = 900
    sort_by: str = "score"
    sort_dir: str = "desc"
    limit: int = 50


def _lc(text: str) -> str:
    return text[:1].lower() + text[1:]


def uncertainty_level(minutes: float, coverage: float) -> str:
    if minutes < 900 or coverage < 0.6:
        return "alta"
    if minutes < 1800 or coverage < 0.8:
        return "media"
    return "baja"


def compute(frame: pd.DataFrame, q: OpportunityQuery, predicted_value: pd.Series | None) -> dict:
    unknown = set(q.weights) - set(COMPONENTS)
    if unknown:
        raise InvalidRequestError(f"Componentes desconocidos: {sorted(unknown)}", details={"allowed": list(COMPONENTS)})
    if any(w < 0 for w in q.weights.values()) or sum(q.weights.values()) <= 0:
        raise InvalidRequestError("Los pesos tienen que ser positivos y sumar más que cero.")
    if q.sort_by not in SORTABLE:
        raise InvalidRequestError(f"sort_by debe ser uno de {sorted(SORTABLE)}")

    notes = []
    weights = {k: v for k, v in q.weights.items() if v > 0}
    if predicted_value is None and "model_gap" in weights:
        weights.pop("model_gap")
        notes.append("El componente 'modelo' no se usa: no hay estimaciones fuera de muestra para esta temporada "
                     "(modelo no entrenado o temporada usada en el entrenamiento). Su peso se repartió.")
    total = sum(weights.values())
    weights = {k: v / total for k, v in weights.items()}

    df = frame.copy()
    value_col = df["market_value_end_eur"].fillna(df["market_value_eur"])
    df["value_used"] = value_col
    without_value = int(df["value_used"].isna().sum())
    # sin valor registrado no se puede hablar de oportunidad de mercado: se excluye y se informa
    df = df[df["value_used"].notna() & df["position"].notna()]
    if predicted_value is not None:
        df["predicted_value"] = predicted_value.reindex(df.index)

    comp = pd.DataFrame(index=df.index)
    comp["performance"] = df["rating"]
    for position, group in df.groupby("position"):
        ref = group[group["minutes"] >= MIN_REFERENCE_MINUTES]
        comp.loc[group.index, "value"] = percentile_against(group["value_used"], ref["value_used"], False)
        if predicted_value is not None:
            gap = np.log(group["predicted_value"] / group["value_used"])
            ref_gap = np.log(ref["predicted_value"] / ref["value_used"])
            comp.loc[group.index, "model_gap"] = percentile_against(gap, ref_gap, True)
    comp["age"] = np.clip((32 - df["age"]) / (32 - 18), 0, 1) * 100
    comp["minutes"] = df["minutes_share"] * 100

    w = pd.Series(weights)
    present = comp[list(weights)].notna()
    raw = (comp[list(weights)].fillna(0) * w).sum(axis=1) / (present * w).sum(axis=1).replace(0, np.nan)
    confidence = np.minimum(1.0, df["minutes"] / FULL_CONFIDENCE_MINUTES)
    checks = pd.DataFrame({
        "value": df["value_used"].notna(), "age": df["age"].notna(), "rating": df["rating"].notna(),
        "minutes_900": df["minutes"] >= 900,
        "recent_value": pd.to_datetime(df["market_value_date"])
        >= pd.to_datetime(df["market_value_date"]).max() - pd.Timedelta(days=400),
    })
    if predicted_value is not None:
        checks["model_estimate"] = df["predicted_value"].notna()
    coverage = checks.mean(axis=1)
    df["score"] = (raw * (0.75 + 0.25 * confidence)).round(1)
    df["confidence"] = confidence.round(3)
    df["coverage"] = coverage.round(3)

    # filtros pedidos
    pool = df[df["minutes"] >= q.min_minutes]
    if q.position:
        pool = pool[pool["position"] == q.position]
    if q.league_ids:
        pool = pool[pool["league_id"].isin(q.league_ids)]
    if q.max_age is not None:
        pool = pool[pool["age"] <= q.max_age]
    if q.max_value_eur is not None:
        pool = pool[pool["value_used"] <= q.max_value_eur]
    sort_col = "value_used" if q.sort_by == "market_value_eur" else q.sort_by
    pool = pool.sort_values([sort_col, "score"], ascending=[q.sort_dir == "asc", False], na_position="last")
    total_matches = int(len(pool))
    pool = pool.head(q.limit)

    rows = []
    for pid, r in pool.iterrows():
        c = comp.loc[pid]
        contributions = {k: round(float(c[k] * w[k]), 1) if pd.notna(c[k]) else None for k in weights}
        top = sorted([k for k in weights if contributions[k] is not None], key=lambda k: -contributions[k])[:2]
        level = uncertainty_level(r["minutes"], r["coverage"])
        parts = ["Aporta sobre todo " + " y ".join(_lc(COMPONENTS[k]) for k in top)]
        parts.append(f"FIQ Rating {r['rating']:.0f}, valor registrado {fmt_eur(r['value_used'])}")
        if predicted_value is not None and pd.notna(r.get("predicted_value")):
            parts.append(f"el modelo estima {fmt_eur(r['predicted_value'])} con su perfil")
        parts.append(f"{int(r['minutes'])} minutos en {int(r['matches'])} partidos (incertidumbre {level})")
        rows.append({
            "player_id": int(pid), "name": r["name"], "position": r["position"], "sub_position": r["sub_position"],
            "image_url": r.get("image_url"), "team_image_url": r.get("team_image_url"),
            "team_name": r["team_name"], "league_name": r["league_name"], "age": num(r["age"]),
            "minutes": int(r["minutes"]), "matches": int(r["matches"]), "rating": num(r["rating"]),
            "market_value_eur": num(r["value_used"]),
            "predicted_value_eur": num(r.get("predicted_value")) if predicted_value is not None else None,
            "score": num(r["score"]), "confidence": num(r["confidence"]), "data_coverage": num(r["coverage"]),
            "uncertainty": level, "components": {k: num(c[k]) for k in weights}, "contributions": contributions,
            "explanation": "; ".join(parts) + ".",
        })
    return {"results": rows, "total": total_matches, "weights": weights, "components": COMPONENTS,
            "excluded_without_value": without_value, "notes": notes,
            "disclaimer": "Índice propio de Football IQ: señala oportunidades estadísticas, no confirma que un "
                          "jugador esté infravalorado en el mercado."}
