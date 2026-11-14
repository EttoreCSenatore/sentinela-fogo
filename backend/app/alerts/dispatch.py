"""Alert routing: recipients (owner, brigades, Defesa Civil...) x channels (telegram, whatsapp, sms, webhook).

Recipients come from settings.recipients_file (see config/recipients.example.json).
Without that file, settings.telegram_chat_id (if set) receives everything.
A channel without credentials configured is skipped and logged, never fatal.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

import httpx

from app.config import settings

log = logging.getLogger(__name__)
ALL_KINDS = ["fire", "hotspot", "danger"]


@dataclass
class Recipient:
    name: str
    channels: dict[str, str]
    sites: list[str] = field(default_factory=lambda: ["*"])
    kinds: list[str] = field(default_factory=lambda: list(ALL_KINDS))

    def wants(self, node_id: str, kind: str) -> bool:
        return ("*" in self.sites or node_id in self.sites) and kind in self.kinds


def load_recipients(path: str | None = None) -> list[Recipient]:
    p = Path(path or settings.recipients_file)
    if p.exists():
        data = json.loads(p.read_text())
        return [
            Recipient(r["name"], r["channels"], r.get("sites", ["*"]), r.get("kinds", list(ALL_KINDS)))
            for r in data.get("recipients", [])
        ]
    if settings.telegram_chat_id:
        return [Recipient("default", {"telegram": settings.telegram_chat_id})]
    return []


async def _telegram(client: httpx.AsyncClient, chat_id: str, alert: dict) -> bool:
    if not settings.telegram_bot_token:
        log.info("telegram not configured; skipping %s", chat_id)
        return False
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    r = await client.post(url, json={"chat_id": chat_id, "text": alert["message"]})
    r.raise_for_status()
    return True


async def _whatsapp(client: httpx.AsyncClient, phone: str, alert: dict) -> bool:
    if not (settings.whatsapp_token and settings.whatsapp_phone_number_id):
        log.info("whatsapp not configured; skipping %s", phone)
        return False
    url = f"https://graph.facebook.com/v21.0/{settings.whatsapp_phone_number_id}/messages"
    body = {"messaging_product": "whatsapp", "to": phone.lstrip("+"), "type": "text",
            "text": {"body": alert["message"]}}
    r = await client.post(url, json=body, headers={"Authorization": f"Bearer {settings.whatsapp_token}"})
    r.raise_for_status()
    return True


async def _sms(client: httpx.AsyncClient, phone: str, alert: dict) -> bool:
    sid, token = settings.twilio_account_sid, settings.twilio_auth_token
    if not (sid and token and settings.twilio_from):
        log.info("sms not configured; skipping %s", phone)
        return False
    url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    r = await client.post(url, data={"To": phone, "From": settings.twilio_from, "Body": alert["message"][:1500]},
                          auth=(sid, token))
    r.raise_for_status()
    return True


async def _webhook(client: httpx.AsyncClient, url: str, alert: dict) -> bool:
    r = await client.post(url, json=alert)
    r.raise_for_status()
    return True


CHANNELS = {"telegram": _telegram, "whatsapp": _whatsapp, "sms": _sms, "webhook": _webhook}


@dataclass
class Delivery:
    recipient: str
    channel: str
    ok: bool
    detail: str = ""


def _error_detail(e: httpx.HTTPError) -> str:
    if isinstance(e, httpx.HTTPStatusError):
        try:  # Telegram/Meta/Twilio all return a JSON error description
            body = e.response.json()
            return str(body.get("description") or body.get("message") or body.get("error") or body)
        except ValueError:
            return f"HTTP {e.response.status_code}"
    return type(e).__name__


async def deliver(node_id: str, kind: str, message: str, score: float = 0.0) -> list[Delivery]:
    """Deliver to every matching recipient/channel and report each attempt."""
    alert = {"node_id": node_id, "kind": kind, "score": score, "message": message}
    targets = [(r.name, ch, addr) for r in load_recipients() if r.wants(node_id, kind)
               for ch, addr in r.channels.items()]
    if not targets:
        log.warning("ALERT (no recipient): %s", message)
        return []

    async with httpx.AsyncClient(timeout=10) as client:
        async def one(name: str, ch: str, addr: str) -> Delivery:
            sender = CHANNELS.get(ch)
            if sender is None:
                log.warning("unknown channel %r for %s", ch, name)
                return Delivery(name, ch, False, "unknown channel")
            try:
                ok = await sender(client, addr, alert)
                return Delivery(name, ch, ok, "" if ok else "channel not configured")
            except httpx.HTTPError as e:
                detail = _error_detail(e)
                log.error("%s delivery to %s failed: %s", ch, name, detail)
                return Delivery(name, ch, False, detail)

        return list(await asyncio.gather(*(one(*t) for t in targets)))


async def send_alert(node_id: str, kind: str, message: str, score: float = 0.0) -> bool:
    """Deliver to every matching recipient/channel. True if at least one delivery succeeded."""
    return any(d.ok for d in await deliver(node_id, kind, message, score))
