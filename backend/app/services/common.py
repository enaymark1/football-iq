"""Utilidades chicas compartidas por los servicios."""
import math

import pandas as pd


def num(v) -> float | None:
    """Convierte a float para JSON; NaN/None -> None (un faltante nunca se vuelve 0)."""
    if v is None:
        return None
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    f = float(v)
    return None if math.isnan(f) else f


def fmt_eur(v: float) -> str:
    text = f"{v / 1e6:.1f} M€" if v >= 1e6 else f"{v / 1e3:.0f} mil €"
    return text.replace(".", ",")
