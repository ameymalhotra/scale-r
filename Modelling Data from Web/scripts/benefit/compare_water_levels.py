"""Compare methods for carrying FEMA 2027 water levels to buildings (prompt 28 Part 2, D-170).

    /Users/.../Climate-Resilience---Miami-Dade/.venv/bin/python -I scripts/benefit/compare_water_levels.py

Steps:
1. Join every building to the 2027 flood zone polygon it sits in (zone,
   subtype, static base flood elevation, study source) and to its C-8/C-9
   subbasin. Saved as data/processed/benefit/fema2027_zones.parquet for
   Module A.
2. Coastal levels apply to buildings in polygons from the coastal studies
   (STUDY5 coastal, STUDY6 and STUDY7 combined coastal and riverine).
   Rainfall and canal levels apply to buildings inside the C-8 and C-9
   subbasins (STUDY7 and STUDY8).
3. Checks for each method:
   a. the 1% level against the base flood elevation of the 2027 polygon
      the building is in (coastal: AE and VE coastal floodplain; rain: AE and
      AH from STUDY7 or STUDY8). Coastal base flood elevations include wave
      height, so the coastal still-water level is expected to sit below
      them; the spread of the gap is what matters;
   b. flood extent: share of buildings inside the 1% zone whose ground is
      below the method's 1% level, and share inside the minimal hazard zone
      whose ground is above it.
4. The 2009 base flood elevations are compared with 2027 where both exist.
Writes outputs/benefit/spec_alignment/water_level_methods.json.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import pyogrio

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
import water_levels as wl  # noqa: E402

OUT = paths.OUT_BENEFIT / "spec_alignment"
COASTAL_SRC = ["STUDY5", "STUDY6", "STUDY7"]
RAIN_SRC = ["STUDY7", "STUDY8"]


def zones_join(b, pts, ext):
    import geopandas as gpd
    z = wl.read(ext, "S_Fld_Haz_Ar")[["FLD_ZONE", "ZONE_SUBTY", "STATIC_BFE", "DEPTH", "SOURCE_CIT", "geometry"]]
    g = gpd.GeoDataFrame({"i": np.arange(len(b))}, geometry=list(pts), crs=wl.CRS)
    j = gpd.sjoin(g, z, how="left", predicate="within").drop_duplicates("i").sort_values("i")
    sb = wl.read(ext, "S_Subbasins")[["NODE_ID", "BASIN_DESC", "geometry"]]
    k = gpd.sjoin(g, sb, how="left", predicate="within").drop_duplicates("i").sort_values("i")
    out = pd.DataFrame({
        "fd_id": b.fd_id.to_numpy(),
        "zone27": j.FLD_ZONE.to_numpy(), "zone27_subtype": j.ZONE_SUBTY.to_numpy(),
        "bfe27_ft": np.where(j.STATIC_BFE.to_numpy() > -9000, j.STATIC_BFE.to_numpy(), np.nan),
        "ao_depth27_ft": np.where(j.DEPTH.to_numpy() > -9000, j.DEPTH.to_numpy(), np.nan),
        "zone27_source": j.SOURCE_CIT.to_numpy(),
        "subbasin_node": k.NODE_ID.to_numpy(), "basin": k.BASIN_DESC.to_numpy()})
    return out


def check(level01, z, ground, mask_bfe, inside, minimal):
    d = (z.bfe27_ft - level01)[mask_bfe].dropna()
    r = {"buildings_compared_with_bfe": int(len(d)),
         "bfe_minus_level_median_ft": round(float(d.median()), 2) if len(d) else None,
         "bfe_minus_level_iqr_ft": [round(float(d.quantile(.25)), 2), round(float(d.quantile(.75)), 2)] if len(d) else None,
         "abs_dev_from_median_gap_ft": round(float((d - d.median()).abs().median()), 2) if len(d) else None,
         "within_0_5ft_of_bfe": round(float((d.abs() <= .5).mean()), 3) if len(d) else None,
         "within_1ft_of_bfe": round(float((d.abs() <= 1).mean()), 3) if len(d) else None,
         "level_above_bfe_share": round(float((d < -0.05).mean()), 3) if len(d) else None}
    wet = ground < level01
    r["in_1pct_zone_ground_below_level"] = round(float(wet[inside].mean()), 3)
    r["in_minimal_zone_ground_above_level"] = round(float((~wet)[minimal].mean()), 3)
    return r


def main():
    t0 = time.time()
    ext = paths.FIRM_2027_EXTRACT
    cols = ["fd_id", "lon", "lat", "ground_elev_ft_navd88", "fema_zone", "fema_bfe_ft_navd88"]
    b = pd.read_parquet(paths.BUILDINGS_PARQUET, columns=cols)
    ground = b.ground_elev_ft_navd88.to_numpy()
    pts, _, _ = wl.points(b)
    z = zones_join(b, pts, ext)
    z.to_parquet(paths.FEMA2027_ZONES_PARQUET, index=False)
    print(f"zones joined, {time.time() - t0:.0f}s", flush=True)

    R = {"buildings": len(b), "zone27_counts": z.zone27.fillna("none").value_counts().to_dict(),
         "zone27_source_counts": z.zone27_source.fillna("none").value_counts().to_dict()}
    sfha = z.zone27.isin(["A", "AE", "AH", "AO", "VE"]).to_numpy()
    minimal = (z.zone27 == "X") & z.zone27_subtype.fillna("").str.startswith("AREA OF MINIMAL")

    # coastal
    t = wl.transects(ext)
    cmask = z.zone27_source.isin(COASTAL_SRC).to_numpy()
    cp = pts[cmask]
    zc = z[cmask].reset_index(drop=True)
    gc = ground[cmask]
    bfe_mask_c = (zc.zone27.isin(["AE", "VE"]) & zc.zone27_subtype.fillna("").str.contains("COASTAL")).to_numpy()
    meth_c = {"nearest": wl.coastal_nearest(cp, t), "alongshore": wl.coastal_alongshore(cp, t, ext)}
    R["coastal"] = {"buildings": int(cmask.sum()), "transects": len(t),
                    "median_distance_to_transect_m": round(float(meth_c["nearest"].tsct_dist_m.median())),
                    "methods": {}}
    for k, m in meth_c.items():
        R["coastal"]["methods"][k] = check(m.p01.to_numpy(), zc, gc, bfe_mask_c, sfha[cmask], minimal[cmask].to_numpy())
    dd = (meth_c["nearest"][wl.EV] - meth_c["alongshore"][wl.EV]).abs()
    R["coastal"]["nearest_vs_alongshore_abs_diff_ft"] = {ev: round(float(dd[ev].median()), 2) for ev in wl.EV}
    print(f"coastal done, {time.time() - t0:.0f}s", flush=True)

    # rainfall and canal (C-8 and C-9 basins)
    n = wl.nodes(ext)
    rmask = z.subbasin_node.notna().to_numpy()
    rp = pts[rmask]
    zr = z[rmask].reset_index(drop=True)
    gr = ground[rmask]
    bfe_mask_r = (zr.zone27.isin(["AE", "AH"]) & zr.zone27_source.isin(RAIN_SRC)).to_numpy()
    meth_r = {"nearest": wl.rain_nearest(rp, n), "subbasin": wl.rain_subbasin(rp, n, zr.subbasin_node.to_numpy()),
              "idw3": wl.rain_idw(rp, n)}
    R["rain"] = {"buildings": int(rmask.sum()), "nodes_with_levels": len(n),
                 "subbasins_with_buildings": int(zr.subbasin_node.nunique()),
                 "own_subbasin_node_used": int((meth_r["subbasin"].node_source == "own_subbasin").sum()),
                 "methods": {}}
    for k, m in meth_r.items():
        R["rain"]["methods"][k] = check(m.p01.to_numpy(), zr, gr, bfe_mask_r, sfha[rmask], minimal[rmask].to_numpy())

    # buildings outside both: 1% zone with a base flood elevation but no multi-frequency levels
    other = ~cmask & ~rmask
    R["outside_both"] = {"buildings": int(other.sum()),
                         "in_1pct_zone": int((other & sfha).sum()),
                         "by_zone": z[other].zone27.fillna("none").value_counts().to_dict(),
                         "by_source_in_1pct_zone": z[other & sfha].zone27_source.fillna("none").value_counts().to_dict()}
    # 2009 against 2027 base flood elevations
    both = b.fema_bfe_ft_navd88.notna() & z.bfe27_ft.notna()
    d = (z.bfe27_ft - b.fema_bfe_ft_navd88)[both]
    R["bfe_2027_minus_2009_ft"] = {"buildings": int(both.sum()), "median": round(float(d.median()), 2),
                                   "p10": round(float(d.quantile(.1)), 2), "p90": round(float(d.quantile(.9)), 2)}
    R["sfha_2009_vs_2027"] = pd.crosstab(b.fema_zone.isin(["A", "AE", "AH", "AO", "VE"]), sfha).to_dict()
    R["seconds"] = round(time.time() - t0)
    (OUT / "water_level_methods.json").write_text(json.dumps(R, indent=2, default=str))
    print(json.dumps(R, indent=1, default=str))


if __name__ == "__main__":
    main()
