"""Ground elevation at every building from the USGS 3DEP 1 m DEM (prompt 28 Part 2, D-166).

    /Users/.../Climate-Resilience---Miami-Dade/.venv/bin/python -I scripts/benefit/sample_3dep.py

Datum check (vendor metadata FL_MiamiDade_D23_Digital_Elevation_Model.xml and the
USGS final DEM report): NAVD88 (GEOID18), NAD83(2011); 10 cm RMSEz accuracy class.
The 1 m tiles are NAVD88 metres in NAD83 / UTM 17N.

Reads each 512 x 512 block of the FL_MiamiDade_D23 tiles once over the web and
takes the 1 m cell under each building point. If that cell is empty (water or
gap), the mean of the 3 x 3 cells around it is used; if still empty, the NOAA
value is kept and flagged. Writes data/processed/benefit/ground_3dep.parquet
(bid, ground_elev_ft_3dep, ground_source) and a summary json.
Must not import geopandas or pyogrio (see sample_rasters.py).
"""
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from pyproj import Transformer
from rasterio.windows import Window

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
from compare_dem import ENV, FT, tile_urls  # noqa: E402

OUT = paths.OUT_BENEFIT / "spec_alignment"
BLOCK = 512


def main():
    t0 = time.time()
    b = pd.read_parquet(paths.BUILDINGS_PARQUET, columns=["fd_id", "bid", "lon", "lat", "ground_elev_ft_navd88"])
    import pyarrow.parquet as pq
    noaa_col = "ground_elev_ft_noaa" if "ground_elev_ft_noaa" in pq.ParquetFile(paths.BUILDINGS_PARQUET).schema.names else "ground_elev_ft_navd88"
    noaa = pd.read_parquet(paths.BUILDINGS_PARQUET, columns=[noaa_col])[noaa_col].to_numpy()
    e, n = Transformer.from_crs("EPSG:4269", "EPSG:26917", always_xy=True).transform(b.lon.values, b.lat.values)
    tile = np.array(["x%dy%d" % (int(a // 10000), int(np.ceil(c / 10000))) for a, c in zip(e, n)])
    urls = tile_urls()
    # each tile is 10,000 x 10,000 m with a small overlap; pixel row/col from its own transform
    with rasterio.Env(**ENV):
        tf = {}
        for k in np.unique(tile):
            if k in urls:
                with rasterio.open("/vsicurl/" + urls[k]) as r:
                    tf[k] = (r.transform, r.width, r.height, r.nodata)
    row = np.full(len(b), -1)
    col = np.full(len(b), -1)
    for k, (T, w, h, _) in tf.items():
        m = tile == k
        c, r_ = ~T * (e[m], n[m])
        row[m], col[m] = np.floor(r_).astype(int), np.floor(c).astype(int)
    ok = (row >= 0) & np.isin(tile, list(tf))
    key = pd.Series(np.where(ok, [f"{t}|{r // BLOCK}|{c // BLOCK}" for t, r, c in zip(tile, row, col)], ""))
    groups = key[ok].groupby(key[ok]).indices
    idx_all = np.flatnonzero(ok)
    print(f"{len(groups):,} blocks for {ok.sum():,} buildings ({(~ok).sum():,} outside the project tiles)", flush=True)

    pt = np.full(len(b), np.nan)
    m3 = np.full(len(b), np.nan)

    def read_block(k):
        loc = idx_all[groups[k]]
        t, br, bc = k.split("|")
        br, bc = int(br), int(bc)
        nod = tf[t][3]
        for attempt in range(5):
            try:
                with rasterio.Env(**ENV), rasterio.open("/vsicurl/" + urls[t]) as r:
                    a = r.read(1, window=Window(bc * BLOCK - 1, br * BLOCK - 1, BLOCK + 2, BLOCK + 2),
                               boundless=True, fill_value=nod).astype(float)
                a[(a == nod) | (a < -50)] = np.nan
                rr = row[loc] - br * BLOCK + 1
                cc = col[loc] - bc * BLOCK + 1
                p = a[rr, cc]
                win = np.stack([a[rr + i, cc + j] for i in (-1, 0, 1) for j in (-1, 0, 1)])
                cnt = np.isfinite(win).sum(0)
                with np.errstate(invalid="ignore"):
                    mm = np.where(cnt >= 3, np.nansum(win, 0) / np.maximum(cnt, 1), np.nan)
                return loc, p, mm
            except Exception:
                if attempt == 4:
                    raise
                time.sleep(4 * (attempt + 1))

    done = 0
    with ThreadPoolExecutor(max_workers=16) as ex:
        for loc, p, mm in ex.map(read_block, list(groups)):
            pt[loc], m3[loc] = p, mm
            done += 1
            if done % 1000 == 0:
                print(f"{done:,}/{len(groups):,} blocks, {time.time() - t0:.0f}s", flush=True)
    g = np.where(np.isfinite(pt), pt, m3) / FT
    src = np.where(np.isfinite(pt), "3dep_1m_cell", np.where(np.isfinite(m3), "3dep_3x3_mean", "noaa_3m_fallback"))
    g = np.where(np.isfinite(g), g, noaa)
    out = pd.DataFrame({"fd_id": b.fd_id, "bid": b.bid, "ground_elev_ft_3dep": g, "ground_source": src})
    out.to_parquet(paths.GROUND_3DEP_PARQUET, index=False)
    d = g - noaa
    R = {"buildings": len(b), "blocks": len(groups), "seconds": round(time.time() - t0),
         "source_counts": pd.Series(src).value_counts().to_dict(),
         "still_missing": int(np.isnan(g).sum()),
         "diff_vs_noaa_ft": {"median": round(float(np.nanmedian(d)), 3),
                             "p05": round(float(np.nanpercentile(d, 5)), 2), "p95": round(float(np.nanpercentile(d, 95)), 2),
                             "share_abs_over_1ft": round(float(np.nanmean(np.abs(d) > 1)), 4),
                             "share_abs_over_2ft": round(float(np.nanmean(np.abs(d) > 2)), 4)},
         "datum": "NAVD88 (GEOID18), NAD83(2011); NOAA DEM: NAVD88 (Geoid 12B)"}
    (OUT / "ground_3dep_summary.json").write_text(json.dumps(R, indent=2))
    print(json.dumps(R, indent=1))


if __name__ == "__main__":
    main()
