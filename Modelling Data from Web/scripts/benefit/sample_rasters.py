"""Sample raster values at each building (prompt 27 Stage 1): storm surge class and NOAA DEM ground elevation.

    .venv/bin/python -I "Modelling Data from Web/scripts/benefit/sample_rasters.py" surge|dem

Run by build_buildings.py as a separate process. It must not import pyogrio or
geopandas: with both GDAL bindings loaded in one process, opening a raster after
reading vectors aborts Python (seen 10 Nov 2026). Reads outputs/benefit/stage1/points.csv.gz
(fd_id, lon, lat) and writes bld_surge.csv.gz or bld_dem.csv.gz. Method: D-126.
"""
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import rasterio
from rasterio.windows import Window, from_bounds

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import paths  # noqa: E402

CK = paths.OUT_BENEFIT / "stage1"
DEM_WATER = -50          # NOAA DEM codes open water as -99 m; anything below -50 m is treated as no ground
STATS = {}


class P:  # minimal stand-in for the GeoDataFrame interface the samplers use
    def __init__(self, df):
        self.fd_id = df.fd_id
        self.lon, self.lat = df.lon.values, df.lat.values


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------- storm surge
def sample_surge(nsi):
    out = pd.DataFrame({"fd_id": nsi.fd_id.values})
    lon, lat = nsi.lon, nsi.lat
    for cat in range(1, 6):
        with rasterio.open(paths.SURGE_DIR / f"us_Category{cat}_MOM_Inundation_HIGH.tif") as r:
            w = from_bounds(lon.min() - .01, lat.min() - .01, lon.max() + .01, lat.max() + .01, r.transform)
            w = w.round_offsets().round_lengths()
            a = r.read(1, window=w)
            rows, cols = rasterio.transform.rowcol(r.window_transform(w), lon, lat)
            v = a[np.asarray(rows), np.asarray(cols)].astype(int)
        cls = np.where((v >= 1) & (v <= 21), v, 0)  # 255 on land = not inundated; 99 never occurs here
        out[f"surge_cat{cat}_class"] = cls
        # class k = depth k-1 to k ft above ground; midpoint used as the depth; class 21 (> 20 ft) set to 20.5
        out[f"surge_cat{cat}_depth_ft"] = np.where(cls > 0, cls - 0.5, 0.0)
        STATS[f"surge_cat{cat}_buildings_wet"] = int((cls > 0).sum())
    return out


# ---------------------------------------------------------------- ground elevation (NOAA DEM, remote)
def sample_dem(nsi):
    lon, lat = nsi.lon, nsi.lat
    env = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MULTIRANGE="YES", GDAL_HTTP_MAX_RETRY="5",
               GDAL_HTTP_RETRY_DELAY="3", VSI_CACHE="FALSE")
    url = "/vsicurl/" + paths.NOAA_DEM_URL
    with rasterio.Env(**env), rasterio.open(url) as r:
        rows, cols = rasterio.transform.rowcol(r.transform, lon, lat)
        rows, cols = np.asarray(rows), np.asarray(cols)
        bx, by = r.block_shapes[0][1], r.block_shapes[0][0]
        nodata = r.nodata
        STATS["dem_profile"] = {"width": r.width, "height": r.height, "res_deg": r.res[0], "crs": str(r.crs),
                                "nodata": nodata, "block": [bx, by]}
    tile = (rows // by) * 100000 + (cols // bx)
    elev = np.full(len(lon), np.nan)
    groups = pd.Series(np.arange(len(lon))).groupby(tile).indices
    log(f"  DEM: {len(groups):,} tiles to read")

    def read_tile(key):
        idx = groups[key]
        tr, tc = key // 100000, key % 100000
        for attempt in range(5):
            try:
                with rasterio.Env(**env), rasterio.open(url) as r:
                    a = r.read(1, window=Window(tc * bx, tr * by, bx, by), boundless=True, fill_value=nodata)
                v = a[rows[idx] - tr * by, cols[idx] - tc * bx].astype(float)
                v[(v == nodata) | (v < DEM_WATER)] = np.nan
                return idx, v
            except Exception as e:  # network hiccup
                if attempt == 4:
                    raise
                time.sleep(5 * (attempt + 1))

    done = 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        for idx, v in ex.map(read_tile, list(groups)):
            elev[idx] = v
            done += 1
            if done % 200 == 0:
                log(f"  DEM: {done:,}/{len(groups):,} tiles")
    out = pd.DataFrame({"fd_id": nsi.fd_id.values, "ground_elev_m_navd88": elev})
    out["ground_elev_ft_navd88"] = out.ground_elev_m_navd88 / 0.3048
    STATS["dem_missing"] = int(np.isnan(elev).sum())
    return out



def main():
    which = sys.argv[1]
    pts = P(pd.read_csv(CK / "points.csv.gz"))
    t = time.time()
    out = sample_surge(pts) if which == "surge" else sample_dem(pts)
    out.to_csv(CK / f"bld_{which}.csv.gz", index=False)
    (CK / f"stats_{which}.json").write_text(json.dumps(STATS, indent=2, default=str))
    log(f"{which}: done in {time.time() - t:.0f}s")


if __name__ == "__main__":
    main()
