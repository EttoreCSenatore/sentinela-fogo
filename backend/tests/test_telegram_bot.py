import json
from datetime import datetime, timedelta, timezone

import httpx
import pytest
import respx

from app.alerts import telegram_bot as bot
from app.config import settings
from app.db import Reading, SessionLocal
from app.sites import sync_sites

BASE = "https://api.telegram.org/botT"


@pytest.fixture
def recipients(tmp_path, monkeypatch):
    f = tmp_path / "r.json"
    f.write_text(json.dumps({"recipients": [{"name": "Ana", "channels": {"telegram": "111"}}]}))
    monkeypatch.setattr(settings, "recipients_file", str(f))


def test_start_tells_chat_id_and_registration(recipients):
    assert "Chat ID: 111" in bot.handle_text(111, "/start")
    assert "já recebe" in bot.handle_text(111, "/start")
    unknown = bot.handle_text(222, "/start")
    assert "ainda não recebe" in unknown and 'add-telegram "<nome>" 222' in unknown


def test_commands_with_bot_suffix_and_unknown_text(recipients):
    assert "Comandos do Sentinela" in bot.handle_text(1, "/ajuda@SentinelaFogoBot")
    assert "Comandos do Sentinela" in bot.handle_text(1, "/HELP")
    assert bot.handle_text(1, "bom dia pessoal") is None  # stays quiet in groups
    assert bot.handle_text(1, "/naoexiste") is None


def test_status_lists_sites_with_inpe_and_fma():
    from datetime import date
    from app.db import SiteRisk
    from app.sites import site_timezone
    from zoneinfo import ZoneInfo
    with SessionLocal() as db:
        sync_sites(db, [
            {"id": "a", "name": "Área Seca", "lat": -14, "lon": -47},
            {"id": "b", "name": "Área Nova", "lat": -15, "lon": -48},
        ])
        now = datetime.now(timezone.utc)
        for d in range(3, 0, -1):  # 3 dry days at 13h Brasília -> FMA+ 15 (alta)
            ts = (now - timedelta(days=d)).replace(hour=16, minute=0)
            db.add(Reading(node_id="a", ts=ts, temp_c=33, humidity_pct=20, flame=False, score=0))
        today = datetime.now(ZoneInfo(site_timezone("a"))).date()
        db.add_all([
            SiteRisk(node_id="a", kind="forecast", valid_date=today, issued_date=today, rf_mean=0.82, rf_max=1.0),
            SiteRisk(node_id="a", kind="forecast", valid_date=today + timedelta(days=1), issued_date=today,
                     rf_mean=0.97, rf_max=1.0),
        ])
        db.commit()
    text = bot.reply_status()
    assert "📍 Área Seca" in text
    assert "INPE hoje: 🟠 Alto (0.82)" in text
    assert "🔴 Crítico" in text  # tomorrow's forecast
    assert "FMA+: 🟠 Alta (15.0)" in text
    assert "📍 Área Nova\n   INPE: sem dados ainda" in text


def test_status_without_sites():
    assert "Nenhuma área" in bot.reply_status()


@respx.mock
async def test_process_update_replies_in_same_chat(recipients):
    send = respx.post(f"{BASE}/sendMessage").mock(return_value=httpx.Response(200, json={"ok": True}))
    async with httpx.AsyncClient() as c:
        await bot.process_update(c, BASE, {"update_id": 1, "message": {"chat": {"id": 111}, "text": "/start"}})
        await bot.process_update(c, BASE, {"update_id": 2, "message": {"chat": {"id": 111}, "text": "oi"}})
        await bot.process_update(c, BASE, {"update_id": 3, "message": {"chat": {"id": 111}, "sticker": {}}})
    assert send.call_count == 1
    assert json.loads(send.calls[0].request.content)["chat_id"] == 111


async def test_poll_forever_is_noop_without_token(monkeypatch):
    monkeypatch.setattr(settings, "telegram_bot_token", None)
    await bot.poll_forever()  # returns immediately instead of looping
