"""Security regressions: authenticated HTTP ingest, no token in logs, bounded SSE subscribers."""

import logging

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from app.alerts import telegram_bot as bot
from app.config import settings
from app.events import MAX_SUBSCRIBERS, bus
from app.main import app

READING = {"node_id": "cerrado-001", "lat": -15.79, "lon": -47.88, "temp_c": 28.0, "humidity_pct": 40.0}


@pytest.fixture
def anon():
    """A client without the ingest header the shared `client` fixture sends."""
    with TestClient(app) as c:
        yield c


def test_ingest_requires_the_token(anon):
    assert anon.post("/api/readings", json=READING).status_code == 401
    assert anon.post("/api/readings", json=READING, headers={"X-Ingest-Token": "wrong"}).status_code == 401
    assert anon.get("/api/nodes").json() == []  # nothing was stored by the rejected requests
    ok = anon.post("/api/readings", json=READING, headers={"X-Ingest-Token": settings.ingest_token})
    assert ok.status_code == 201


def test_ingest_disabled_when_no_token_configured(anon, monkeypatch):
    monkeypatch.setattr(settings, "ingest_token", None)
    r = anon.post("/api/readings", json=READING, headers={"X-Ingest-Token": "anything"})
    assert r.status_code == 503 and "disabled" in r.json()["detail"]


def test_read_endpoints_stay_public(anon):
    for path in ("/api/health", "/api/nodes", "/api/overview", "/api/hotspots", "/api/alerts"):
        assert anon.get(path).status_code == 200, path


@respx.mock
async def test_bot_token_never_reaches_the_logs(monkeypatch, caplog):
    secret = "123456:SECRET-TOKEN-VALUE"
    monkeypatch.setattr(settings, "telegram_bot_token", secret)
    base = f"https://api.telegram.org/bot{secret}"
    respx.post(f"{base}/sendMessage").mock(return_value=httpx.Response(400, json={"ok": False}))
    update = {"update_id": 7, "message": {"chat": {"id": 1}, "text": "/ajuda"}}
    with caplog.at_level(logging.DEBUG):
        async with httpx.AsyncClient() as c:
            await bot.safe_process_update(c, base, update)
    assert secret not in caplog.text
    assert "SECRET-TOKEN" not in caplog.text
    assert "400" in caplog.text  # still tells the operator what went wrong


def test_sse_subscribers_are_capped():
    queues = []
    try:
        while len(queues) < MAX_SUBSCRIBERS:
            queues.append(bus.subscribe())
        with pytest.raises(RuntimeError):
            bus.subscribe()
    finally:
        for q in queues:
            bus.unsubscribe(q)


def test_stream_returns_503_when_full(anon, monkeypatch):
    monkeypatch.setattr("app.events.MAX_SUBSCRIBERS", 0)
    assert anon.get("/api/stream").status_code == 503
