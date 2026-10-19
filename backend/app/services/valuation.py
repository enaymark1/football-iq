"""Estimación de valor de mercado (jugador existente o perfil hipotético)."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.core.errors import InvalidRequestError, NotFoundError
from app.ml import registry, value_model
from app.repositories import models as models_repo
from app.repositories import players as players_repo
from app.services.common import num
from app.services.metrics import add_derived_metrics


def predicted_values(frame: pd.DataFrame) -> pd.Series | None:
    """Estimaciones fuera de muestra para una temporada (None si el modelo la vio al entrenar)."""
    artifact = registry.try_load(value_model.MODEL_KEY)
    if artifact is None or frame.empty or int(frame["season"].iloc[0]) <= artifact["train_max_season"]:
        return None
    return pd.Series(value_model.predict_frame(artifact, frame), index=frame.index)


def estimate(session: Session, player_id: int | None, season: int | None, profile: dict | None) -> dict:
    artifact = registry.load(value_model.MODEL_KEY)
    run = models_repo.latest_run(session, value_model.MODEL_KEY)
    if player_id is not None:
        df = players_repo.players_frame(session, [player_id], season)
        if df.empty:
            raise NotFoundError("El jugador no tiene estadísticas para estimar su valor.")
        row = df.iloc[0]
        registered = num(row["market_value_end_eur"]) or num(row["market_value_eur"])
        subject = {"type": "player", "player_id": player_id, "name": row["name"], "season": int(row["season"])}
    elif profile is not None:
        base = {k: profile.get(k) for k in ("age", "position", "sub_position", "league_name", "foot", "height_cm",
                                            "matches", "minutes", "goals", "assists", "yellow_cards", "red_cards",
                                            "team_matches", "team_goals_for", "team_goals_against", "team_points",
                                            "clean_sheets", "matches_60")}
        df = add_derived_metrics(pd.DataFrame([base]).astype({"minutes": float}))
        df["season"] = artifact["train_max_season"] + 1
        row = df.iloc[0]
        registered = None
        subject = {"type": "profile"}
    else:
        raise InvalidRequestError("Indicá player_id o un perfil.")

    pred = value_model.predict_frame(artifact, df.iloc[[0]] if player_id is not None else df)[0]
    if np.isnan(pred):
        raise InvalidRequestError("Faltan edad o posición: no se puede estimar.")
    band = artifact["error_band"]
    notes = value_model.confidence_notes(artifact, row)
    m = run.metrics["model"] if run else {}
    reliable = row["minutes"] >= 900 and not any("pocas observaciones" in n for n in notes)
    return {
        "subject": subject,
        "estimated_value_eur": float(pred),
        "typical_range_eur": [float(pred / band["p90_ratio"]), float(pred / band["p10_ratio"])],
        "registered_value_eur": registered,
        "difference_pct": round((pred - registered) / registered * 100, 1) if registered else None,
        "reliable": bool(reliable), "notes": notes,
        "model_metrics": {k: m.get(k) for k in ("mae_eur", "rmse_eur", "median_abs_pct_error")},
        "explanation": (
            "Estimación a partir de edad, posición, liga, minutos y producción de la temporada. El rango típico "
            "cubre el 80% de los errores observados en la evaluación. No usa el historial de valores, así que "
            "puede diferir mucho del valor registrado por razones que el modelo no ve (contrato, selección, "
            "potencial, lesiones)."),
    }
