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
- Waterway rule (D-202): the building's nearest open water must be that
  coastal shoreline. If a canal, creek, river or inner waterway (FEMA 2027
  water lines, build_water_distance.py) is nearer, water reaches it another
  way and it is not protected. Safety cap: within max_distance_from_wall_m
  (1 km) of the wall.
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
from shapely import LineString, distance, linestrings, points
from shapely.ops import transform

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
import module_b_eyd as mb  # noqa: E402

CONFIG = mb.CONFIG
TO_UTM = Transformer.from_crs("EPSG:4326", "EPSG:26917", always_xy=True)


def building_key(A):
    """One integer per physical building: records at exactly the same NSI point (D-218).
    The NSI splits a mixed-use building into one record per occupancy type, all at the same point and with the same
    footprint id. bid is not used: 47,994 parcel-based records have a blank bid, and 152 bids hold separate footprints."""
    return pd.factorize(pd.MultiIndex.from_arrays([A.x_utm.to_numpy(), A.y_utm.to_numpy()]))[0]


def building_reasons(t):
    """One reason per building from the per-record reasons of seawall_reasons (D-218): protected if any of its records
    is protected; otherwise the reason its records share. Returns (per-building Series, buildings whose other
    records disagree)."""
    g = t.groupby("building").reason
    prot = g.apply(lambda v: (v == "protected").any())
    first = g.first()
    mixed = g.nunique() > 1
    out = first.where(~prot, "protected")
    return out, int((mixed & ~prot).sum())


def frequent(L):
    """Expected yearly damage from the storms between 10% and 2% only (Module D sensitivity)."""
    L = np.maximum.accumulate(L, axis=1)
    return (0.5 * (L[:, :-1] + L[:, 1:]) * (mb.P[:-1] - mb.P[1:]))[:, :2].sum(1)


class Model:
    """Holds the precomputed Module A and B tables; each project call reruns only affected rows."""

    def __init__(self):
        t = time.time()
        self.A = mb.load_a()
        self.B = pd.read_parquet(paths.MODULE_B_PARQUET, columns=["fd_id", "eyd_low", "eyd_mid", "eyd_high", "eyd_tail_mid"] +
                                 [f"loss_{e}_mid" for e in mb.EVENTS])
        assert (self.A.fd_id.to_numpy() == self.B.fd_id.to_numpy()).all()
        self.cur = mb.load_curves()
        iw = pd.read_parquet(paths.INNER_WATER_PARQUET, columns=["fd_id", "inner_water_dist_m"]).set_index("fd_id").inner_water_dist_m
        self.inner_water = iw.reindex(self.A.fd_id).to_numpy(float)
        # One physical building per NSI point (D-218): the NSI splits a mixed-use building into one record per use
        # (occupancy type), all at the same point. Counts labelled "buildings" count these; dollars stay per record.
        self.bldg = building_key(self.A)
        self.bldg_of = pd.Series(self.bldg, index=self.A.fd_id.to_numpy())
        self.load_seconds = round(time.time() - t, 1)

    def n_buildings(self, fd_ids):
        """Physical buildings among these NSI records (D-218)."""
        return int(self.bldg_of.reindex(pd.Index(fd_ids)).dropna().nunique())

    def _result(self, rows, scen, extra, t0, sub=None, slr=0.0):
        lcols = [f"loss_{e}_mid" for e in mb.EVENTS]
        if slr:
            # baseline for the same rows under the same sea level rise
            base = mb.compute(sub, self.cur, slr=slr, keep_losses=True)[["eyd_low", "eyd_mid", "eyd_high", "eyd_tail_mid"] + lcols]
        else:
            base = self.B.loc[rows, ["eyd_low", "eyd_mid", "eyd_high", "eyd_tail_mid"] + lcols]
        avoided = {c: float((base[f"eyd_{c}"].to_numpy() - scen[f"eyd_{c}"].to_numpy()).sum()) for c in ("low", "mid", "high")}
        b = self.bldg[rows]
        red = base.eyd_mid.to_numpy() - scen.eyd_mid.to_numpy()
        per = pd.DataFrame({"fd_id": self.A.fd_id.to_numpy()[rows], "building": b, "eyd_mid_before": base.eyd_mid.to_numpy(),
                            "eyd_mid_after": scen.eyd_mid.to_numpy(),
                            "eyd_tail_before": base.eyd_tail_mid.to_numpy(), "eyd_tail_after": scen.eyd_tail_mid.to_numpy(),
                            "eyd_freq_before": frequent(base[lcols].to_numpy()), "eyd_freq_after": frequent(scen[lcols].to_numpy())})
        return {"buildings_affected": int(pd.unique(b).size), "records_affected": int(len(rows)),
                "buildings_with_damage_before": int(pd.unique(b[base.eyd_mid.to_numpy() > 0]).size),
                "records_with_damage_before": int((base.eyd_mid > 0).sum()),
                # a building is protected if any of its records has damage avoided > 0 (D-218)
                "buildings_protected": int(pd.unique(b[red > 0]).size), "records_protected": int((red > 0).sum()),
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
        # the line to the shore passes within snap_tolerance_m of the wall (exact distance; D-204, was a buffer polygon)
        behind = distance(segs, wall) <= cfg["snap_tolerance_m"]
        rows = cand[behind]
        # waterway rule and 1 km cap (D-202)
        water_ok = np.ones(len(rows), bool)
        if cfg.get("inner_water_rule"):
            # compared in single precision, as in the browser export (D-204)
            water_ok = ~(self.inner_water[rows].astype(np.float32) < A.shore_dist_m.to_numpy()[rows].astype(np.float32))
        near = np.ones(len(rows), bool)
        if cfg.get("max_distance_from_wall_m"):
            near = wall.distance(points(np.c_[x[rows], y[rows]])) <= cfg["max_distance_from_wall_m"]
        removed = {"behind_the_wall_before_rules": int(len(rows)), "removed_by_inner_water": int((~water_ok).sum()),
                   "removed_by_1km_cap_only": int((water_ok & ~near).sum())}
        rows = rows[water_ok & near]
        sub = A.iloc[rows].reset_index(drop=True)

        def off(ev, s):
            lv = np.full(len(sub), -np.inf)
            for name in mb.COASTAL:
                lv = np.fmax(lv, np.nan_to_num(sub[f"wse_{name}_{ev}"].to_numpy(float), nan=-np.inf) + s)
            return lv < crest_ft          # wall holds: coastal water removed for this storm

        scen = mb.compute(sub, self.cur, slr=slr, coastal_off=off, keep_losses=True)
        bsub = self.bldg[rows]
        held = {ev: int(pd.unique(bsub[off(ev, slr)]).size) for ev in mb.EVENTS}   # buildings (D-218)
        return self._result(rows, scen, {"wall_length_m": round(wall.length), "crest_ft_navd88": crest_ft,
                                         "candidates_checked": int(len(cand)), "storms_held_by_wall_buildings": held,
                                         "sea_level_rise_ft": slr, **removed}, t0, sub, slr)

    REASONS = ["protected", "overtopped", "inner_water", "bay_beyond_ends", "beyond_1km", "rain_only"]

    @property
    def wet(self):
        """Buildings wet (water above ground) in at least one storm today: the What-If export set."""
        if not hasattr(self, "_wet"):
            g = self.A.ground_elev_ft_navd88.to_numpy(float)
            w = np.zeros(len(self.A), bool)
            cw = np.zeros(len(self.A), bool)
            for ev in mb.EVENTS:
                lv, _ = mb.levels(self.A, ev)
                w |= lv > g
                c = np.nan_to_num(self.A[f"wse_coastal_{ev}"].to_numpy(float), nan=-np.inf)
                cw |= c > g
            self._wet, self._coastal_wet = w, cw
        return self._wet

    def seawall_reasons(self, line_lonlat, crest_ft):
        """Why each flooding building near a wall is or is not protected (D-204). One reason per building, in order:
        rain_only: no coastal water above its ground in any storm (it floods only from rainfall, canals or the map
          level, which a seawall does not change);
        inner_water: its nearest open water is a canal, creek, river or inner waterway, not the coastal shoreline;
        bay_beyond_ends: its nearest water is the coastal shoreline, but its line to the shore misses the wall;
        beyond_1km: behind the wall but more than max_distance_from_wall_m from it;
        protected: behind the wall and its yearly damage (middle) goes down;
        overtopped: behind the wall, but every storm that floods it goes over the crest (or its ground is above it).
        Shown: flooding buildings within max_distance_from_wall_m of the wall, plus those beyond it that would
        otherwise count. Returns (table, Model.seawall result)."""
        r, per = self.seawall(line_lonlat, crest_ft)
        cfg = CONFIG["projects"]["seawall"]
        wall = transform(TO_UTM.transform, LineString(line_lonlat))
        A = self.A
        wet = self.wet
        x, y = A.x_utm.to_numpy(), A.y_utm.to_numpy()
        reach = cfg["max_distance_to_shore_m"]
        cap = cfg.get("max_distance_from_wall_m") or np.inf
        minx, miny, maxx, maxy = wall.buffer(reach).bounds
        idx = np.flatnonzero(wet & (x >= minx) & (x <= maxx) & (y >= miny) & (y <= maxy))
        dw = distance(points(np.c_[x[idx], y[idx]]), wall)
        sx, sy = A.shore_x.to_numpy()[idx], A.shore_y.to_numpy()[idx]
        has_shore = np.isfinite(sx) & np.isfinite(sy)
        segs = linestrings(np.stack([np.c_[x[idx], y[idx]], np.c_[np.nan_to_num(sx), np.nan_to_num(sy)]], axis=1))
        cross = has_shore & (distance(segs, wall) <= cfg["snap_tolerance_m"])
        sd = A.shore_dist_m.to_numpy()[idx].astype(np.float32)
        iw = self.inner_water[idx].astype(np.float32)
        inner = iw < sd
        coastal_wet = self._coastal_wet[idx]
        behind = cross & (sd <= reach)
        red = per.set_index("fd_id")
        reduced = (red.eyd_mid_before - red.eyd_mid_after).reindex(A.fd_id.to_numpy()[idx]).fillna(0).to_numpy() > 0
        reason = np.select([~coastal_wet, inner, ~behind, dw > cap, reduced],
                           ["rain_only", "inner_water", "bay_beyond_ends", "beyond_1km", "protected"], "overtopped")
        show = (dw <= cap) | (reason == "beyond_1km")
        t = pd.DataFrame({"fd_id": A.fd_id.to_numpy()[idx], "building": self.bldg[idx], "reason": reason, "dist_to_wall_m": dw, "shore_dist_m": sd,
                          "inner_water_dist_m": iw})[show].reset_index(drop=True)
        return t, r

    def elevate(self, fd_ids, raise_ft=None):
        t0 = time.time()
        raise_ft = CONFIG["projects"]["elevation"]["default_raise_ft"] if raise_ft is None else raise_ft
        rows = np.flatnonzero(self.A.fd_id.isin(set(fd_ids)).to_numpy())
        sub = self.A.iloc[rows].reset_index(drop=True)
        scen = mb.compute(sub, self.cur, ffe_add=raise_ft, keep_losses=True)
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
            inside = (st >= s0) & (st <= s0 + L)
            k = inside.sum()   # the stretch is still chosen by records, so the example (and its dollars) do not change (D-218)
            if best is None or k > best[0]:
                best = (k, g, s0, r.WTR_NM, r.TBASELN_ID, np.flatnonzero(coastal_hit)[on][inside])
    k, g, s0, water, bid, hit_rows = best
    seg = substring(g, s0, min(s0 + 1500, g.length))
    to_ll = Transformer.from_crs("EPSG:26917", "EPSG:4326", always_xy=True)
    line = [to_ll.transform(*c) for c in seg.coords]
    sf = A.occtype.str.startswith("RES1").to_numpy()
    tr = pd.Series(B.eyd_mid.to_numpy()[sf]).groupby(A.GEOID_tract.to_numpy()[sf]).sum().sort_values(ascending=False)
    tract = tr.index[0]
    w1, _ = mb.levels(A, "p01")
    sel = sf & (A.GEOID_tract.to_numpy() == tract) & (w1 > A.ffe_ft_navd88.to_numpy())
    return {"line": line, "water": water, "baseline_id": int(bid), "buildings_on_stretch": int(pd.unique(M.bldg[hit_rows]).size),
            "records_on_stretch": int(k)}, \
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
                            "buildings_with_coastal_damage_on_stretch": ex1["buildings_on_stretch"],
                            "records_with_coastal_damage_on_stretch": ex1["records_on_stretch"]}
    for ft in (2.0, 3.0, 5.0):
        r, per = M.elevate(ex2["fd_ids"], ft)
        R[f"elevate_{ft:g}ft"] = r
    A = M.A[M.A.GEOID_tract == ex2["tract"]]
    R["elevation_example"] = {"tract": ex2["tract"], "place": place_of(float(A.lon.median()), float(A.lat.median())),
                              "homes_selected": M.n_buildings(ex2["fd_ids"]), "records_selected": len(ex2["fd_ids"]),   # D-218
                              "single_family_homes_in_tract": M.n_buildings(A.fd_id[A.occtype.str.startswith("RES1")]),
                              "single_family_records_in_tract": int(A.occtype.str.startswith("RES1").sum())}
    for name in ("pump_drainage", "buyout", "green_stormwater"):
        try:
            getattr(M, name)()
        except NotImplementedError as e:
            R[f"{name}_status"] = str(e)
    (paths.OUT_BENEFIT / "spec_alignment" / "module_c_examples.json").write_text(json.dumps(R, indent=2, default=str))
    print(json.dumps(R, indent=1, default=str))


if __name__ == "__main__":
    main()
