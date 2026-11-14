"""Simulate sensor nodes in Brazilian biomes and publish telemetry over MQTT.

    python simulator/simulate.py --nodes 5 --interval 2 --fire-at 3

--fire-at N  starts a simulated fire at node 0 after N cycles (smoke/temp rise, RH drop, flame).
Uses aiomqtt from the backend venv.
"""

import argparse
import asyncio
import json
import random
from datetime import datetime, timezone

import aiomqtt

# (prefix, lat, lon, base_temp, base_rh): rough dry-season conditions
BIOMES = [
    ("cerrado", -15.8, -47.9, 31, 25),
    ("pantanal", -18.0, -56.5, 33, 35),
    ("amazonia", -9.0, -63.0, 32, 55),
    ("caatinga", -8.5, -40.5, 34, 30),
    ("mata-atlantica", -22.9, -43.5, 27, 60),
]


def make_nodes(n: int):
    nodes = []
    for i in range(n):
        prefix, lat, lon, t, rh = BIOMES[i % len(BIOMES)]
        nodes.append({
            "id": f"{prefix}-{i:03d}",
            "lat": lat + random.uniform(-0.3, 0.3),
            "lon": lon + random.uniform(-0.3, 0.3),
            "t": t, "rh": rh, "smoke": random.uniform(40, 70),
        })
    return nodes


def sample(node, fire_level: float):
    return {
        "lat": round(node["lat"], 5),
        "lon": round(node["lon"], 5),
        "temp_c": round(node["t"] + random.gauss(0, 0.4) + 12 * fire_level, 1),
        "humidity_pct": round(max(3, node["rh"] + random.gauss(0, 1.0) - 20 * fire_level), 1),
        "smoke_ppm": round(node["smoke"] * (1 + 9 * fire_level) + random.gauss(0, 3), 1),
        "flame": fire_level > 0.8,
        "wind_ms": round(abs(random.gauss(3, 1)), 1),
        "rain_mm": 0.0,
        "battery_v": round(random.uniform(3.7, 4.1), 2),
    }


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=1883)
    ap.add_argument("--nodes", type=int, default=5)
    ap.add_argument("--interval", type=float, default=2.0)
    ap.add_argument("--fire-at", type=int, default=None, help="cycle at which node 0 catches fire")
    args = ap.parse_args()

    nodes = make_nodes(args.nodes)
    cycle = 0
    async with aiomqtt.Client(args.host, args.port) as client:
        while True:
            for i, node in enumerate(nodes):
                fire = 0.0
                if args.fire_at is not None and i == 0 and cycle >= args.fire_at:
                    fire = min(1.0, (cycle - args.fire_at + 1) / 3)
                payload = sample(node, fire)
                topic = f"sentinela/v1/nodes/{node['id']}/telemetry"
                await client.publish(topic, json.dumps(payload), qos=1)
            print(f"{datetime.now(timezone.utc):%H:%M:%S} cycle {cycle}: published {len(nodes)} readings")
            cycle += 1
            await asyncio.sleep(args.interval)


if __name__ == "__main__":
    asyncio.run(main())
