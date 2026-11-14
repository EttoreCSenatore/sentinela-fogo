from datetime import datetime, timezone
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field


def _utc(v: datetime) -> datetime:
    # SQLite returns naive datetimes; everything is stored in UTC.
    return v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v


UTCDatetime = Annotated[datetime, AfterValidator(_utc)]


class Telemetry(BaseModel):
    """MQTT/HTTP payload sent by a sensor node (see docs/architecture.md)."""

    node_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_\-]+$")
    ts: datetime | None = None
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)
    temp_c: float = Field(ge=-20, le=90)
    humidity_pct: float = Field(ge=0, le=100)
    smoke_ppm: float | None = Field(default=None, ge=0)
    flame: bool = False
    wind_ms: float | None = Field(default=None, ge=0)
    rain_mm: float | None = Field(default=None, ge=0)
    battery_v: float | None = None


class NodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str | None
    lat: float
    lon: float
    biome: str | None
    kind: str
    radius_km: float | None
    last_seen: UTCDatetime | None
    battery_v: float | None


class ReadingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ts: UTCDatetime
    temp_c: float
    humidity_pct: float
    smoke_ppm: float | None
    flame: bool
    wind_ms: float | None
    rain_mm: float | None
    score: float


class HotspotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    lat: float
    lon: float
    satellite: str
    ts: UTCDatetime


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    node_id: str
    ts: UTCDatetime
    kind: str
    score: float
    message: str
    delivered: bool


class DangerOut(BaseModel):
    node_id: str
    fma_plus: float
    danger_class: str
    days_used: int


class OverviewNode(NodeOut):
    last: ReadingOut | None = None
    danger: DangerOut | None = None
