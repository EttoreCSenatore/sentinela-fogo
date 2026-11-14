import asyncio
import json
import logging

import aiomqtt
from pydantic import ValidationError

from app import service
from app.config import settings
from app.db import SessionLocal
from app.schemas import Telemetry

log = logging.getLogger(__name__)


async def handle_payload(payload: bytes | str, topic: str) -> None:
    try:
        data = json.loads(payload)
        # The topic is authoritative for node_id, so a node cannot write into another node's data.
        data["node_id"] = topic.split("/")[3]
        t = Telemetry.model_validate(data)
    except (json.JSONDecodeError, ValidationError, IndexError) as e:
        log.warning("Bad telemetry on %s: %s", topic, e)
        return
    with SessionLocal() as db:
        await service.process(db, t)


async def run_forever() -> None:
    while True:
        try:
            async with aiomqtt.Client(
                settings.mqtt_host, settings.mqtt_port,
                username=settings.mqtt_username, password=settings.mqtt_password,
            ) as client:
                await client.subscribe(settings.mqtt_topic, qos=1)
                log.info("MQTT subscribed to %s", settings.mqtt_topic)
                async for msg in client.messages:
                    try:
                        await handle_payload(msg.payload, str(msg.topic))
                    except Exception:
                        log.exception("Failed to process message on %s", msg.topic)
        except aiomqtt.MqttError as e:
            log.warning("MQTT connection lost (%s); retrying in 5s", e)
            await asyncio.sleep(5)
