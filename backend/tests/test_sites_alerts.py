import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest
import respx

from app import service
from app.alerts import dispatch
from app.config import settings
from app.db import Alert, Hotspot, Node, Reading, SessionLocal
from app.ingest import weather
from app.sites import sync_sites

SITE = {"id": "chapada", "name": "Chapada", "biome": "cerrado", "lat": -14.07, "lon": -47.68, "radius_km": 20}
NOW = datetime(2026, 11, 14, 18, 0, tzinfo=timezone.utc)


def open_meteo(days: int, rh: float = 20, rain: float = 0.0):
    start = NOW.replace(hour=0) - timedelta(days=days - 1)
    times = [start + timedelta(hours=i) for i in range(days * 24 + 24)]  # includes forecast hours
    n = len(times)
    return {"hourly": {
        "time": [t.strftime("%Y-%m-%dT%H:%M") for t in times],
        "temperature_2m": [32.0] * n, "relative_humidity_2m": [rh] * n,
        "wind_speed_10m": [0.0] * n, "precipitation": [rain] * n,
    }}


def test_sync_sites_is_idempotent():
    with SessionLocal() as db:
        sync_sites(db, [SITE])
        sync_sites(db, [{**SITE, "name": "Renamed"}])
        nodes = db.query(Node).all()
    assert len(nodes) == 1 and nodes[0].kind == "virtual" and nodes[0].name == "Renamed"


@respx.mock
async def test_weather_backfill_then_incremental_and_danger_alert():
    respx.get(settings.weather_base_url).mock(return_value=httpx.Response(200, json=open_meteo(5)))
    with SessionLocal() as db:
        sync_sites(db, [SITE])
    async with httpx.AsyncClient() as c:
        first = await weather.poll_once(c, now=NOW)
        second = await weather.poll_once(c, now=NOW)
    assert first == 4 * 24 + 19  # 4 full days + today's 00:00..18:00, no forecast hours
    assert second == 0
    with SessionLocal() as db:
        value, cls, n = service.node_danger(db, "chapada")
        alerts = db.query(Alert).all()
    assert n >= 5 and cls in ("alta", "muito_alta")
    assert [a.kind for a in alerts] == ["danger"]  # once per day, not per poll


async def test_hotspot_near_site_alerts_once_far_ignored():
    with SessionLocal() as db:
        sync_sites(db, [SITE])
        db.add_all([
            Hotspot(lat=-14.10, lon=-47.70, satellite="GOES-19", ts=NOW - timedelta(minutes=30)),  # ~4 km
            Hotspot(lat=-14.00, lon=-47.60, satellite="NOAA-21", ts=NOW - timedelta(minutes=20)),  # ~11 km
            Hotspot(lat=-15.00, lon=-47.68, satellite="GOES-19", ts=NOW),                          # ~100 km
            Hotspot(lat=-14.07, lon=-47.68, satellite="GOES-19", ts=NOW - timedelta(hours=10)),    # too old
        ])
        db.commit()
        first = await service.check_hotspots_near_nodes(db, NOW)
        again = await service.check_hotspots_near_nodes(db, NOW + timedelta(minutes=10))
    assert len(first) == 1 and "2 foco(s)" in first[0].message
    assert again == []  # cooldown


def test_recipient_routing(tmp_path, monkeypatch):
    f = tmp_path / "r.json"
    f.write_text(json.dumps({"recipients": [
        {"name": "all", "channels": {"telegram": "1"}},
        {"name": "brigada", "channels": {"sms": "+55"}, "sites": ["chapada"], "kinds": ["fire"]},
    ]}))
    monkeypatch.setattr(settings, "recipients_file", str(f))
    rs = dispatch.load_recipients()
    assert [r.name for r in rs if r.wants("chapada", "fire")] == ["all", "brigada"]
    assert [r.name for r in rs if r.wants("chapada", "danger")] == ["all"]
    assert [r.name for r in rs if r.wants("pantanal", "fire")] == ["all"]


@respx.mock
async def test_send_alert_fans_out_and_skips_unconfigured(tmp_path, monkeypatch):
    f = tmp_path / "r.json"
    f.write_text(json.dumps({"recipients": [
        {"name": "a", "channels": {"telegram": "42", "webhook": "https://hooks.example/x",
                                   "whatsapp": "+5561", "sms": "+5561"}},
    ]}))
    monkeypatch.setattr(settings, "recipients_file", str(f))
    monkeypatch.setattr(settings, "telegram_bot_token", "T")
    tg = respx.post("https://api.telegram.org/botT/sendMessage").mock(return_value=httpx.Response(200))
    hook = respx.post("https://hooks.example/x").mock(return_value=httpx.Response(500))
    assert await dispatch.send_alert("chapada", "fire", "fogo!") is True
    assert json.loads(tg.calls[0].request.content) == {"chat_id": "42", "text": "fogo!"}
    assert hook.called  # failed, but did not break the other channels


@respx.mock
async def test_whatsapp_and_sms_payloads(monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_token", "W")
    monkeypatch.setattr(settings, "whatsapp_phone_number_id", "999")
    monkeypatch.setattr(settings, "twilio_account_sid", "AC1")
    monkeypatch.setattr(settings, "twilio_auth_token", "tok")
    monkeypatch.setattr(settings, "twilio_from", "+1555")
    wa = respx.post("https://graph.facebook.com/v21.0/999/messages").mock(return_value=httpx.Response(200))
    sms = respx.post("https://api.twilio.com/2010-04-01/Accounts/AC1/Messages.json").mock(
        return_value=httpx.Response(201))
    async with httpx.AsyncClient() as c:
        assert await dispatch._whatsapp(c, "+5561999", {"message": "m"})
        assert await dispatch._sms(c, "+5561999", {"message": "m"})
    body = json.loads(wa.calls[0].request.content)
    assert body["to"] == "5561999" and body["text"]["body"] == "m"
    assert wa.calls[0].request.headers["authorization"] == "Bearer W"
    assert b"To=%2B5561999" in sms.calls[0].request.content


@pytest.mark.parametrize("hours_of_data", [0])
def test_no_recipients_logs_only(hours_of_data):
    assert dispatch.load_recipients() == []
