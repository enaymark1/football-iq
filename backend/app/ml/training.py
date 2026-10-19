"""Entrena y evalúa todos los modelos y guarda artefactos + métricas en la base."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy.orm import Session

from app.ml import match_features, match_model, registry, similarity_eval, value_model
from app.models import ModelRun
from app.repositories import meta as meta_repo
from app.repositories import models as models_repo
from app.repositories import players as players_repo
from app.repositories import teams as teams_repo
from app.services.metrics import POSITION_FEATURES

log = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def all_seasons_frame(session: Session) -> pd.DataFrame:
    seasons = meta_repo.player_seasons(session)
    frames = [players_repo.season_frame(session, s) for s in seasons]
    frames = [f for f in frames if not f.empty]
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def train_match_model(session: Session, models_dir: Path | None = None) -> ModelRun:
    matches = teams_repo.matches_frame(session)
    artifact, info = match_model.train_and_evaluate(matches)
    path = registry.save(match_model.MODEL_KEY, artifact, models_dir)
    m = info["metrics"]
    return models_repo.save_run(session, ModelRun(
        model_key=match_model.MODEL_KEY, name="Predictor de partidos (Poisson + Elo)",
        objective="Probabilidades de victoria local, empate y victoria visitante, y goles esperados.",
        trained_at=_now(), n_train=info["n_train"], n_test=info["n_test"], features=match_features.FEATURES,
        metrics={**m, "coefficients": info["coefficients"]},
        validation=(f"Cronológica: entrenamiento con temporadas {m['split']['train_seasons'][0]}–"
                    f"{m['split']['train_seasons'][1]}, evaluación con {m['split']['test_seasons'][0]}–"
                    f"{m['split']['test_seasons'][1]}. Cada variable usa solo partidos anteriores al encuentro. "
                    f"Se excluyen partidos donde algún equipo tiene menos de {match_model.MIN_HISTORY} partidos "
                    "previos. El modelo publicado se reentrena con todas las temporadas con la misma configuración."),
        limitations=[
            "Solo usa resultados y goles: no conoce lesiones, alineaciones, mercado de pases ni cuotas.",
            "Goles local y visitante se modelan como Poisson independientes: subestima levemente los empates.",
            "El Elo es relativo a cada liga; comparar equipos de ligas distintas no es confiable.",
            "Las ligas no europeas solo tienen 2 temporadas en la fuente: menos historial.",
        ],
        artifact_path=str(path),
    ))


def train_value_model(session: Session, frame: pd.DataFrame, models_dir: Path | None = None) -> ModelRun:
    artifact, info = value_model.train_and_evaluate(frame)
    path = registry.save(value_model.MODEL_KEY, artifact, models_dir)
    m = info["metrics"]
    return models_repo.save_run(session, ModelRun(
        model_key=value_model.MODEL_KEY, name="Estimador de valor de mercado (Gradient Boosting)",
        objective="Valor de mercado registrado al final de la temporada, a partir de perfil y rendimiento.",
        trained_at=_now(), n_train=info["n_train"], n_test=info["n_test"], features=value_model.FEATURES,
        metrics=m,
        validation=(f"Temporal: entrenamiento con temporadas {m['split']['train_seasons'][0]}–"
                    f"{m['split']['train_seasons'][1]}, evaluación con {m['split']['test_season']}. "
                    "Se entrena sobre log(valor). Comparado con la mediana por liga, posición y edad."),
        limitations=[
            "No usa historial de valores a propósito; repetir el valor previo acierta más (ver referencia).",
            "Las estadísticas disponibles son goles, asistencias, minutos, tarjetas y contexto de equipo: "
            "no hay pases, remates ni acciones defensivas individuales.",
            "Los valores de Transfermarkt son estimaciones de una comunidad, no precios de transferencia.",
            "El error relativo es alto en jugadores jóvenes y de valores extremos.",
        ],
        artifact_path=str(path),
    ))


def evaluate_similarity(session: Session, frame: pd.DataFrame) -> ModelRun | None:
    seasons = sorted(frame["season"].unique())
    if len(seasons) < 2:
        return None
    prev = frame[frame["season"] == seasons[-2]].set_index("player_id")
    curr = frame[frame["season"] == seasons[-1]].set_index("player_id")
    res = similarity_eval.evaluate(prev, curr)
    return models_repo.save_run(session, ModelRun(
        model_key="similarity", name="Jugadores similares (similitud coseno)",
        objective="Recomendar perfiles estadísticos parecidos dentro de la misma posición.",
        trained_at=_now(), n_train=0, n_test=res.get("queries", 0),
        features=POSITION_FEATURES,
        metrics=res,
        validation=(f"Auto-recuperación entre temporadas: perfil {seasons[-2]} buscado entre los perfiles de "
                    f"{seasons[-1]} de la misma posición (900+ minutos en ambas). Se compara con el azar."),
        limitations=[
            "No hay un conjunto de 'similares verdaderos': la métrica mide estabilidad del perfil, no utilidad.",
            "Pocas variables disponibles: perfiles distintos en el campo pueden verse parecidos en los números.",
            "Variables de contexto de equipo (vallas invictas, goles recibidos) pesan en defensores y arqueros.",
        ],
        artifact_path=None,
    ))


def train_all(session: Session, models_dir: Path | None = None) -> list[ModelRun]:
    runs = [train_match_model(session, models_dir)]
    log.info("Predictor de partidos entrenado")
    frame = all_seasons_frame(session)
    runs.append(train_value_model(session, frame, models_dir))
    log.info("Estimador de valor entrenado")
    sim = evaluate_similarity(session, frame)
    if sim:
        runs.append(sim)
    return runs
