"""INPE Risco de Fogo ingest: GeoTIFF/NetCDF sampling, storage, today/forecast selection and danger alerts."""

from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
import numpy as np
import pytest
import respx
import tifffile

from app import service
from app.db import Alert, Reading, SessionLocal, SiteRisk
from app.ingest import inpe_risk as ir
from app.sites import site_timezone, sync_sites

SITE = {"id": "chapada", "name": "Chapada", "lat": -14.07, "lon": -47.68, "radius_km": 10}
GDAL_MD = ('<GDALMetadata>\n  <Item name="time#units">hours since {d} 18:00:00</Item>\n'
           '  <Item name="NC_GLOBAL#title">Risco de fogo previsto para o dia {d}</Item>\n</GDALMetadata>')


def write_geotiff(path: Path, value: float, valid: str, hot_cell: bool = True) -> None:
    """Tiled, LZW-compressed GeoTIFF shaped like INPE's (north-up, 0.01°, top-left tiepoint, -999 nodata)."""
    lat0, lon0, step = -13.5, -48.5, 0.01
    h, w = 150, 200  # covers lat -13.5..-15.0, lon -48.5..-46.5
    data = np.full((h, w), value, dtype="f8")
    data[:10, :] = -999  # a band of no-data
    if hot_cell:
        row, col = int((lat0 - -14.07) / step), int((-47.63 - lon0) / step)  # ~5 km east of the centre
        data[row, col] = 1.0
    tifffile.imwrite(
        path, data, tile=(64, 64), compression="lzw",
        extratags=[
            (33550, "d", 3, (step, step, 0.0)),
            (33922, "d", 6, (0.0, 0.0, 0.0, lon0, lat0, 0.0)),
            (42112, "s", 0, GDAL_MD.format(d=valid)),
            (42113, "s", 0, "-999"),
        ],
    )


def test_geotiff_sampling_and_valid_date(tmp_path):
    p = tmp_path / "RF.PREV.T1.tif"
    write_geotiff(p, 0.5, "2026-11-15")
    assert ir.tiff_valid_date(p) == date(2026, 11, 15)
    s = ir.sample_geotiff(p, [SITE, {"id": "far", "lat": 0.0, "lon": 0.0, "radius_km": 5}])
    assert "far" not in s
    assert s["chapada"].rf_max == pytest.approx(1.0)
    assert 0.5 < s["chapada"].rf_mean < 0.51
    assert s["chapada"].rf_center == pytest.approx(0.5)


@pytest.mark.parametrize("v,cls", [(0.1, "minimo"), (0.3, "baixo"), (0.5, "medio"), (0.8, "alto"), (0.99, "critico")])
def test_rf_class(v, cls):
    assert ir.rf_class(v) == cls


def _today():
    return datetime.now(ZoneInfo(site_timezone("chapada"))).date()


def setup_site():
    with SessionLocal() as db:
        sync_sites(db, [SITE])


def test_store_upserts_and_keeps_newest_forecast():
    setup_site()
    d = date(2026, 11, 16)
    with SessionLocal() as db:
        ir.store(db, "forecast", d, date(2026, 11, 14), {"chapada": ir.Sample(0, 0.3, 0.4)})
        ir.store(db, "forecast", d, date(2026, 11, 15), {"chapada": ir.Sample(0, 0.8, 0.9)})  # newer run
        ir.store(db, "forecast", d, date(2026, 11, 13), {"chapada": ir.Sample(0, 0.1, 0.1)})  # stale run
        rows = db.query(SiteRisk).all()
    assert len(rows) == 1 and rows[0].rf_mean == 0.8 and rows[0].issued_date == date(2026, 11, 15)


def test_inpe_risk_prefers_today_forecast_then_recent_observed():
    setup_site()
    t = _today()
    with SessionLocal() as db:
        assert service.inpe_risk(db, "chapada") is None
        ir.store(db, "observed", t - timedelta(days=1), t - timedelta(days=1), {"chapada": ir.Sample(0, 0.2, 0.3)})
        r = service.inpe_risk(db, "chapada")
        assert r["today"]["kind"] == "observed" and r["today"]["risk_class"] == "baixo" and r["forecast"] == []
        for lead, v in enumerate([0.75, 0.5, 0.97, 0.1]):
            ir.store(db, "forecast", t + timedelta(days=lead), t, {"chapada": ir.Sample(0, v, v)})
        r = service.inpe_risk(db, "chapada")
    assert r["today"]["kind"] == "forecast" and r["today"]["label"] == "Alto"
    assert [d["risk_class"] for d in r["forecast"]] == ["medio", "critico", "minimo"]


def add_dry_fma_days(db, n=3):
    now = datetime.now(timezone.utc)
    for d in range(n, 0, -1):  # dry days at 13h Brasília -> FMA+ 5 per day
        db.add(Reading(node_id="chapada", ts=(now - timedelta(days=d)).replace(hour=16, minute=0),
                       temp_c=33, humidity_pct=20, flame=False, score=0))
    db.commit()


async def test_danger_alert_from_inpe_today():
    setup_site()
    t = _today()
    with SessionLocal() as db:
        add_dry_fma_days(db)
        ir.store(db, "forecast", t, t, {"chapada": ir.Sample(0, 0.82, 1.0)})
        ir.store(db, "forecast", t + timedelta(days=1), t, {"chapada": ir.Sample(0, 0.97, 1.0)})
        a = await service.check_danger(db, db.get(service.Node, "chapada"))
        again = await service.check_danger(db, db.get(service.Node, "chapada"))
    assert a is not None and again is None  # once a day
    assert "ALTO hoje em Chapada (INPE 0.82)" in a.message
    assert "Crítico (0.97)" in a.message and "FMA+ 15.0 (alta)" in a.message
    assert a.score == pytest.approx(0.97)


async def test_danger_early_warning_from_forecast_only():
    setup_site()
    t = _today()
    with SessionLocal() as db:
        ir.store(db, "forecast", t, t, {"chapada": ir.Sample(0, 0.3, 0.5)})
        ir.store(db, "forecast", t + timedelta(days=2), t, {"chapada": ir.Sample(0, 0.96, 1.0)})
        a = await service.check_danger(db, db.get(service.Node, "chapada"))
    assert a is not None and a.message.startswith("⚠️ Previsão: risco de fogo CRÍTICO")
    assert f"{t + timedelta(days=2):%d/%m}" in a.message


async def test_inpe_low_overrides_alarming_fma():
    setup_site()
    t = _today()
    with SessionLocal() as db:
        add_dry_fma_days(db)  # FMA+ alta on its own would alert
        ir.store(db, "forecast", t, t, {"chapada": ir.Sample(0, 0.5, 0.9)})
        assert await service.check_danger(db, db.get(service.Node, "chapada")) is None
        assert db.query(Alert).count() == 0


async def test_fma_fallback_without_inpe_data():
    setup_site()
    with SessionLocal() as db:
        add_dry_fma_days(db)
        a = await service.check_danger(db, db.get(service.Node, "chapada"))
    assert a is not None and "risco do INPE indisponível" in a.message


@respx.mock
async def test_poll_forecast_downloads_t0_t3_once_per_run(tmp_path):
    setup_site()
    issued = "Sat, 14 Nov 2026 09:35:24 GMT"
    for lead in range(4):
        p = tmp_path / f"T{lead}.tif"
        write_geotiff(p, 0.2 * (lead + 1), f"2026-11-{14 + lead}", hot_cell=False)
        respx.get(ir.FCST_URL + f"RF.PREV.T{lead}.tif").mock(return_value=httpx.Response(200, content=p.read_bytes()))
    head = respx.head(ir.FCST_URL + "RF.PREV.T0.tif").mock(
        return_value=httpx.Response(200, headers={"last-modified": issued}))
    async with httpx.AsyncClient() as c:
        assert await ir.poll_forecast(c) == 4
        assert await ir.poll_forecast(c) == 0  # same run: nothing downloaded again
    assert head.call_count == 2
    with SessionLocal() as db:
        rows = db.query(SiteRisk).order_by(SiteRisk.valid_date).all()
    assert [(r.valid_date.day, round(r.rf_mean, 2)) for r in rows] == [(14, 0.2), (15, 0.4), (16, 0.6), (17, 0.8)]
    assert all(r.issued_date == date(2026, 11, 14) for r in rows)
