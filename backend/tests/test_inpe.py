import httpx
import respx

from app.db import Hotspot, SessionLocal
from app.ingest import inpe

LISTING = """<a href="focos_10min_20261114_1550.csv">x</a>
<a href="focos_10min_20261114_1600.csv">x</a><a href="focos_10min_20261114_1600.csv">dup</a>"""

CSV = """lat,lon,satelite,data
   9.297000, -63.000500,GOES-19,2026-11-14 15:40:00
 -15.790000, -47.880000,GOES-19,2026-11-14 15:40:00
 -10.000000, -55.000000,NOAA-21,2026-11-14 15:50:00
bad,row,x,y
"""


def test_latest_files_sorted_and_deduped():
    assert inpe.latest_files(LISTING, 1) == ["focos_10min_20261114_1600.csv"]
    assert len(inpe.latest_files(LISTING, 5)) == 2


def test_parse_filters_to_brazil_bbox():
    rows = inpe.parse_csv(CSV)
    assert [(r["lat"], r["satellite"]) for r in rows] == [(-15.79, "GOES-19"), (-10.0, "NOAA-21")]
    assert rows[0]["ts"].tzinfo is not None


@respx.mock
async def test_fetch_and_store_idempotent():
    base = inpe.settings.inpe_base_url
    respx.get(base).mock(return_value=httpx.Response(200, text=LISTING))
    respx.get(base + "focos_10min_20261114_1600.csv").mock(return_value=httpx.Response(200, text=CSV))
    async with httpx.AsyncClient() as c:
        rows = await inpe.fetch_latest(c, n=1)
    with SessionLocal() as db:
        assert inpe.store(db, rows) == 2
        assert inpe.store(db, rows) == 0
        assert db.query(Hotspot).count() == 2
