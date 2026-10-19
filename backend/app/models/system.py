"""Tablas de soporte: corridas de modelos e informes de importación."""
from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ModelRun(Base):
    __tablename__ = "model_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    model_key: Mapped[str] = mapped_column(String(60), index=True)
    name: Mapped[str] = mapped_column(String(120))
    objective: Mapped[str] = mapped_column(Text)
    trained_at: Mapped[datetime] = mapped_column(DateTime)
    n_train: Mapped[int] = mapped_column(Integer)
    n_test: Mapped[int] = mapped_column(Integer)
    features: Mapped[list] = mapped_column(JSON)
    metrics: Mapped[dict] = mapped_column(JSON)
    validation: Mapped[str] = mapped_column(Text)
    limitations: Mapped[list] = mapped_column(JSON)
    artifact_path: Mapped[str | None] = mapped_column(String(300))


class ImportReport(Base):
    __tablename__ = "import_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime)
    source: Mapped[str] = mapped_column(String(60))
    report: Mapped[dict] = mapped_column(JSON)
