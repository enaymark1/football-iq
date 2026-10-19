"""Entidades deportivas.

Cada entidad importada guarda `source` + `source_id`: los identificadores de una
fuente no se asumen únicos entre fuentes, así que la clave interna es `id`.
"""
from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class League(Base):
    __tablename__ = "leagues"
    __table_args__ = (UniqueConstraint("source", "source_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(40))
    source_id: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(120))
    country: Mapped[str | None] = mapped_column(String(80))
    confederation: Mapped[str | None] = mapped_column(String(40))
    tier: Mapped[str | None] = mapped_column(String(40))
    image_url: Mapped[str | None] = mapped_column(String(300))


class Season(Base):
    __tablename__ = "seasons"

    year: Mapped[int] = mapped_column(primary_key=True)  # 2025 = temporada 2025/26
    label: Mapped[str] = mapped_column(String(20))


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = (UniqueConstraint("source", "source_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(40))
    source_id: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(120), index=True)
    league_id: Mapped[int | None] = mapped_column(ForeignKey("leagues.id"), index=True)
    stadium: Mapped[str | None] = mapped_column(String(120))
    stadium_seats: Mapped[int | None] = mapped_column(Integer)
    image_url: Mapped[str | None] = mapped_column(String(300))

    league: Mapped[League | None] = relationship()


class Player(Base):
    __tablename__ = "players"
    __table_args__ = (UniqueConstraint("source", "source_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(40))
    source_id: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(120), index=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    nationality: Mapped[str | None] = mapped_column(String(80), index=True)
    country_of_birth: Mapped[str | None] = mapped_column(String(80))
    position: Mapped[str | None] = mapped_column(String(20), index=True)  # Goalkeeper/Defender/Midfield/Attack
    sub_position: Mapped[str | None] = mapped_column(String(40))
    foot: Mapped[str | None] = mapped_column(String(10))
    height_cm: Mapped[float | None] = mapped_column(Float)
    current_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), index=True)
    market_value_eur: Mapped[float | None] = mapped_column(Float)
    market_value_date: Mapped[date | None] = mapped_column(Date)
    highest_market_value_eur: Mapped[float | None] = mapped_column(Float)
    profile_url: Mapped[str | None] = mapped_column(String(300))
    image_url: Mapped[str | None] = mapped_column(String(300))

    current_team: Mapped[Team | None] = relationship()


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (UniqueConstraint("source", "source_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(40))
    source_id: Mapped[str] = mapped_column(String(40))
    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id"), index=True)
    season: Mapped[int] = mapped_column(ForeignKey("seasons.year"), index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    round: Mapped[str | None] = mapped_column(String(60))
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), index=True)
    home_goals: Mapped[int] = mapped_column(Integer)
    away_goals: Mapped[int] = mapped_column(Integer)


class PlayerSeasonStats(Base):
    """Estadísticas de liga doméstica de un jugador en una temporada.

    Las métricas `team_*` describen al equipo en los partidos que jugó el
    jugador (no son estadísticas individuales en cancha).
    """

    __tablename__ = "player_season_stats"
    __table_args__ = (UniqueConstraint("player_id", "season"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), index=True)
    season: Mapped[int] = mapped_column(ForeignKey("seasons.year"), index=True)
    team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), index=True)
    league_id: Mapped[int | None] = mapped_column(ForeignKey("leagues.id"), index=True)
    teams_count: Mapped[int] = mapped_column(Integer, default=1)
    age: Mapped[float | None] = mapped_column(Float)
    matches: Mapped[int] = mapped_column(Integer)
    minutes: Mapped[int] = mapped_column(Integer, index=True)
    goals: Mapped[int] = mapped_column(Integer)
    assists: Mapped[int] = mapped_column(Integer)
    yellow_cards: Mapped[int] = mapped_column(Integer)
    red_cards: Mapped[int] = mapped_column(Integer)
    team_matches: Mapped[int | None] = mapped_column(Integer)
    team_goals_for: Mapped[int | None] = mapped_column(Integer)
    team_goals_against: Mapped[int | None] = mapped_column(Integer)
    team_points: Mapped[int | None] = mapped_column(Integer)
    clean_sheets: Mapped[int | None] = mapped_column(Integer)  # sobre partidos con 60+ minutos
    matches_60: Mapped[int | None] = mapped_column(Integer)
    # Derivadas (app.services.metrics.add_derived_metrics): una sola definición.
    goals_p90: Mapped[float | None] = mapped_column(Float)
    assists_p90: Mapped[float | None] = mapped_column(Float)
    goal_contrib_p90: Mapped[float | None] = mapped_column(Float)
    cards_p90: Mapped[float | None] = mapped_column(Float)
    minutes_share: Mapped[float | None] = mapped_column(Float)
    goal_involvement_share: Mapped[float | None] = mapped_column(Float)
    team_ppm: Mapped[float | None] = mapped_column(Float)
    team_ga_pm: Mapped[float | None] = mapped_column(Float)
    clean_sheet_rate: Mapped[float | None] = mapped_column(Float)
    # Valor registrado (Transfermarkt) al inicio y al final de la temporada.
    market_value_start_eur: Mapped[float | None] = mapped_column(Float)
    market_value_end_eur: Mapped[float | None] = mapped_column(Float)
    rating: Mapped[float | None] = mapped_column(Float, index=True)
    rating_reliability: Mapped[float | None] = mapped_column(Float)


class Valuation(Base):
    __tablename__ = "valuations"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), index=True)
    date: Mapped[date] = mapped_column(Date)
    value_eur: Mapped[float] = mapped_column(Float)
