"""Pilot sites: fixed locations monitored as virtual stations (no hardware needed)."""

import json
import logging
from pathlib import Path

from sqlalchemy.orm import Session

from app.config import settings
from app.db import Node

log = logging.getLogger(__name__)


def load_sites(path: str | None = None) -> list[dict]:
    p = Path(path or settings.sites_file)
    if not p.exists():
        log.warning("sites file %s not found; no virtual stations", p)
        return []
    return json.loads(p.read_text())["sites"]


def sync_sites(db: Session, sites: list[dict] | None = None) -> list[Node]:
    """Create or update a Node (kind=virtual) for each configured site."""
    nodes = []
    for s in sites if sites is not None else load_sites():
        node = db.get(Node, s["id"]) or Node(id=s["id"], kind="virtual")
        node.name, node.lat, node.lon = s.get("name"), s["lat"], s["lon"]
        node.biome, node.radius_km, node.kind = s.get("biome"), s.get("radius_km"), "virtual"
        db.add(node)
        nodes.append(node)
    db.commit()
    return nodes
