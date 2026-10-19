"""Jugadores similares: similitud coseno sobre métricas estandarizadas.

El índice va de -1 a 1 (se muestra x100). Es una medida geométrica entre
perfiles estadísticos, no una probabilidad.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.core.errors import InvalidRequestError, NotFoundError
from app.services.common import num as _num
from app.services.metrics import METRICS, POSITION_FEATURES

DEFAULT_MIN_MINUTES = 900


def validate_features(features: list[str] | None, position: str) -> list[str]:
    if not features:
        return list(POSITION_FEATURES[position])
    unknown = [f for f in features if f not in METRICS or METRICS[f].unit in ("eur",)]
    if unknown:
        raise InvalidRequestError(f"Variables no válidas para similitud: {unknown}",
                                  details={"allowed": [k for k, m in METRICS.items() if m.unit != "eur"]})
    if len(set(features)) < 2:
        raise InvalidRequestError("Hacen falta al menos 2 variables distintas para comparar perfiles.")
    return list(dict.fromkeys(features))


def _describe_z(z: float) -> str:
    if z >= 1.5:
        return "muy por encima del promedio"
    if z >= 0.5:
        return "por encima del promedio"
    if z <= -1.5:
        return "muy por debajo del promedio"
    if z <= -0.5:
        return "por debajo del promedio"
    return "en el promedio"


def similarity_matrix(target: np.ndarray, pool: np.ndarray) -> np.ndarray:
    """Coseno entre un vector y cada fila de una matriz. Vectores nulos dan 0."""
    t_norm = np.linalg.norm(target)
    p_norm = np.linalg.norm(pool, axis=1)
    denom = t_norm * p_norm
    with np.errstate(divide="ignore", invalid="ignore"):
        sims = np.where(denom > 0, pool @ target / denom, 0.0)
    return sims


def find_similar(frame: pd.DataFrame, player_id: int, *, features: list[str] | None = None, k: int = 10,
                 min_minutes: int = DEFAULT_MIN_MINUTES) -> dict:
    if frame.empty or player_id not in frame.index:
        raise NotFoundError("El jugador no tiene estadísticas en esa temporada.")
    target = frame.loc[player_id]
    position = target["position"]
    if position not in POSITION_FEATURES:
        raise InvalidRequestError("El jugador no tiene una posición registrada; no se puede comparar el perfil.")
    feats = validate_features(features, position)
    warnings: list[str] = []

    # Solo jugadores de la misma posición: no se comparan perfiles incompatibles.
    pool = frame[(frame["position"] == position) & (frame["minutes"] >= min_minutes)
                 & (frame["player_id"] != player_id)]
    if target["minutes"] < min_minutes:
        warnings.append(f"El jugador elegido tiene {int(target['minutes'])} minutos (menos de {min_minutes}): "
                        "su perfil es poco estable y la similitud es orientativa.")
    if len(pool) < k:
        warnings.append(f"Solo hay {len(pool)} candidatos con {min_minutes}+ minutos en la posición.")
    if pool.empty:
        return {"features": feats, "results": [], "pool_size": 0, "warnings": warnings, "position": position}

    used = [f for f in feats if pd.notna(target[f])]
    dropped = [f for f in feats if f not in used]
    if dropped:
        warnings.append(f"Sin dato para el jugador elegido en {dropped}: esas variables no se usan.")
    if len(used) < 2:
        raise InvalidRequestError("El jugador elegido no tiene datos suficientes para calcular similitud.")

    ref = pd.concat([pool[used], target[used].to_frame().T]).astype(float)
    means, stds = ref.mean(), ref.std(ddof=0).replace(0, np.nan)
    medians = pool[used].astype(float).median()
    pool_vals = pool[used].astype(float)
    imputed = pool_vals.isna()
    pool_vals = pool_vals.fillna(medians)  # faltantes del candidato -> mediana de la posición
    z_pool = ((pool_vals - means) / stds).fillna(0.0)
    z_target = ((target[used].astype(float) - means) / stds).fillna(0.0)

    sims = similarity_matrix(z_target.to_numpy(), z_pool.to_numpy())
    order = np.argsort(-sims)[:k]
    results = []
    for idx in order:
        cand = pool.iloc[idx]
        zc = z_pool.iloc[idx]
        diffs = (zc - z_target).abs()
        shared = [f for f in diffs.sort_values().index if abs(z_target[f]) >= 0.5 and np.sign(zc[f]) == np.sign(z_target[f])][:3]
        different = [f for f in diffs.sort_values(ascending=False).index if diffs[f] >= 1.0][:2]
        expl = []
        if shared:
            expl.append("Comparten: " + "; ".join(f"{METRICS[f].label} {_describe_z(z_target[f])}" for f in shared))
        if different:
            expl.append("Se diferencian en: " + ", ".join(METRICS[f].label for f in different))
        results.append({
            "player_id": int(cand["player_id"]), "name": cand["name"], "team_name": cand["team_name"],
            "image_url": cand.get("image_url"), "team_image_url": cand.get("team_image_url"),
            "league_name": cand["league_name"], "age": _num(cand["age"]), "minutes": int(cand["minutes"]),
            "market_value_eur": _num(cand["market_value_eur"]), "rating": _num(cand["rating"]),
            "similarity": round(float(sims[idx]), 4),
            "values": {f: _num(pool.iloc[idx][f]) for f in used},
            "imputed_features": [f for f in used if imputed.iloc[idx][f]],
            "shared_traits": shared, "main_differences": different,
            "explanation": ". ".join(expl) if expl else "Perfil parecido en todas las variables, sin rasgos extremos.",
        })
    return {
        "position": position, "features": used, "pool_size": int(len(pool)), "min_minutes": min_minutes,
        "target_values": {f: _num(target[f]) for f in used}, "results": results, "warnings": warnings,
    }

