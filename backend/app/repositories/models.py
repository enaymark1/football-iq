"""Corridas de modelos guardadas por scripts/train_models.py."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import ModelRun


def save_run(session: Session, run: ModelRun) -> ModelRun:
    session.add(run)
    session.commit()
    return run


def latest_runs(session: Session) -> list[ModelRun]:
    latest_ids = select(func.max(ModelRun.id)).group_by(ModelRun.model_key)
    return list(session.scalars(select(ModelRun).where(ModelRun.id.in_(latest_ids)).order_by(ModelRun.model_key)))


def latest_run(session: Session, model_key: str) -> ModelRun | None:
    return session.scalar(select(ModelRun).where(ModelRun.model_key == model_key)
                          .order_by(ModelRun.id.desc()).limit(1))
