import math
from datetime import date

import pytest

netCDF4 = pytest.importorskip("netCDF4")
np = pytest.importorskip("numpy")

from app.validation import inpe_risk as v  # noqa: E402


@pytest.mark.parametrize("rf,cls", [(0.0, "minimo"), (0.149, "minimo"), (0.15, "baixo"), (0.5, "medio"),
                                    (0.7, "alto"), (0.96, "critico"), (1.0, "critico")])
def test_rf_class_limits(rf, cls):
    assert v.rf_class(rf) == cls


def test_spearman():
    assert v.spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert v.spearman([1, 2, 3, 4], [4, 3, 2, 1]) == pytest.approx(-1.0)
    assert v.spearman([1, 2, 2, 3], [1, 2, 2, 3]) == pytest.approx(1.0)  # ties
    assert math.isnan(v.spearman([1, 2], [1, 2]))


def make_grid(path, lat_desc=False):
    lats = np.arange(-15.0, -13.0, 0.01)
    if lat_desc:
        lats = lats[::-1]
    lons = np.arange(-48.5, -47.0, 0.01)
    with netCDF4.Dataset(path, "w") as ds:
        ds.createDimension("time", 1)
        ds.createDimension("lat", len(lats))
        ds.createDimension("lon", len(lons))
        ds.createVariable("lat", "f8", ("lat",))[:] = lats
        ds.createVariable("lon", "f8", ("lon",))[:] = lons
        rf = ds.createVariable("rf", "f4", ("time", "lat", "lon"))
        data = np.full((1, len(lats), len(lons)), 0.2, dtype="f4")
        # a hot cell 5 km east of the site centre, a missing (-999) cell, and a hot cell far outside the radius
        data[0, np.abs(lats - -14.07).argmin(), np.abs(lons - -47.634).argmin()] = 1.0
        data[0, np.abs(lats - -14.07).argmin(), np.abs(lons - -47.68).argmin()] = -999
        data[0, np.abs(lats - -14.9).argmin(), np.abs(lons - -48.4).argmin()] = 1.0
        rf[:] = data


@pytest.mark.parametrize("lat_desc", [False, True])
def test_sample_grid_radius_mean_max_and_missing(tmp_path, lat_desc):
    p = tmp_path / "rf.nc"
    make_grid(p, lat_desc)
    site = {"id": "veadeiros", "lat": -14.07, "lon": -47.68, "radius_km": 10}
    s = v.sample_grid(p, [site, {"id": "outside", "lat": 0.0, "lon": 0.0, "radius_km": 5}])
    assert "outside" not in s
    sv = s["veadeiros"]
    assert math.isnan(sv.rf_center)  # -999 is missing, not a value
    assert sv.rf_max == pytest.approx(1.0)  # the hot cell 5 km away is inside the 10 km radius
    assert 0.2 < sv.rf_mean < 0.21  # one hot cell among hundreds of 0.2 cells; far hot cell excluded


def test_build_rows_and_summary():
    days = [date(2026, 11, d) for d in (1, 2, 3, 4)]
    fma = {days[0]: 1.0, days[1]: 5.0, days[2]: 12.0, days[3]: 30.0}  # nula, pequena, media, muito_alta
    rf = {(d.isoformat(), "x"): v.Sample(float("nan"), m, m)
          for d, m in zip(days, (0.05, 0.2, 0.3, float("nan")))}  # minimo, baixo, baixo, missing
    rows = v.build_rows("x", fma, rf, days)
    assert [(r.fma_class, r.rf_class, r.class_gap) for r in rows] == [
        ("nula", "minimo", 0), ("pequena", "baixo", 0), ("media", "baixo", 1)]
    st = v.summarize(rows)
    assert st["n"] == 3 and st["exact"] == pytest.approx(2 / 3) and st["within_one"] == 1.0
    assert st["mean_gap"] == pytest.approx(1 / 3) and st["spearman"] == pytest.approx(1.0)
    assert v.summarize([]) == {"n": 0}
