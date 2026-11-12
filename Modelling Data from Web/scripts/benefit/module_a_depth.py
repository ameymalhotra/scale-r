"""Module A: flood depth above the first floor at every building (prompt 28 Part 2, spec Module A).

    /Users/.../Climate-Resilience---Miami-Dade/.venv/bin/python -I scripts/benefit/module_a_depth.py

For every building and every storm frequency in module_config.json:
    depth_above_floor = max(0, water_surface_elev - first_floor_elev)
Water surface elevations (ft NAVD88) come from the sources in the config:
- coastal: FEMA 2027 coastal still-water levels, carried to buildings in the
  coastal study area by the chosen method (D-170);
- rain: FEMA 2027 XP-SWMM levels in the C-8 and C-9 basins (D-170);
- map: FEMA 2027 base flood elevation (1%) where neither of the above exists;
  0.2% copies the 1% level (lower bound, D-137).
Extent cap (config "cap_to_fema_extent", D-170): a source's level only
reaches buildings inside FEMA's 2027 mapped extent for that storm: the 1%
zone (A, AE, AH, AO, VE) for the 1% storm and more frequent ones, and the 1%
zone plus the 0.2% zone (shaded X) for the 0.2% storm. Without it, filling
the land to the water level floods buildings FEMA maps as outside the
floodplain. With sea level rise the cap is widened: buildings in NOAA's
sea level rise inundation area for that rise also count as inside.
Sea level rise is added to the coastal levels only (config). The 2009
effective map is carried as a comparison source. NHC surge maps stay in the
buildings table as worst-case event scenarios (not used here).

Writes data/processed/benefit/module_a_depth.parquet keyed by fd_id:
- ground and first-floor elevation, ffe_estimated, found_ht, occupancy fields
  needed by Module B;
- wse_<source>_<event>: water level by source (NaN where the source does not
  reach the building);
- shore_x, shore_y: nearest point on the coastal transect baseline (for the
  seawall "behind the alignment" test in Module C);
- depth_<event>_slr<k>: depth above the first floor from the highest source,
  0 where dry (no blanks).
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
import water_levels as wl  # noqa: E402

CONFIG = json.loads((Path(__file__).resolve().parent / "module_config.json").read_text())
EVENTS = [e["name"] for e in CONFIG["events"]]
KEEP = ["fd_id", "bid", "GEOID_tract", "GEOID_bg", "lon", "lat", "occtype", "found_type", "found_ht", "num_story",
        "sqft", "st_damcat", "val_struct", "val_cont", "fullrep", "residents_night", "resunits", "jv_alloc",
        "ground_elev_ft_navd88", "ground_elev_ft_noaa", "ffe_ft_navd88", "ffe_estimated", "ffe_rule",
        "year_built_used", "fema_zone", "fema_bfe_ft_navd88", "nfip_cid", "slr_1ft", "slr_2ft", "slr_3ft"]


ANCHOR_KIND = {}


def source_levels(name, cfg, b, pts, z):
    """Water levels (n x events) for one source; NaN where it does not apply."""
    ext = paths.FIRM_2027_EXTRACT
    out = pd.DataFrame(np.nan, index=range(len(b)), columns=EVENTS)
    if cfg["type"] == "fema_transects":
        m = z.zone27_source.isin(cfg["zone_sources"]).to_numpy()
        t = wl.transects(ext)
        if cfg["method"] == "anchored":
            v = wl.coastal_anchored(pts[m], t, z[m].reset_index(drop=True),
                                    b.ground_elev_ft_navd88.to_numpy()[m], ext)
            ANCHOR_KIND[name] = pd.Series(v.anchor_kind.to_numpy(), index=np.flatnonzero(m))
        elif cfg["method"] == "alongshore":
            v = wl.coastal_alongshore(pts[m], t, ext)
        else:
            v = wl.coastal_nearest(pts[m], t)
        out.loc[m, cfg["events"]] = v[cfg["events"]].to_numpy()
    elif cfg["type"] == "fema_nodes":
        m = z.subbasin_node.notna().to_numpy()
        n = wl.nodes(ext)
        if cfg["method"] == "subbasin":
            v = wl.rain_subbasin(pts[m], n, z.subbasin_node.to_numpy()[m])
        elif cfg["method"] == "idw3":
            v = wl.rain_idw(pts[m], n)
        else:
            v = wl.rain_nearest(pts[m], n)
        out.loc[m, cfg["events"]] = v[cfg["events"]].to_numpy()
    elif cfg["type"] == "fema_zone_bfe":
        lvl = z.bfe27_ft.to_numpy().copy()
        ao = z.ao_depth27_ft.notna().to_numpy()
        lvl[ao] = b.ground_elev_ft_navd88.to_numpy()[ao] + z.ao_depth27_ft.to_numpy()[ao]
        out["p01"] = lvl
    elif cfg["type"] == "buildings_column":
        out["p01"] = b[cfg["column"]].to_numpy()
    elif cfg["type"] == "raster":
        raise NotImplementedError("raster sources (depth grids) plug in here once the files exist")
    for dst, src in cfg.get("rare_event_copy", {}).items():
        out[dst] = out[src]
    return out


def main():
    t0 = time.time()
    b = pd.read_parquet(paths.BUILDINGS_PARQUET, columns=KEEP).reset_index(drop=True)
    z = pd.read_parquet(paths.FEMA2027_ZONES_PARQUET)
    assert (z.fd_id.to_numpy() == b.fd_id.to_numpy()).all(), "zones table out of order; rerun compare_water_levels.py"
    pts, ex, ny = wl.points(b)
    A = b.copy()
    A["zone27"] = z.zone27.to_numpy()
    A["bfe27_ft"] = z.bfe27_ft.to_numpy()
    A["zone27_source"] = z.zone27_source.to_numpy()
    A["basin"] = z.basin.to_numpy()
    A["zone27_subtype"] = z.zone27_subtype.to_numpy()
    A["x_utm"], A["y_utm"] = ex, ny

    lv = {}
    for name, cfg in CONFIG["sources"].items():
        lv[name] = source_levels(name, cfg, b, pts, z)
        print(f"{name}: {lv[name].notna().any(axis=1).sum():,} buildings, {time.time() - t0:.0f}s", flush=True)
    # the map source only where neither multi-frequency source reaches
    covered = lv["coastal"].notna().any(axis=1) | lv["rain"].notna().any(axis=1)
    lv["map"].loc[covered] = np.nan
    # FEMA 2027 mapped extent per storm (D-170)
    sfha = z.zone27.isin(["A", "AE", "AH", "AO", "VE"]).to_numpy()
    x02 = (z.zone27.eq("X") & z.zone27_subtype.fillna("").str.startswith("0.2 PCT")).to_numpy()
    extent = {ev: (sfha | x02) if ev == "p002" else sfha for ev in EVENTS}
    for name, cfg in CONFIG["comparison_sources"].items():
        lv[name] = source_levels(name, cfg, b, pts, z)
    capped_names = [n for n, c in {**CONFIG["sources"], **CONFIG["comparison_sources"]}.items()
                    if c["type"] != "buildings_column"]
    uncapped = {}
    for name in capped_names:
        for ev in EVENTS:
            v = lv[name][ev].to_numpy(float).copy()
            uncapped[(name, ev)] = v.copy()
            if CONFIG.get("cap_to_fema_extent", True):
                v[~extent[ev]] = np.nan
            lv[name][ev] = v
    for name, v in lv.items():
        for ev in EVENTS:
            A[f"wse_{name}_{ev}"] = v[ev].to_numpy(np.float32)
    for name in [n for n in capped_names if {**CONFIG["sources"], **CONFIG["comparison_sources"]}[n]["kind"] == "coastal"]:
        for ev in EVENTS:
            A[f"wse_{name}_uncapped_{ev}"] = uncapped[(name, ev)].astype(np.float32)

    # nearest point on the coastal transect baseline (shoreline), for the seawall test
    from shapely.strtree import STRtree
    base = wl.read(paths.FIRM_2027_EXTRACT, "S_Tsct_Basln")
    tree = STRtree(base.geometry.values)
    idx = tree.query_nearest(pts, all_matches=False)
    order = np.argsort(idx[0])
    bj = idx[1][order]
    sx = np.empty(len(b))
    sy = np.empty(len(b))
    for k in np.unique(bj):
        m = np.flatnonzero(bj == k)
        g = base.geometry.iloc[k]
        q = [g.interpolate(g.project(p)) for p in pts[m]]
        sx[m] = [p.x for p in q]
        sy[m] = [p.y for p in q]
    A["shore_x"], A["shore_y"] = sx, sy
    for name, k in ANCHOR_KIND.items():
        col = np.full(len(A), "", dtype=object)
        col[k.index.to_numpy()] = k.to_numpy()
        A[f"anchor_{name}"] = col
    A["shore_dist_m"] = np.hypot(sx - ex, sy - ny)

    ffe = A.ffe_ft_navd88.to_numpy()
    main_src = list(CONFIG["sources"])
    unc_wet = {}
    for ev in EVENTS:
        w = np.full(len(A), -np.inf)
        for name in main_src:
            w = np.fmax(w, np.nan_to_num(uncapped[(name, ev)], nan=-np.inf))
        unc_wet[ev] = int((w > ffe).sum())
    for s in CONFIG["sea_level_rise_ft"]:
        for ev in EVENTS:
            w = np.full(len(A), -np.inf)
            for name in main_src:
                v = A[f"wse_{name}_{ev}"].to_numpy(float)
                if name in CONFIG["sea_level_rise_applies_to"] and s:
                    wide = A[f"slr_{s}ft"].to_numpy().astype(bool)
                    v = np.where(wide, A[f"wse_{name}_uncapped_{ev}"].to_numpy(float), v) + s
                w = np.fmax(w, np.nan_to_num(v, nan=-np.inf))
            A[f"depth_{ev}_slr{s}"] = np.clip(w - ffe, 0, None).astype(np.float32)
    A.to_parquet(paths.MODULE_A_PARQUET, index=False)

    dep = A[[f"depth_{ev}_slr0" for ev in EVENTS]]
    S = {"buildings": len(A), "seconds": round(time.time() - t0),
         "buildings_by_source": {k: int(v.notna().any(axis=1).sum()) for k, v in lv.items()},
         "anchor_kinds": {k: v.value_counts().to_dict() for k, v in ANCHOR_KIND.items()},
         "blank_depths": int(A.filter(like="depth_").isna().sum().sum()),
         "buildings_wet_above_floor_slr0_without_extent_cap": unc_wet,
         "buildings_wet_above_floor_slr0": {ev: int((A[f"depth_{ev}_slr0"] > 0).sum()) for ev in EVENTS},
         "buildings_wet_above_floor_slr3": {ev: int((A[f"depth_{ev}_slr3"] > 0).sum()) for ev in EVENTS},
         "median_depth_where_wet_slr0_ft": {ev: round(float(dep[f"depth_{ev}_slr0"][dep[f"depth_{ev}_slr0"] > 0].median()), 2)
                                           for ev in EVENTS if (dep[f"depth_{ev}_slr0"] > 0).any()}}
    (paths.OUT_BENEFIT / "spec_alignment" / "module_a_summary.json").write_text(json.dumps(S, indent=2))
    print(json.dumps(S, indent=1))


if __name__ == "__main__":
    main()
