"""Compare ground elevation at buildings: USGS 3DEP 1 m DEM against the NOAA 3 m DEM (prompt 28 Part 1, D-160).

    /Users/.../Climate-Resilience---Miami-Dade/.venv/bin/python -I scripts/benefit/compare_dem.py

Sample: 5,000 buildings from the Stage 1 buildings table, stratified by tract
(each tract in proportion to its number of buildings, at least one), seed 20261111.
The NOAA value is the one already stored on each building (Stage 1, D-126).
The 3DEP value is read remotely, block by block, from the FL_MiamiDade_D23 1 m
tiles listed by the National Map API (tile index saved in data/raw/usgs_3dep):
- point value: the 1 m cell under the building point;
- 3 x 3 m mean: the mean of the 3 x 3 block of 1 m cells around it, which is
  the same footprint as one NOAA cell, so resolution alone is separated from
  the other differences (lidar date, processing).
Both are NAVD88 heights in metres, converted to feet.
Writes outputs/benefit/spec_alignment/dem_compare_sample.csv and dem_compare.json.
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
import paths  # noqa: E402

OUT = paths.OUT_BENEFIT / "spec_alignment"
N = 5000
SEED = 20261111
FT = 0.3048
ENV = dict(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR", GDAL_HTTP_MULTIRANGE="YES", GDAL_HTTP_MAX_RETRY="5",
           GDAL_HTTP_RETRY_DELAY="3", VSI_CACHE="FALSE")


def sample_buildings():
    cols = ["bid", "lon", "lat", "GEOID_tract", "ground_elev_ft_navd88", "fema_zone", "occtype", "ftprntsqft",
            "num_story", "med_yr_blt"]
    b = pd.read_parquet(paths.BUILDINGS_PARQUET, columns=cols).dropna(subset=["ground_elev_ft_navd88"])
    rng = np.random.default_rng(SEED)
    share = b.GEOID_tract.value_counts(normalize=True)
    take = np.maximum(1, np.round(share * N)).astype(int)
    idx = []
    for tr, k in take.items():
        rows = b.index[b.GEOID_tract == tr]
        idx.extend(rng.choice(rows, size=min(k, len(rows)), replace=False))
    idx = np.array(idx)
    if len(idx) > N:
        idx = rng.choice(idx, size=N, replace=False)
    return b.loc[np.sort(idx)].reset_index(drop=True)


def tile_urls():
    d = json.loads(paths.USGS_3DEP_INDEX_JSON.read_text())
    out = {}
    for i in d["items"]:
        u = i["downloadURL"]
        if f"/Projects/{paths.USGS_3DEP_PROJECT}/" in u:
            key = u.split("USGS_1M_17_")[1].split("_")[0]          # e.g. x51y279
            out[key] = u
    return out


def main():
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    s = sample_buildings()
    e, n = Transformer.from_crs("EPSG:4269", "EPSG:26917", always_xy=True).transform(s.lon.values, s.lat.values)
    s["utm_e"], s["utm_n"] = e, n
    # USGS 1 m tile names give the upper-left corner in units of 10 km: x51y279 = E 510,000, N 2,790,000
    s["tile"] = ["x%dy%d" % (int(a // 10000), int(np.ceil(c / 10000))) for a, c in zip(e, n)]
    urls = tile_urls()
    s["tile_in_project"] = s.tile.isin(urls)

    def read_point(i):
        u = urls.get(s.tile[i])
        if u is None:
            return i, np.nan, np.nan
        for attempt in range(5):
            try:
                with rasterio.Env(**ENV), rasterio.open("/vsicurl/" + u) as r:
                    row, col = r.index(s.utm_e[i], s.utm_n[i])
                    a = r.read(1, window=Window(col - 1, row - 1, 3, 3), boundless=True, fill_value=r.nodata)
                    a = a.astype(float)
                    a[(a == r.nodata) | (a < -50)] = np.nan
                pt = a[1, 1]
                m = np.nanmean(a) if np.isfinite(a).sum() >= 5 else np.nan
                return i, pt, m
            except Exception:
                if attempt == 4:
                    return i, np.nan, np.nan
                time.sleep(3 * (attempt + 1))

    pt = np.full(len(s), np.nan)
    m3 = np.full(len(s), np.nan)
    with ThreadPoolExecutor(max_workers=16) as ex:
        for k, (i, a, b) in enumerate(ex.map(read_point, range(len(s)))):
            pt[i], m3[i] = a, b
            if (k + 1) % 500 == 0:
                print(f"{k + 1:,}/{len(s):,} points, {time.time() - t0:.0f}s", flush=True)
    s["usgs_pt_ft"] = pt / FT
    s["usgs_3x3_ft"] = m3 / FT
    s["diff_pt_ft"] = s.usgs_pt_ft - s.ground_elev_ft_navd88          # 3DEP minus NOAA
    s["diff_3x3_ft"] = s.usgs_3x3_ft - s.ground_elev_ft_navd88
    s.drop(columns=["utm_e", "utm_n"]).to_csv(OUT / "dem_compare_sample.csv", index=False)

    ok = s.dropna(subset=["diff_pt_ft"])
    def stats(x):
        return {"n": int(len(x)), "median": round(float(x.median()), 3), "mean": round(float(x.mean()), 3),
                "p05": round(float(x.quantile(.05)), 2), "p25": round(float(x.quantile(.25)), 2),
                "p75": round(float(x.quantile(.75)), 2), "p95": round(float(x.quantile(.95)), 2),
                "median_abs": round(float(x.abs().median()), 3),
                "share_abs_over_0_5ft": round(float((x.abs() > 0.5).mean()), 3),
                "share_abs_over_1ft": round(float((x.abs() > 1).mean()), 3),
                "share_abs_over_2ft": round(float((x.abs() > 2).mean()), 3)}
    R = {"sample": len(s), "seed": SEED, "project": paths.USGS_3DEP_PROJECT,
         "points_outside_project_tiles": int((~s.tile_in_project).sum()),
         "points_no_usgs_value": int(s.usgs_pt_ft.isna().sum()),
         "diff_point_ft": stats(ok.diff_pt_ft), "diff_3x3_ft": stats(ok.diff_3x3_ft.dropna()),
         "corr_point": round(float(ok[["usgs_pt_ft", "ground_elev_ft_navd88"]].corr().iloc[0, 1]), 4),
         "by_fema_zone": {z: stats(g.diff_3x3_ft.dropna()) for z, g in ok.groupby("fema_zone") if len(g) >= 30},
         "seconds": round(time.time() - t0)}
    pl = pd.read_csv(paths.OUT_BENEFIT / "stage2" / "tract_places.csv", dtype={"GEOID_tract": str}).set_index("GEOID_tract").place
    ok = ok.assign(place=ok.GEOID_tract.map(pl).fillna("unincorporated"))
    by_place = ok.groupby("place").diff_3x3_ft.agg(["size", "median", lambda x: x.abs().median()])
    by_place.columns = ["buildings", "median_diff_ft", "median_abs_diff_ft"]
    by_place = by_place[by_place.buildings >= 30].sort_values("median_abs_diff_ft", ascending=False).round(2)
    by_place.to_csv(OUT / "dem_compare_by_place.csv")
    R["places_largest_disagreement"] = by_place.head(8).reset_index().to_dict("records")
    R["largest_point_disagreements"] = ok.reindex(ok.diff_3x3_ft.abs().sort_values(ascending=False).index).head(10)[
        ["bid", "place", "fema_zone", "occtype", "ground_elev_ft_navd88", "usgs_3x3_ft", "diff_3x3_ft"]].round(2).to_dict("records")
    (OUT / "dem_compare.json").write_text(json.dumps(R, indent=2, default=str))
    print(json.dumps(R, indent=1, default=str))


if __name__ == "__main__":
    main()
