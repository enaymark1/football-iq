"""Escritura de las tablas normalizadas en la base (SQLite o cualquier motor de SQLAlchemy)."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import insert
from sqlalchemy.engine import Engine

from app.core.database import Base, init_db
from app.models import ImportReport

log = logging.getLogger(__name__)

# Orden de inserción respetando las claves foráneas.
TABLE_ORDER = ["leagues", "seasons", "teams", "players", "matches", "player_season_stats", "valuations"]


def _records(df: pd.DataFrame) -> list[dict]:
    clean = df.astype(object).where(pd.notna(df), None)
    recs = clean.to_dict("records")
    for r in recs:
        for k, v in r.items():
            if isinstance(v, np.generic):
                r[k] = v.item()
    return recs


def write_tables(engine: Engine, tables: dict[str, pd.DataFrame], report: dict, reports_dir: Path | None) -> dict:
    """Reemplaza todo el contenido de la base. Los modelos hay que re-entrenarlos después."""
    from app import models  # noqa: F401

    Base.metadata.drop_all(engine)
    init_db(engine)
    with engine.begin() as conn:
        for name in TABLE_ORDER:
            table = Base.metadata.tables[name]
            df = tables[name]
            recs = _records(df)
            for i in range(0, len(recs), 20_000):
                conn.execute(insert(table), recs[i:i + 20_000])
            log.info("%s: %d filas guardadas", name, len(df))
        created = datetime.now(timezone.utc).replace(tzinfo=None)
        report = {**report, "imported_at": created.isoformat(timespec="seconds")}
        conn.execute(insert(ImportReport.__table__), [{"created_at": created, "source": report["source"],
                                                       "report": report}])
    if reports_dir is not None:
        reports_dir.mkdir(parents=True, exist_ok=True)
        (reports_dir / "data_quality.json").write_text(json.dumps(report, indent=2, ensure_ascii=False),
                                                       encoding="utf-8")
    return report
