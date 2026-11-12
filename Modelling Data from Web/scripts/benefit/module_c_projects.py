"""Module C: project effects as attribute changes (prompt 28 Part 2, spec Module C).

    /Users/.../Climate-Resilience---Miami-Dade/.venv/bin/python -I scripts/benefit/module_c_projects.py

    losses_avoided = EYD_baseline - EYD_with_project

Only buildings inside the project's influence zone are recomputed (Module A
and B for those rows only, using module_b_eyd.compute).

Seawall or surge barrier: the user gives an alignment (a line, lon/lat) and a
crest height (ft NAVD88).
- "Behind the alignment": the straight line from the building to its nearest
  point on the coastal shoreline (the FEMA transect baseline, the line the
  coastal study measures from, stored by Module A) crosses the wall, within
  a few metres. So the wall stands between the building and the water it
  would flood from. Buildings more than max_distance_to_shore_m from the
  shoreline are not affected. Water that goes around the ends is not
  stopped: buildings whose line to the shore misses the wall stay exposed.
- "Low-lying": ground below the crest.
- For those buildings, the coastal water level is removed for every storm
  whose coastal level (with sea level rise) is below the crest. Storms that
  overtop the crest keep their full depth. Rainfall and canal flooding is
  not changed.
Building elevation: the selected buildings' first floor is raised by X ft.
Pump or drainage upgrade, buyout and green stormwater: placeholders until
rainfall depths and drainage basins exist countywide.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer
from shapely import LineString, intersects, linestrings
from shapely.ops import transform

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
import module_b_eyd as mb  # noqa: E402

CONFIG = mb.CONFIG
TO_UTM = Transformer.from_crs("EPSG:4326", "EPSG:26917", always_xy=True)


class Model:
    """Holds the precomputed Module A and B tables; each project call reruns only affected rows."""

    def __init__(self):
        t = time.time()
        self.A = mb.load_a()
        self.B = pd.read_parquet(paths.MODULE_B_PARQUET, columns=["fd_id", "eyd_low", "eyd_mid", "eyd_high"])
        assert (self.A.fd_id.to_numpy() == self.B.fd_id.to_numpy()).all()
        self.cur = mb.load_curves()
        self.load_seconds = round(time.time() - t, 1)

    def _result(self, rows, scen, extra, t0, sub=None, slr=0.0):
        if slr:
            # baseline for the same rows under the same sea level rise
            base = mb.compute(sub, self.cur, slr=slr)[["eyd_low", "eyd_mid", "eyd_high"]]
        else:
            base = self.B.loc[rows, ["eyd_low", "eyd_mid", "eyd_high"]]
        avoided = {c: float((base[f"eyd_{c}"].to_numpy() - scen[f"eyd_{c}"].to_numpy()).sum()) for c in ("low", "mid", "high")}
        per = pd.DataFrame({"fd_id": self.A.fd_id.to_numpy()[rows], "eyd_mid_before": base.eyd_mid.to_numpy(),
                            "eyd_mid_after": scen.eyd_mid.to_numpy()})
        return {"buildings_affected": int(len(rows)),
                "buildings_with_damage_before": int((base.eyd_mid > 0).sum()),
                "eyd_baseline": {c: float(base[f"eyd_{c}"].sum()) for c in ("low", "mid", "high")},
                "losses_avoided_per_year": avoided, "seconds": round(time.time() - t0, 2), **extra}, per

    def seawall(self, line_lonlat, crest_ft, slr=0.0):
        """line_lonlat: [(lon, lat), ...]; crest_ft: crest elevation, ft NAVD88."""
        t0 = time.time()
        cfg = CONFIG["projects"]["seawall"]
        wall = transform(TO_UTM.transform, LineString(line_lonlat))
        A = self.A
        # candidates: within reach of the wall, coastal level present, ground below the crest
        x, y = A.x_utm.to_numpy(), A.y_utm.to_numpy()
        minx, miny, maxx, maxy = wall.buffer(cfg["max_distance_to_shore_m"]).bounds
        coastal = np.zeros(len(A), bool)
        for name in mb.COASTAL:
            coastal |= A[f"wse_{name}_p002"].notna().to_numpy()
        cand = np.flatnonzero((x >= minx) & (x <= maxx) & (y >= miny) & (y <= maxy) & coastal &
                              (A.shore_dist_m.to_numpy() <= cfg["max_distance_to_shore_m"]) &
                              (A.ground_elev_ft_navd88.to_numpy() < crest_ft))
        segs = linestrings(np.stack([np.c_[x[cand], y[cand]], np.c_[A.shore_x.to_numpy()[cand], A.shore_y.to_numpy()[cand]]], axis=1))
        behind = intersects(segs, wall.buffer(cfg["snap_tolerance_m"]))
        rows = cand[behind]
        sub = A.iloc[rows].reset_index(drop=True)

        def off(ev, s):
            lv = np.full(len(sub), -np.inf)
            for name in mb.COASTAL:
                lv = np.fmax(lv, np.nan_to_num(sub[f"wse_{name}_{ev}"].to_numpy(float), nan=-np.inf) + s)
            return lv < crest_ft          # wall holds: coastal water removed for this storm

        scen = mb.compute(sub, self.cur, slr=slr, coastal_off=off)
        held = {ev: int(off(ev, slr).sum()) for ev in mb.EVENTS}
        return self._result(rows, scen, {"wall_length_m": round(wall.length), "crest_ft_navd88": crest_ft,
                                         "candidates_checked": int(len(cand)), "storms_held_by_wall_buildings": held,
                                         "sea_level_rise_ft": slr}, t0, sub, slr)

    def elevate(self, fd_ids, raise_ft=None):
        t0 = time.time()
        raise_ft = CONFIG["projects"]["elevation"]["default_raise_ft"] if raise_ft is None else raise_ft
        rows = np.flatnonzero(self.A.fd_id.isin(set(fd_ids)).to_numpy())
        sub = self.A.iloc[rows].reset_index(drop=True)
        scen = mb.compute(sub, self.cur, ffe_add=raise_ft)
        return self._result(rows, scen, {"raise_ft": raise_ft}, t0)

    def pump_drainage(self, *a, **k):
        raise NotImplementedError("Placeholder: needs rainfall depth grids and drainage basin polygons countywide "
                                  "(config projects.pump_drainage). Only the C-8 and C-9 basins have rainfall levels now.")

    def buyout(self, *a, **k):
        raise NotImplementedError("Placeholder (prompt 28): to be built with the drainage and rainfall project types.")

    def green_stormwater(self, *a, **k):
        raise NotImplementedError("Placeholder: needs rainfall depth grids and sub-basin polygons.")


def pick_examples(M):
    """Example 1: a 1.5 km seawall on the shoreline where the most buildings take coastal damage.
    Example 2: the tract with the highest single-family EYD; elevate its single-family homes that flood
    above the floor in the 1% storm."""
    from shapely.ops import substring
    import water_levels as wl
    A, B = M.A, M.B
    base = wl.read(paths.FIRM_2027_EXTRACT, "S_Tsct_Basln")
    coastal_hit = A.wse_coastal_p01.notna().to_numpy() & (B.eyd_mid.to_numpy() > 0) & (A.shore_dist_m.to_numpy() < 1000)
    xs, ys = A.shore_x.to_numpy()[coastal_hit], A.shore_y.to_numpy()[coastal_hit]
    best = None
    for _, r in base.iterrows():
        g = r.geometry
        from shapely import points as _pts
        on = g.distance(_pts(np.c_[xs, ys])) < 1.0
        if on.sum() < 50:
            continue
        st = np.array([g.project(p) for p in _pts(np.c_[xs[on], ys[on]])])
        L = 1500.0
        for s0 in np.arange(0, max(g.length - L, 1), 100):
            k = ((st >= s0) & (st <= s0 + L)).sum()
            if best is None or k > best[0]:
                best = (k, g, s0, r.WTR_NM, r.TBASELN_ID)
    k, g, s0, water, bid = best
    seg = substring(g, s0, min(s0 + 1500, g.length))
    to_ll = Transformer.from_crs("EPSG:26917", "EPSG:4326", always_xy=True)
    line = [to_ll.transform(*c) for c in seg.coords]
    sf = A.occtype.str.startswith("RES1").to_numpy()
    tr = pd.Series(B.eyd_mid.to_numpy()[sf]).groupby(A.GEOID_tract.to_numpy()[sf]).sum().sort_values(ascending=False)
    tract = tr.index[0]
    w1, _ = mb.levels(A, "p01")
    sel = sf & (A.GEOID_tract.to_numpy() == tract) & (w1 > A.ffe_ft_navd88.to_numpy())
    return {"line": line, "water": water, "baseline_id": int(bid), "buildings_on_stretch": int(k)}, \
        {"tract": tract, "fd_ids": A.fd_id.to_numpy()[sel].tolist()}


def place_of(lon, lat):
    import geopandas as gpd
    pl = gpd.read_file(f"zip://{paths.BOUNDARY_DIR / 'tl_2024_12_place.zip'}").to_crs(4326)
    m = pl[pl.contains(gpd.points_from_xy([lon], [lat], crs=4326)[0])]
    return m.NAME.iloc[0] if len(m) else "unincorporated Miami-Dade"


def main():
    M = Model()
    ex1, ex2 = pick_examples(M)
    mid = ex1["line"][len(ex1["line"]) // 2]
    R = {"model_load_seconds": M.load_seconds}
    for crest in (6.0, 8.0):
        r, per = M.seawall(ex1["line"], crest)
        R[f"seawall_crest_{crest:g}ft"] = r
    r3, _ = M.seawall(ex1["line"], 8.0, slr=2.0)
    R["seawall_crest_8ft_with_2ft_slr"] = r3
    R["seawall_example"] = {"place_at_midpoint": place_of(*mid), "water_body": ex1["water"],
                            "line_lonlat": [[round(a, 6), round(b, 6)] for a, b in ex1["line"]],
                            "buildings_with_coastal_damage_on_stretch": ex1["buildings_on_stretch"]}
    for ft in (2.0, 3.0, 5.0):
        r, per = M.elevate(ex2["fd_ids"], ft)
        R[f"elevate_{ft:g}ft"] = r
    A = M.A[M.A.GEOID_tract == ex2["tract"]]
    R["elevation_example"] = {"tract": ex2["tract"], "place": place_of(float(A.lon.median()), float(A.lat.median())),
                              "homes_selected": len(ex2["fd_ids"]),
                              "single_family_homes_in_tract": int(A.occtype.str.startswith("RES1").sum())}
    for name in ("pump_drainage", "buyout", "green_stormwater"):
        try:
            getattr(M, name)()
        except NotImplementedError as e:
            R[f"{name}_status"] = str(e)
    (paths.OUT_BENEFIT / "spec_alignment" / "module_c_examples.json").write_text(json.dumps(R, indent=2, default=str))
    print(json.dumps(R, indent=1, default=str))


if __name__ == "__main__":
    main()
