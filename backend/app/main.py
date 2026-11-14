import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import service
from app.config import settings
from app.db import Alert, Hotspot, Node, Reading, SessionLocal, init_db
from app.sites import sync_sites
from app.events import bus
from app.schemas import AlertOut, DangerOut, HotspotOut, NodeOut, OverviewNode, ReadingOut, Telemetry

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)  # one line per INPE/Open-Meteo request is noise


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    with SessionLocal() as db:
        sync_sites(db)
    tasks = []
    if settings.mqtt_enabled:
        from app.ingest import mqtt
        tasks.append(asyncio.create_task(mqtt.run_forever()))
    if settings.inpe_enabled:
        from app.ingest import inpe
        tasks.append(asyncio.create_task(inpe.poll_forever()))
    if settings.weather_enabled:
        from app.ingest import weather
        tasks.append(asyncio.create_task(weather.poll_forever()))
    yield
    for t in tasks:
        t.cancel()


app = FastAPI(title="Sentinela do Fogo", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5174"], allow_methods=["*"], allow_headers=["*"])


def get_db():
    with SessionLocal() as db:
        yield db


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.post("/api/readings", status_code=201)
async def post_reading(t: Telemetry, db: Session = Depends(get_db)):
    """HTTP ingest. An alternative to MQTT for LoRaWAN network-server webhooks and 4G gateways."""
    reading, alert = await service.process(db, t)
    return {"score": reading.score, "alert_id": alert.id if alert else None}


@app.get("/api/overview", response_model=list[OverviewNode])
def overview(db: Session = Depends(get_db)):
    """Every node/site with its latest reading and FMA+ danger, in one call for the dashboard."""
    out = []
    for node in db.scalars(select(Node).order_by(Node.kind.desc(), Node.id)).all():
        last = db.scalars(
            select(Reading).where(Reading.node_id == node.id).order_by(Reading.ts.desc()).limit(1)
        ).first()
        item = OverviewNode.model_validate(node)
        if last is not None:
            item.last = ReadingOut.model_validate(last)
            value, cls, n = service.node_danger(db, node.id)
            item.danger = DangerOut(node_id=node.id, fma_plus=round(value, 2), danger_class=cls, days_used=n)
        out.append(item)
    return out


HEARTBEAT_SECONDS = 15


async def event_stream(request: Request, queue):
    try:
        yield "retry: 5000\n\n"
        while not await request.is_disconnected():
            try:
                yield await asyncio.wait_for(queue.get(), timeout=HEARTBEAT_SECONDS)
            except asyncio.TimeoutError:
                yield ": ping\n\n"
    finally:
        bus.unsubscribe(queue)


@app.get("/api/stream")
async def stream(request: Request):
    """Server-Sent Events: `alert`, `reading` and `refresh` events."""
    return StreamingResponse(
        event_stream(request, bus.subscribe()),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/nodes", response_model=list[NodeOut])
def list_nodes(db: Session = Depends(get_db)):
    return db.scalars(select(Node).order_by(Node.id)).all()


@app.get("/api/nodes/{node_id}/readings", response_model=list[ReadingOut])
def node_readings(node_id: str, limit: int = Query(100, le=2000), db: Session = Depends(get_db)):
    if db.get(Node, node_id) is None:
        raise HTTPException(404, "node not found")
    rows = db.scalars(
        select(Reading).where(Reading.node_id == node_id).order_by(Reading.ts.desc()).limit(limit)
    ).all()
    return list(reversed(rows))


@app.get("/api/nodes/{node_id}/danger", response_model=DangerOut)
def node_danger(node_id: str, db: Session = Depends(get_db)):
    if db.get(Node, node_id) is None:
        raise HTTPException(404, "node not found")
    value, cls, n = service.node_danger(db, node_id)
    return DangerOut(node_id=node_id, fma_plus=round(value, 2), danger_class=cls, days_used=n)


@app.get("/api/hotspots", response_model=list[HotspotOut])
def hotspots(hours: int = Query(24, ge=1, le=168), limit: int = Query(5000, le=20000), db: Session = Depends(get_db)):
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    return db.scalars(select(Hotspot).where(Hotspot.ts >= since).order_by(Hotspot.ts.desc()).limit(limit)).all()


@app.get("/api/alerts", response_model=list[AlertOut])
def alerts(limit: int = Query(50, le=500), db: Session = Depends(get_db)):
    return db.scalars(select(Alert).order_by(Alert.ts.desc()).limit(limit)).all()
