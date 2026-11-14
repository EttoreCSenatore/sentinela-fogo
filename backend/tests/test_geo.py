import json
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, inspect

from app import geo
from app.config import settings
from app.db import Hotspot, SessionLocal, add_missing_columns
from app.ingest import inpe


@pytest.fixture
def square(tmp_path, monkeypatch):
    """A 1°x1° state 'XX' with a hole in the middle, and an island 'YY'."""
    f = tmp_path / "b.geojson"
    f.write_text(json.dumps({"type": "FeatureCollection", "features": [
        {"properties": {"sigla": "XX", "nome": "X"}, "geometry": {"type": "Polygon", "coordinates": [
            [[-50, -10], [-49, -10], [-49, -9], [-50, -9], [-50, -10]],
            [[-49.6, -9.6], [-49.4, -9.6], [-49.4, -9.4], [-49.6, -9.4], [-49.6, -9.6]],
        ]}},
        {"properties": {"sigla": "YY", "nome": "Y"}, "geometry": {"type": "MultiPolygon", "coordinates": [
            [[[-40, -10], [-39.99, -10], [-39.99, -9.99], [-40, -10]]],
        ]}},
    ]}))
    monkeypatch.setattr(settings, "boundaries_file", str(f))
    geo._states_cached.cache_clear()
    yield
    geo._states_cached.cache_clear()


def test_inside_hole_and_outside(square):
    assert geo.locate_uf(-9.8, -49.8) == "XX"
    assert geo.locate_uf(-9.5, -49.5, tolerance_km=0) is None  # inside the hole
    assert geo.locate_uf(-5.0, -45.0) is None


def test_border_tolerance(square):
    just_outside = (-9.5, -48.99)  # ~1.1 km east of the edge at lon -49
    assert geo.locate_uf(*just_outside, tolerance_km=0) is None
    assert geo.locate_uf(*just_outside, tolerance_km=2) == "XX"
    assert geo.locate_uf(-9.5, -48.95, tolerance_km=2) is None  # ~5.5 km away
    assert geo.locate_uf(-9.995, -39.98, tolerance_km=2) == "YY"  # next to the tiny island


def test_missing_file_falls_back(monkeypatch):
    monkeypatch.setattr(settings, "boundaries_file", "/nonexistent.geojson")
    geo._states_cached.cache_clear()
    try:
        assert not geo.boundaries_available() and geo.locate_uf(-15.8, -47.9) is None
        rows = inpe.parse_csv("lat,lon,satelite,data\n9.3,-63.0,GOES-19,2026-11-14 15:40:00\n"
                              "-15.79,-47.88,GOES-19,2026-11-14 15:40:00\n")
        assert [r["uf"] for r in rows] == [None]  # bbox only: still drops the far-away point
    finally:
        geo._states_cached.cache_clear()


@pytest.mark.parametrize("lat,lon,uf", [
    (-15.79, -47.88, "DF"), (-3.12, -60.02, "AM"), (-30.03, -51.23, "RS"), (-16.75, -56.75, "MT"),
    (-3.85, -32.42, "PE"),          # Fernando de Noronha, via tolerance
    (-17.78, -63.18, None),         # Santa Cruz de la Sierra, Bolivia
    (-25.28, -57.63, None),         # Asunción, Paraguay
    (-23.2, -43.0, None),           # Atlantic, ~30 km off Rio
])
def test_real_ibge_boundaries(lat, lon, uf):
    geo._states_cached.cache_clear()
    assert geo.locate_uf(lat, lon) == uf


def test_parse_csv_tags_state_and_drops_foreign():
    geo._states_cached.cache_clear()
    csv = ("lat,lon,satelite,data\n"
           "-15.79,-47.88,GOES-19,2026-11-14 15:40:00\n"
           "-17.78,-63.18,GOES-19,2026-11-14 15:40:00\n")  # Bolivia, inside the old rectangle
    assert [(r["lat"], r["uf"]) for r in inpe.parse_csv(csv)] == [(-15.79, "DF")]


def test_tag_existing_and_api_filter(client):
    geo._states_cached.cache_clear()
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        db.add_all([Hotspot(lat=-15.79, lon=-47.88, satellite="A", ts=now),     # DF
                    Hotspot(lat=-16.75, lon=-56.75, satellite="A", ts=now),     # MT
                    Hotspot(lat=-17.78, lon=-63.18, satellite="A", ts=now)])    # Bolivia
        db.commit()
        assert inpe.tag_existing(db) == (2, 1)
        assert inpe.tag_existing(db) == (0, 0)
    assert sorted(h["uf"] for h in client.get("/api/hotspots").json()) == ["DF", "MT"]
    assert [h["uf"] for h in client.get("/api/hotspots?uf=mt").json()] == ["MT"]


def test_add_missing_columns_on_old_database(tmp_path):
    eng = create_engine(f"sqlite:///{tmp_path}/old.db")
    with eng.begin() as c:  # hotspots table as created by the first release (no uf column)
        c.exec_driver_sql("CREATE TABLE hotspots (id INTEGER PRIMARY KEY, lat FLOAT, lon FLOAT, "
                          "satellite VARCHAR(32), ts DATETIME)")
        c.exec_driver_sql("INSERT INTO hotspots (lat, lon, satellite, ts) VALUES (-15.8, -47.9, 'A', '2026-11-14')")
    assert add_missing_columns(eng) == ["hotspots.uf"]
    assert "uf" in {col["name"] for col in inspect(eng).get_columns("hotspots")}
    assert add_missing_columns(eng) == []
