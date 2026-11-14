import math

import pytest

from app.risk.detect import haversine_km, score_reading
from app.risk.fma import DayObs, daily_observations, danger_class, fma_plus, fma_series, rain_factor


def test_fma_plus_accumulates_dry_days():
    days = [DayObs(humidity_13h=20, wind_13h=0)] * 3
    assert fma_plus(days) == pytest.approx(15.0)  # 3 × 100/20
    assert danger_class(15.0) == "alta"


def test_fma_plus_wind_term():
    assert fma_plus([DayObs(50, wind_13h=10)]) == pytest.approx(2 * math.exp(0.4))


@pytest.mark.parametrize("rain,factor", [(0, 1.0), (3, 0.7), (7, 0.4), (11, 0.2), (13, None)])
def test_rain_factor(rain, factor):
    assert rain_factor(rain) == factor


def test_heavy_rain_resets():
    days = [DayObs(20)] * 5 + [DayObs(80, rain_mm=30), DayObs(50)]
    assert fma_plus(days) == pytest.approx(2.0)


@pytest.mark.parametrize("v,cls", [(1, "nula"), (5, "pequena"), (10, "media"), (20, "alta"), (40, "muito_alta")])
def test_classes(v, cls):
    assert danger_class(v) == cls


def test_haversine_brasilia_goiania():
    assert haversine_km(-15.79, -47.88, -16.68, -49.25) == pytest.approx(178, abs=5)


BASE = dict(hotspot_radius_km=5.0, nearest_hotspot_km=None)
CALM = [(28.0, 40.0, 50.0)] * 5


def test_calm_reading_scores_zero():
    d = score_reading(temp_c=28.5, humidity_pct=39, smoke_ppm=52, flame=False, history=CALM, **BASE)
    assert d.score == 0 and d.reasons == []


def test_fire_signature_crosses_threshold():
    d = score_reading(temp_c=38, humidity_pct=22, smoke_ppm=400, flame=False, history=CALM, **BASE)
    assert d.score == pytest.approx(0.7)
    assert len(d.reasons) == 2


def test_hotspot_corroboration_and_cap():
    d = score_reading(temp_c=38, humidity_pct=22, smoke_ppm=400, flame=True, history=CALM,
                      hotspot_radius_km=5.0, nearest_hotspot_km=2.0)
    assert d.score == 1.0


def test_smoke_needs_baseline():
    d = score_reading(temp_c=28, humidity_pct=40, smoke_ppm=999, flame=False, history=CALM[:1], **BASE)
    assert d.score == 0


def test_fma_series_running_values_and_reset():
    days = [DayObs(20), DayObs(20), DayObs(50, rain_mm=20), DayObs(50)]
    assert fma_series(days) == pytest.approx([5.0, 10.0, 0.0, 2.0])


def test_daily_observations_uses_site_local_13h():
    from datetime import datetime, timedelta, timezone
    from zoneinfo import ZoneInfo
    # Hourly points for one day, RH = UTC hour so we can see which hour was picked.
    start = datetime(2026, 11, 10, 3, tzinfo=timezone.utc)
    pts = [(start + timedelta(hours=h), float((3 + h) % 24), 1.0, 0.5) for h in range(24)]
    [(_, sp)] = [x for x in daily_observations(pts, ZoneInfo("America/Sao_Paulo")) if x[0].day == 10]
    [(_, cb)] = [x for x in daily_observations(pts, ZoneInfo("America/Cuiaba")) if x[0].day == 10]
    assert sp.humidity_13h == 16  # 13:00 UTC-3 = 16 UTC
    assert cb.humidity_13h == 17  # 13:00 UTC-4 = 17 UTC (was wrongly 16 before)
    assert sp.rain_mm == pytest.approx(0.5 * 24)  # 03 UTC on the 10th .. 02 UTC on the 11th = whole local day
