"""Explorador, perfil y comparador de jugadores."""
from __future__ import annotations

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from app.core.errors import DomainError, InvalidRequestError, NotFoundError
from app.ml import registry, value_model
from app.repositories import meta as meta_repo
from app.repositories import players as repo
from app.services import similarity
from app.services.common import num
from app.services.metrics import METRICS, MIN_REFERENCE_MINUTES, POSITION_FEATURES, RATING_WEIGHTS, percentile_against

STAT_FIELDS = ["season", "team_id", "league_id", "teams_count", "age", "matches", "minutes", "goals", "assists",
               "yellow_cards", "red_cards", "goals_p90", "assists_p90", "goal_contrib_p90", "cards_p90",
               "minutes_share", "goal_involvement_share", "team_ppm", "team_ga_pm", "clean_sheet_rate",
               "market_value_start_eur", "market_value_end_eur", "rating", "rating_reliability"]
COMPARE_METRICS = ["age", "matches", "minutes", "goals", "assists", "goals_p90", "assists_p90", "goal_contrib_p90",
                   "cards_p90", "goal_involvement_share", "minutes_share", "team_ppm", "team_ga_pm",
                   "clean_sheet_rate", "market_value_eur"]
UNAVAILABLE_METRICS = {
    "shots": "Remates", "passes": "Pases", "progressive_passes": "Pases progresivos",
    "defensive_actions": "Acciones defensivas", "dribbles": "Regates", "chances_created": "Ocasiones creadas",
}
UNAVAILABLE_REASON = ("La fuente (transfermarkt-datasets) registra goles, asistencias, minutos y tarjetas por "
                      "partido; no tiene eventos de remates, pases ni acciones defensivas.")


def _player_dict(p, team_name=None, league_name=None, team_image_url=None) -> dict:
    return {
        "id": p.id, "name": p.name, "date_of_birth": p.date_of_birth, "nationality": p.nationality,
        "country_of_birth": p.country_of_birth, "position": p.position, "sub_position": p.sub_position,
        "foot": p.foot, "height_cm": p.height_cm, "current_team_id": p.current_team_id,
        "current_team_name": team_name, "current_league_name": league_name,
        "market_value_eur": p.market_value_eur, "market_value_date": p.market_value_date,
        "highest_market_value_eur": p.highest_market_value_eur, "profile_url": p.profile_url,
        "image_url": p.image_url, "current_team_image_url": team_image_url,
    }


def row_to_list_item(row) -> dict:
    s, p = row[0], row[1]
    return {
        "player_id": p.id, "name": p.name, "age": s.age, "nationality": p.nationality, "position": p.position,
        "sub_position": p.sub_position, "team_id": s.team_id, "team_name": row.team_name,
        "league_id": s.league_id, "league_name": row.league_name, "season": s.season, "matches": s.matches,
        "minutes": s.minutes, "goals": s.goals, "assists": s.assists, "goals_p90": s.goals_p90,
        "assists_p90": s.assists_p90, "market_value_eur": p.market_value_eur, "rating": s.rating,
        "rating_reliability": s.rating_reliability, "image_url": p.image_url, "team_image_url": row.team_image_url,
    }


def list_players(session: Session, filters: repo.PlayerFilters, sort_by: str, sort_dir: str, page: int,
                 page_size: int) -> dict:
    if sort_by not in repo.SORTABLE:
        raise InvalidRequestError(f"sort_by debe ser uno de {sorted(repo.SORTABLE)}")
    if filters.age_min is not None and filters.age_max is not None and filters.age_min > filters.age_max:
        raise InvalidRequestError("La edad mínima no puede ser mayor que la máxima.")
    if filters.value_min is not None and filters.value_max is not None and filters.value_min > filters.value_max:
        raise InvalidRequestError("El valor mínimo no puede ser mayor que el máximo.")
    rows, total = repo.list_player_seasons(session, filters, sort_by, sort_dir, page, page_size)
    return {"items": [row_to_list_item(r) for r in rows], "total": total, "page": page, "page_size": page_size,
            "pages": max(1, -(-total // page_size)), "season": filters.season}


def _percentiles(row: pd.Series, frame: pd.DataFrame, metrics: list[str]) -> tuple[dict, pd.DataFrame]:
    ref = frame[(frame["position"] == row["position"]) & (frame["minutes"] >= MIN_REFERENCE_MINUTES)]
    out = {}
    for k in metrics:
        if pd.isna(row[k]) or ref.empty:
            out[k] = None
            continue
        pct = percentile_against(pd.Series([row[k]]), ref[k], METRICS[k].higher_is_better).iloc[0]
        out[k] = num(round(pct, 1))
    return out, ref


def profile(session: Session, player_id: int, season: int | None) -> dict:
    found = repo.get_player(session, player_id)
    if not found:
        raise NotFoundError(f"No existe el jugador {player_id}.")
    p, team_name, league_name, team_image_url = found
    seasons_rows = repo.player_seasons(session, player_id)
    seasons = []
    for r in seasons_rows:
        s = r[0]
        d = {f: getattr(s, f) for f in STAT_FIELDS}
        d.update(team_name=r.team_name, league_name=r.league_name, team_image_url=r.team_image_url)
        seasons.append(d)
    labels = meta_repo.season_labels(session)
    for d in seasons:
        d["season_label"] = labels.get(d["season"], str(d["season"]))
    available = [d["season"] for d in seasons]
    if season is None:
        season = available[-1] if available else None
    elif season not in available:
        raise NotFoundError(f"El jugador no tiene estadísticas en la temporada {season}.",
                            details={"available_seasons": available})

    result = {"player": _player_dict(p, team_name, league_name, team_image_url), "seasons": seasons, "selected_season": season,
              "valuations": [{"date": d, "value_eur": v} for d, v in repo.valuations(session, player_id)],
              "unavailable_metrics": list(UNAVAILABLE_METRICS.values()), "unavailable_reason": UNAVAILABLE_REASON}
    if season is None:
        result.update(position_comparison=None, strengths=[], weaknesses=[], similar=None,
                      data_quality=_data_quality(p, None, result["valuations"]))
        return result

    frame = repo.season_frame(session, season)
    row = frame.loc[player_id]
    pos = row["position"]
    metrics = [m for m in POSITION_FEATURES.get(pos, []) if m != "age"] or ["goals_p90", "assists_p90", "minutes_share"]
    for m in RATING_WEIGHTS.get(pos, {}):
        if m not in metrics:
            metrics.append(m)
    pcts, ref = _percentiles(row, frame, metrics)
    comparison = [{
        "metric": k, "label": METRICS[k].label, "value": num(row[k]), "percentile": pcts[k],
        "position_median": num(ref[k].median()) if not ref.empty else None,
        "position_p90": num(ref[k].quantile(0.9 if METRICS[k].higher_is_better else 0.1)) if not ref.empty else None,
        "higher_is_better": METRICS[k].higher_is_better, "scope": METRICS[k].scope,
    } for k in metrics]
    enough = row["minutes"] >= MIN_REFERENCE_MINUTES
    strengths = [c for c in comparison if enough and c["percentile"] is not None and c["percentile"] >= 75]
    weaknesses = [c for c in comparison if enough and c["percentile"] is not None and c["percentile"] <= 25]

    try:
        sim = similarity.find_similar(frame, player_id, k=5)
    except DomainError as exc:  # perfil sin datos suficientes: se informa en vez de fallar
        sim = {"results": [], "warnings": [exc.message]}

    estimate = None
    artifact = registry.try_load(value_model.MODEL_KEY)
    if artifact is not None:
        pred = value_model.predict_frame(artifact, frame.loc[[player_id]])[0]
        if not np.isnan(pred):
            band = artifact["error_band"]
            estimate = {"estimated_value_eur": float(pred),
                        "typical_range_eur": [float(pred / band["p90_ratio"]), float(pred / band["p10_ratio"])],
                        "out_of_sample": season > artifact["train_max_season"],
                        "notes": value_model.confidence_notes(artifact, row)}

    result.update(
        position_comparison={"position": pos, "reference_size": int(len(ref)), "metrics": comparison,
                             "sample_warning": None if enough else
                             f"Solo {int(row['minutes'])} minutos: no se marcan fortalezas ni debilidades."},
        strengths=strengths, weaknesses=weaknesses, similar=sim, value_estimate=estimate,
        data_quality=_data_quality(p, row, result["valuations"]),
    )
    return result


def _data_quality(p, row, valuations) -> dict:
    fields = {"Fecha de nacimiento": p.date_of_birth, "Nacionalidad": p.nationality, "Posición": p.position,
              "Altura": p.height_cm, "Pie hábil": p.foot, "Valor de mercado": p.market_value_eur}
    present = [k for k, v in fields.items() if v is not None]
    out = {"profile_fields_present": present, "profile_fields_missing": [k for k in fields if k not in present],
           "profile_completeness": round(len(present) / len(fields), 3), "valuation_points": len(valuations),
           "last_valuation_date": p.market_value_date}
    if row is not None:
        out.update(minutes=int(row["minutes"]), matches=int(row["matches"]),
                   rating_reliability=num(row["rating_reliability"]), teams_in_season=int(row["teams_count"]),
                   sample="suficiente" if row["minutes"] >= 1800 else "moderada" if row["minutes"] >= 900 else "chica")
    return out


def compare(session: Session, player_ids: list[int], season: int | None) -> dict:
    if not 2 <= len(player_ids) <= 4:
        raise InvalidRequestError("Elegí entre 2 y 4 jugadores.")
    if len(set(player_ids)) != len(player_ids):
        raise InvalidRequestError("Hay jugadores repetidos.")
    rows, notes = [], []
    for pid in player_ids:
        found = repo.get_player(session, pid)
        if not found:
            raise NotFoundError(f"No existe el jugador {pid}.")
        df = repo.players_frame(session, [pid], season)
        if df.empty:
            raise NotFoundError(f"{found[0].name} no tiene estadísticas" + (f" en {season}." if season else "."))
        rows.append(df.iloc[0])
    seasons = {int(r["season"]) for r in rows}
    if len(seasons) > 1:
        notes.append("Los jugadores se comparan en temporadas distintas (la última de cada uno).")
    positions = {r["position"] for r in rows}
    same_position = len(positions) == 1
    if not same_position:
        notes.append("Posiciones distintas: los percentiles del radar son relativos a la posición de cada "
                     "jugador y las métricas de contexto de equipo no son comparables entre sí.")

    players = []
    for r in rows:
        players.append({"player_id": int(r["player_id"]), "name": r["name"], "position": r["position"],
                        "sub_position": r["sub_position"], "team_name": r["team_name"],
                        "league_name": r["league_name"], "season": int(r["season"]), "rating": num(r["rating"]),
                        "image_url": r["image_url"]})

    metrics_out = []
    for k in COMPARE_METRICS:
        vals = [num(r[k]) for r in rows]
        if all(v is None for v in vals):
            continue
        ref = vals[0]
        diffs = []
        for v in vals:
            if v is None or ref is None:
                diffs.append(None)
            elif METRICS[k].unit == "ratio":  # en proporciones se informa la diferencia en puntos
                diffs.append({"type": "points", "value": round((v - ref) * 100, 1)})
            elif ref > 0:
                diffs.append({"type": "percent", "value": round((v - ref) / ref * 100, 1)})
            else:
                diffs.append(None)  # no hay % válido sobre una base 0
        metrics_out.append({"metric": k, "label": METRICS[k].label, "unit": METRICS[k].unit,
                            "higher_is_better": METRICS[k].higher_is_better, "scope": METRICS[k].scope,
                            "values": vals, "diff_vs_first": diffs})

    # Radar: percentil dentro de la posición de cada jugador, misma temporada de ese jugador.
    radar_pos = rows[0]["position"] if same_position else None
    radar_metrics = [m for m in POSITION_FEATURES.get(radar_pos, [])] if radar_pos else \
        ["goals_p90", "assists_p90", "goal_involvement_share", "minutes_share", "team_ppm", "cards_p90"]
    radar_metrics = [m for m in radar_metrics if m != "age"]
    radar = []
    for r in rows:
        frame = repo.season_frame(session, int(r["season"]))
        pcts, _ = _percentiles(r, frame, radar_metrics)
        radar.append(pcts)
    return {
        "players": players, "metrics": metrics_out,
        "radar": {"metrics": [{"key": m, "label": METRICS[m].label} for m in radar_metrics], "percentiles": radar,
                  "normalization": "Percentil (0-100) contra jugadores de la misma posición con "
                                   f"{MIN_REFERENCE_MINUTES}+ minutos en la misma temporada; en métricas donde menos "
                                   "es mejor, el percentil ya está invertido."},
        "unavailable_metrics": list(UNAVAILABLE_METRICS.values()), "unavailable_reason": UNAVAILABLE_REASON,
        "notes": notes, "same_position": same_position,
    }
