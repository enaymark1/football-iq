"""Entrena y evalúa los modelos con los datos importados.

Uso (desde la raíz del proyecto):
    python scripts/train_models.py
"""
import copy
import json
import logging
import sys

import _bootstrap  # noqa: F401

from app.core.database import SessionLocal
from app.ml.training import train_all

log = logging.getLogger("train_models")


def main() -> int:
    with SessionLocal() as session:
        runs = train_all(session)
    for run in runs:
        summary = {k: v for k, v in copy.deepcopy(run.metrics).items()
                   if k in ("poisson", "logistic", "baseline", "model", "baseline_group_median",
                            "reference_previous_value", "hit_at_10", "random_hit_at_10", "median_rank")}
        for v in summary.values():
            if isinstance(v, dict):
                v.pop("calibration", None)
                v.pop("confusion_matrix", None)
        log.info("%s | train=%d test=%d\n%s", run.name, run.n_train, run.n_test,
                 json.dumps(summary, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
