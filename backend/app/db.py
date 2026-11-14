from datetime import date, datetime

from sqlalchemy import (
    Boolean, Date, DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, create_engine, event,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


class Node(Base):
    __tablename__ = "nodes"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str | None] = mapped_column(String(128))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    biome: Mapped[str | None] = mapped_column(String(32))
    kind: Mapped[str] = mapped_column(String(16), default="sensor")  # sensor | virtual
    radius_km: Mapped[float | None] = mapped_column(Float)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    battery_v: Mapped[float | None] = mapped_column(Float)


class Reading(Base):
    __tablename__ = "readings"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    node_id: Mapped[str] = mapped_column(ForeignKey("nodes.id"), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    temp_c: Mapped[float] = mapped_column(Float)
    humidity_pct: Mapped[float] = mapped_column(Float)
    smoke_ppm: Mapped[float | None] = mapped_column(Float)
    flame: Mapped[bool] = mapped_column(Boolean, default=False)
    wind_ms: Mapped[float | None] = mapped_column(Float)
    rain_mm: Mapped[float | None] = mapped_column(Float)
    score: Mapped[float] = mapped_column(Float, default=0.0)


class Hotspot(Base):
    __tablename__ = "hotspots"
    __table_args__ = (UniqueConstraint("lat", "lon", "satellite", "ts"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lat: Mapped[float] = mapped_column(Float, index=True)
    lon: Mapped[float] = mapped_column(Float, index=True)
    satellite: Mapped[str] = mapped_column(String(32))
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class SiteRisk(Base):
    """INPE Risco de Fogo sampled over a site: observed (yesterday and before) or forecast (today + 3 days)."""
    __tablename__ = "site_risk"
    __table_args__ = (UniqueConstraint("node_id", "kind", "valid_date"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    node_id: Mapped[str] = mapped_column(ForeignKey("nodes.id"), index=True)
    kind: Mapped[str] = mapped_column(String(16))  # observed | forecast
    valid_date: Mapped[date] = mapped_column(Date, index=True)
    issued_date: Mapped[date | None] = mapped_column(Date)
    rf_mean: Mapped[float] = mapped_column(Float)
    rf_max: Mapped[float] = mapped_column(Float)
    fetched_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    node_id: Mapped[str] = mapped_column(ForeignKey("nodes.id"), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    score: Mapped[float] = mapped_column(Float)
    message: Mapped[str] = mapped_column(String(1024))
    delivered: Mapped[bool] = mapped_column(Boolean, default=False)


def make_engine(url: str):
    kwargs = {"connect_args": {"check_same_thread": False}} if url.startswith("sqlite") else {}
    engine = create_engine(url, **kwargs)
    if url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _pragma(conn, _):
            # journal_mode=WAL is persistent, so it is set once in init_db (setting it on every
            # connect can fail with "database is locked" while another connection is writing).
            conn.execute("PRAGMA busy_timeout=5000")
            conn.execute("PRAGMA foreign_keys=ON")
    return engine


engine = make_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def upsert_ignore(db, model, rows: list[dict]):
    """INSERT ... ON CONFLICT DO NOTHING for SQLite and Postgres."""
    if db.get_bind().dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert
    else:
        from sqlalchemy.dialects.sqlite import insert
    return insert(model).values(rows).on_conflict_do_nothing()


def init_db(eng=None) -> None:
    eng = eng or engine
    if eng.url.get_backend_name() == "sqlite":
        with eng.connect() as conn:
            conn.exec_driver_sql("PRAGMA journal_mode=WAL")
    Base.metadata.create_all(eng)
