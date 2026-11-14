"""Telegram bot commands: /start, /status, /ajuda.

Runs inside the backend via long polling (no public URL or webhook needed, so it works on a home server).
The bot never subscribes anyone by itself: /start only tells the user their chat ID, and an admin adds
them with `python -m app.cli add-telegram`.

Note: Telegram allows a single getUpdates consumer per bot. While this loop runs, use /start (which shows
the chat ID) instead of `app.cli telegram-check` to find chat IDs.
"""

import asyncio
import logging

import httpx
from sqlalchemy import select

from app import service
from app.alerts.dispatch import load_recipients
from app.config import settings
from app.db import Node, SessionLocal

log = logging.getLogger(__name__)

COMMANDS = [
    {"command": "status", "description": "Nível de perigo de incêndio nas áreas monitoradas"},
    {"command": "start", "description": "Mostra seu chat ID e se você recebe alertas"},
    {"command": "ajuda", "description": "Lista os comandos"},
]
DANGER_ICON = {"nula": "🟢", "pequena": "🟢", "media": "🟡", "alta": "🟠", "muito_alta": "🔴"}
DANGER_LABEL = {"nula": "Nula", "pequena": "Pequena", "media": "Média", "alta": "Alta", "muito_alta": "Muito alta"}


def _is_registered(chat_id: int) -> bool:
    return any(r.channels.get("telegram") == str(chat_id) for r in load_recipients())


def reply_start(chat_id: int) -> str:
    if _is_registered(chat_id):
        status = "✅ Este chat já recebe os alertas do Sentinela do Fogo."
    else:
        status = ("ℹ️ Este chat ainda não recebe alertas. Peça ao administrador para cadastrá-lo com:\n"
                  f"python -m app.cli add-telegram \"<nome>\" {chat_id}")
    return (f"🔥 Sentinela do Fogo\n\nChat ID: {chat_id}\n{status}\n\n"
            "Comandos: /status (perigo de incêndio nas áreas), /ajuda")


RF_ICON = {"minimo": "🟢", "baixo": "🟢", "medio": "🟡", "alto": "🟠", "critico": "🔴"}


def reply_status() -> str:
    with SessionLocal() as db:
        sites = db.scalars(select(Node).where(Node.kind == "virtual").order_by(Node.name)).all()
        if not sites:
            return "Nenhuma área monitorada configurada."
        lines = ["🔥 Risco de fogo por área\n"]
        for node in sites:
            lines.append(f"📍 {node.name or node.id}")
            risk = service.inpe_risk(db, node.id)
            if risk and risk["today"]:
                t = risk["today"]
                lines.append(f"   INPE hoje: {RF_ICON[t['risk_class']]} {t['label']} ({t['rf']:.2f})")
            if risk and risk["forecast"]:
                fc = "  ".join(f"{d['date']:%d/%m} {RF_ICON[d['risk_class']]} {d['label']}" for d in risk["forecast"])
                lines.append(f"   Previsão: {fc}")
            if not risk:
                lines.append("   INPE: sem dados ainda")
            value, cls, days = service.node_danger(db, node.id)
            if days:
                lines.append(f"   FMA+: {DANGER_ICON.get(cls, '⚪')} {DANGER_LABEL.get(cls, cls)} ({value:.1f})")
            lines.append("")
        lines.append("INPE = Risco de Fogo oficial (0 a 1). FMA+ = índice calculado com o clima da área.")
    return "\n".join(lines)


def reply_help() -> str:
    return ("Comandos do Sentinela do Fogo:\n"
            "/status: nível de perigo de incêndio em cada área monitorada\n"
            "/start: mostra o chat ID deste chat e se ele recebe alertas\n"
            "/ajuda: esta mensagem")


def handle_text(chat_id: int, text: str) -> str | None:
    """Return the reply for a message, or None to stay silent (e.g. ordinary chatter in a group)."""
    if not text.startswith("/"):
        return None
    cmd = text.split()[0][1:].split("@")[0].lower()  # "/status@SentinelaFogoBot" -> "status"
    if cmd == "start":
        return reply_start(chat_id)
    if cmd == "status":
        return reply_status()
    if cmd in ("ajuda", "help"):
        return reply_help()
    return None


async def process_update(client: httpx.AsyncClient, base: str, update: dict) -> None:
    msg = update.get("message") or {}
    text, chat = msg.get("text"), msg.get("chat")
    if not text or not chat:
        return
    reply = handle_text(chat["id"], text)
    if reply:
        r = await client.post(f"{base}/sendMessage", json={"chat_id": chat["id"], "text": reply})
        r.raise_for_status()


async def safe_process_update(client: httpx.AsyncClient, base: str, update: dict) -> None:
    """Answer one update; on failure log what went wrong WITHOUT the request URL (it contains the bot token)."""
    try:
        await process_update(client, base, update)
    except httpx.HTTPStatusError as e:
        log.error("Telegram reply to update %s failed: HTTP %s", update.get("update_id"), e.response.status_code)
    except httpx.HTTPError as e:
        log.error("Telegram reply to update %s failed: %s", update.get("update_id"), type(e).__name__)
    except Exception as e:  # never let one bad message stop the bot; the type is enough to debug
        log.error("Telegram update %s could not be handled: %s", update.get("update_id"), type(e).__name__)


async def poll_forever() -> None:
    token = settings.telegram_bot_token
    if not token:
        return
    base = f"https://api.telegram.org/bot{token}"
    offset: int | None = None
    async with httpx.AsyncClient(timeout=40) as client:
        try:
            await client.post(f"{base}/setMyCommands", json={"commands": COMMANDS})
        except httpx.HTTPError:
            log.warning("could not register bot commands")
        log.info("Telegram bot listening for commands")
        while True:
            try:
                params = {"timeout": 30, "allowed_updates": '["message"]'}
                if offset is not None:
                    params["offset"] = offset
                r = await client.get(f"{base}/getUpdates", params=params)
                if r.status_code == 409:  # another getUpdates consumer (e.g. a second backend instance)
                    log.warning("Telegram getUpdates conflict: is another instance polling this bot?")
                    await asyncio.sleep(30)
                    continue
                r.raise_for_status()
                for update in r.json()["result"]:
                    offset = update["update_id"] + 1
                    await safe_process_update(client, base, update)
            except httpx.HTTPError as e:
                log.warning("Telegram polling error: %s; retrying in 5s", type(e).__name__)
                await asyncio.sleep(5)
