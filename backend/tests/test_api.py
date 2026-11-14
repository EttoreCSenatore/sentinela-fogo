from datetime import datetime, timedelta, timezone

from app.db import Hotspot, SessionLocal
from app.ingest.mqtt import handle_payload

NODE = {"node_id": "cerrado-001", "lat": -15.79, "lon": -47.88}


def reading(**kw):
    return {**NODE, "temp_c": 28.0, "humidity_pct": 40.0, "smoke_ppm": 50.0, **kw}


def test_health(client):
    assert client.get("/api/health").json() == {"status": "ok"}


def test_calm_readings_no_alert(client):
    for _ in range(5):
        r = client.post("/api/readings", json=reading())
        assert r.status_code == 201 and r.json()["alert_id"] is None
    nodes = client.get("/api/nodes").json()
    assert [n["id"] for n in nodes] == ["cerrado-001"]
    assert nodes[0]["last_seen"].endswith("Z") or "+00:00" in nodes[0]["last_seen"]
    assert len(client.get("/api/nodes/cerrado-001/readings").json()) == 5


def test_fire_opens_single_alert_with_cooldown(client):
    for _ in range(4):
        client.post("/api/readings", json=reading())
    r = client.post("/api/readings", json=reading(temp_c=40, humidity_pct=20, smoke_ppm=500))
    assert r.json()["alert_id"] is not None and r.json()["score"] >= 0.6
    r2 = client.post("/api/readings", json=reading(temp_c=45, humidity_pct=15, smoke_ppm=900, flame=True))
    assert r2.json()["alert_id"] is None  # cooldown
    alerts = client.get("/api/alerts").json()
    assert len(alerts) == 1 and "cerrado-001" in alerts[0]["message"]


def test_hotspot_nearby_raises_score(client):
    with SessionLocal() as db:
        db.add(Hotspot(lat=-15.80, lon=-47.89, satellite="GOES-19", ts=datetime.now(timezone.utc)))
        db.commit()
    r = client.post("/api/readings", json=reading())
    assert r.json()["score"] == 0.3
    assert len(client.get("/api/hotspots").json()) == 1


def test_validation_rejects_bad_node_id(client):
    assert client.post("/api/readings", json=reading(node_id="../x")).status_code == 422
    assert client.post("/api/readings", json=reading(humidity_pct=150)).status_code == 422


def test_danger_endpoint(client):
    now = datetime.now(timezone.utc)
    for d in range(3, 0, -1):
        ts = (now - timedelta(days=d)).replace(hour=16, minute=0)  # 13h in Brasília
        client.post("/api/readings", json=reading(humidity_pct=20, ts=ts.isoformat()))
    body = client.get("/api/nodes/cerrado-001/danger").json()
    assert body["days_used"] == 3
    assert body["fma_plus"] == 15.0 and body["danger_class"] == "alta"
    assert client.get("/api/nodes/nope/danger").status_code == 404


async def test_mqtt_topic_overrides_node_id(client):
    await handle_payload(b'{"node_id":"spoof","lat":-10,"lon":-50,"temp_c":30,"humidity_pct":30}',
                         "sentinela/v1/nodes/pantanal-007/telemetry")
    await handle_payload(b"not json", "sentinela/v1/nodes/pantanal-007/telemetry")
    ids = [n["id"] for n in client.get("/api/nodes").json()]
    assert ids == ["pantanal-007"]


def test_overview_has_latest_reading_and_danger(client):
    client.post("/api/readings", json=reading(temp_c=30.5))
    [n] = client.get("/api/overview").json()
    assert n["id"] == "cerrado-001" and n["kind"] == "sensor"
    assert n["last"]["temp_c"] == 30.5
    assert n["danger"]["days_used"] == 1


async def test_bus_receives_reading_and_alert_events(client):
    from app.events import bus
    q = bus.subscribe()
    try:
        for _ in range(4):
            client.post("/api/readings", json=reading())
        client.post("/api/readings", json=reading(temp_c=40, humidity_pct=20, smoke_ppm=500, flame=True))
        events = [q.get_nowait().split("\n")[0] for _ in range(q.qsize())]
    finally:
        bus.unsubscribe(q)
    assert events.count("event: reading") == 5
    assert events.count("event: alert") == 1


async def test_event_stream_heartbeat_and_cleanup(monkeypatch):
    from app import main
    from app.events import bus
    monkeypatch.setattr(main, "HEARTBEAT_SECONDS", 0.01)

    class FakeRequest:
        calls = 0
        async def is_disconnected(self):
            FakeRequest.calls += 1
            return FakeRequest.calls > 2

    q = bus.subscribe()
    q.put_nowait("event: alert\ndata: {}\n\n")
    chunks = [c async for c in main.event_stream(FakeRequest(), q)]
    assert chunks[0].startswith("retry:") and chunks[1].startswith("event: alert") and chunks[2] == ": ping\n\n"
    assert q not in bus._subs
