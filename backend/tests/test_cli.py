import json

import httpx
import pytest
import respx

from app import cli
from app.config import settings

TG = "https://api.telegram.org/botT"


@pytest.fixture
def recipients(tmp_path, monkeypatch):
    f = tmp_path / "recipients.json"
    monkeypatch.setattr(settings, "recipients_file", str(f))
    return f


@pytest.fixture
def token(monkeypatch):
    monkeypatch.setattr(settings, "telegram_bot_token", "T")


@respx.mock
async def test_telegram_check_lists_private_and_group_chats(token, capsys):
    respx.get(f"{TG}/getMe").mock(return_value=httpx.Response(200, json={
        "ok": True, "result": {"username": "sentinela_bot", "first_name": "Sentinela"}}))
    respx.get(f"{TG}/getUpdates").mock(return_value=httpx.Response(200, json={"ok": True, "result": [
        {"message": {"chat": {"id": 111, "type": "private", "first_name": "Ana", "username": "ana"}}},
        {"my_chat_member": {"chat": {"id": -100222, "type": "supergroup", "title": "Brigada Chapada"}}},
        {"message": {"chat": {"id": 111, "type": "private", "first_name": "Ana", "username": "ana"}}},
    ]}))
    assert await cli.telegram_check() == 0
    out = capsys.readouterr().out
    assert "@sentinela_bot" in out
    assert "111" in out and "Ana (@ana)" in out
    assert "-100222" in out and "Brigada Chapada" in out


@respx.mock
async def test_telegram_check_bad_token(token, capsys):
    respx.get(f"{TG}/getMe").mock(return_value=httpx.Response(401, json={"ok": False, "description": "Unauthorized"}))
    assert await cli.telegram_check() == 1
    assert "Unauthorized" in capsys.readouterr().out


async def test_telegram_check_without_token(monkeypatch, capsys):
    monkeypatch.setattr(settings, "telegram_bot_token", None)
    assert await cli.telegram_check() == 1
    assert "infra/.env" in capsys.readouterr().out


def test_add_telegram_creates_then_updates(recipients):
    assert cli.add_telegram("Ana", "111", ["*"], ["fire"]) == 0
    assert cli.add_telegram("Brigada", "-100222", ["chapada-veadeiros"], ["fire", "hotspot"]) == 0
    assert cli.add_telegram("Ana Souza", "111", ["*"], ["fire", "danger"]) == 0  # same chat -> update
    data = json.loads(recipients.read_text())["recipients"]
    assert [(r["name"], r["channels"]["telegram"], r["kinds"]) for r in data] == [
        ("Ana Souza", "111", ["fire", "danger"]),
        ("Brigada", "-100222", ["fire", "hotspot"]),
    ]


def test_add_telegram_validates(recipients):
    assert cli.add_telegram("x", "@ana", ["*"], ["fire"]) == 1
    assert cli.add_telegram("x", "111", ["*"], ["smoke"]) == 1
    assert not recipients.exists()


@respx.mock
async def test_test_alert_reports_each_delivery(recipients, token, capsys):
    cli.add_telegram("Ana", "111", ["*"], ["fire"])
    cli.add_telegram("Errado", "999", ["*"], ["fire"])

    def reply(request):
        chat = json.loads(request.content)["chat_id"]
        if chat == "999":
            return httpx.Response(400, json={"ok": False, "description": "Bad Request: chat not found"})
        return httpx.Response(200, json={"ok": True})

    respx.post(f"{TG}/sendMessage").mock(side_effect=reply)
    assert await cli.test_alert("teste", "fire") == 1
    out = capsys.readouterr().out
    assert "OK    Ana" in out
    assert "FAIL  Errado" in out and "chat not found" in out


async def test_test_alert_without_recipients(recipients, capsys):
    assert await cli.test_alert("teste", "fire") == 1
    assert "No recipient" in capsys.readouterr().out


def test_infra_env_fills_only_missing_vars(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text("# comment\nSENTINELA_TELEGRAM_BOT_TOKEN='abc'\nSENTINELA_X=\nOTHER=1\nSENTINELA_MQTT_HOST=h\n")
    monkeypatch.setattr(cli, "INFRA_ENV", env)
    monkeypatch.delenv("SENTINELA_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.setenv("SENTINELA_MQTT_HOST", "keep")
    monkeypatch.delenv("OTHER", raising=False)
    cli._load_infra_env()
    import os
    assert os.environ["SENTINELA_TELEGRAM_BOT_TOKEN"] == "abc"
    assert os.environ["SENTINELA_MQTT_HOST"] == "keep"
    assert "OTHER" not in os.environ and "SENTINELA_X" not in os.environ
    monkeypatch.delenv("SENTINELA_TELEGRAM_BOT_TOKEN")
