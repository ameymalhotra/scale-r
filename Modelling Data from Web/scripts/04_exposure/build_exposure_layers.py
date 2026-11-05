"""Stage A of prompt 21: population exposure layers for Miami-Dade.

Counts residents of each tract and block group living on land exposed to sea
level rise, storm surge and surface heat. Data preparation and description
only: nothing is joined to the analysis tables or correlated with investment.

Population surface (reused, not rebuilt): population_surface.load_blocks, the
  same logic as load_blocks in build_population_exposure.py (left unchanged):
  ACS 2020-2024 B01003 block group totals, split across 2020 census blocks in
  proportion to POP20, each block's land = block minus TIGER 2024 areawater.
Core assumption: residents are spread evenly over their block's land, so
  exposed residents in a block = block residents x share of block land exposed.
Blocks are only used to place people; results are reported for block groups
and tracts.

Hazards, all from the original data (never the website PNGs):
  sea level rise  NOAA OCM FL_SE GeoPackage polygons, EPSG:6346 area overlay,
                  same reading/clip/subdivide steps as process_slr.py
                  slr 1, 2, 3, 6 ft (ocean-connected) and low 3 ft (unconnected)
  storm surge     NHC SLOSH MOM v4 (06/2026) high tide GeoTIFFs, raw values as in
                  process_surge.py (255 on land = not inundated, 99 levee kept
                  apart). Categories 1-5, any inundation (class >= 1) and more
                  than 3 ft (class >= 4), plus cat5max: per pixel the deepest
                  class over categories 1-5 (fills the Category 5 hole)
  surface heat    ../output/lst/lst_composite_f.tif (Landsat 8/9 C2 L2 summer
                  2021-2024 median, 30 m); thresholds at the county 75th and
                  95th percentile of land pixels (primary) and 100/105/110 F
                  (sensitivity); population-weighted mean surface temperature

Raster layers use fractional pixel coverage by 4 x 4 supersampling of each
block's land (exactextract is not installed and nothing is downloaded). The
pixel-centre version is computed too, for the county-total comparison. A block
too small to hold any sample takes the value of the pixel under its
representative point.

Checkpoints: output/exposure_checkpoints/, one file per layer, skipped on
restart. Outputs: exposure_tract.csv, exposure_blockgroup.csv, and the run log
output/exposure_layers_log.txt (written by tee from the caller).

Usage: ../.venv/bin/python scripts/build_exposure_layers.py
"""
import gc
import json
import math
import sys
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import shapely
from rasterio.features import rasterize
from rasterio.transform import Affine

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
paths.use("03_physical")
import population_surface  # noqa: E402
import process_slr as pslr  # noqa: E402
import process_surge as psurge  # noqa: E402
from allocation import POP_FILES, assign_municipality, load_population, load_units  # noqa: E402

BASE = paths.ROOT
REPO = paths.REPO
CK = paths.OUT_EXPOSURE_CK
AREA_CRS = "EPSG:6346"
LST_TIF = paths.LST_TIF
VIZ_DATA = paths.VIZ_DATA
OUT = {"tract": paths.EXPOSURE_DIR / "exposure_tract.csv", "bg": paths.EXPOSURE_DIR / "exposure_blockgroup.csv"}
EXPECTED = {"tract": 707, "bg": 1843}

FACTOR = 4          # supersampling per axis for fractional coverage
STRIP = 64          # coarse rows per strip
LOW_POP = 100
CV_LOW = 0.40
HEAT_FIXED = [100.0, 105.0, 110.0]
SLR_KEYS = {"FL_SE_slr_1_0ft": "slr_1ft", "FL_SE_slr_2_0ft": "slr_2ft",
            "FL_SE_slr_3_0ft": "slr_3ft", "FL_SE_slr_6_0ft": "slr_6ft",
            "FL_SE_low_3_0ft": "low_3ft"}
SURGE_VERSIONS = ["cat1", "cat2", "cat3", "cat4", "cat5", "cat5max"]
# surge pixel codes on block land
DRY, SHALLOW, DEEP, LEVEE, HOLE = 0, 1, 2, 3, 4   # HOLE only in the hole layer


def sec(t):
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78, flush=True)


# --------------------------------------------------------------------------
# population surface
# --------------------------------------------------------------------------

def blocks_table():
    path = CK / "blocks.gpkg"
    if path.exists():
        b = gpd.read_file(path)
        print(f"blocks: checkpoint {len(b):,} populated blocks, {b.people.sum():,.0f} residents")
        return b
    sec("POPULATION SURFACE (population_surface.load_blocks, EPSG:6346)")
    blocks, total = population_surface.load_blocks(AREA_CRS)
    b = gpd.GeoDataFrame(
        {"GEOID20": blocks["GEOID20"], "bg": blocks["bg"], "people": blocks["people"],
         "POP20": blocks["POP20"].astype(float), "ALAND20": blocks["ALAND20"].astype(float),
         "full_shape": shapely.equals(blocks["land"].values, blocks.geometry.values)},
        geometry=gpd.GeoSeries(blocks["land"].values, crs=AREA_CRS))
    b["land_m2"] = b.geometry.area
    b.to_file(path, driver="GPKG")
    print(f"  checkpoint written: {path.name}")
    return b


# --------------------------------------------------------------------------
# generic fractional zonal counting on a raster grid
# --------------------------------------------------------------------------

def strip_labels(geoms, tree, tf, width, r0, r1, factor):
    """Fine label grid (block index + 1) for coarse rows r0..r1."""
    ftf = tf * Affine.translation(0, r0) * Affine.scale(1 / factor)
    h, w = (r1 - r0) * factor, width * factor
    x0, y0 = tf * (0, r0)
    x1, y1 = tf * (width, r1)
    box = shapely.box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
    idx = tree.query(box, predicate="intersects")
    if len(idx) == 0:
        return None
    return rasterize(((geoms[i], int(i) + 1) for i in idx), out_shape=(h, w),
                     transform=ftf, fill=0, dtype="int32")


def zonal(geoms, tf, shape, layers, factor, weights=None):
    """Per block cell counts by code for each layer, at `factor` x `factor` samples per pixel.

    layers: {name: (code_array (H, W) int, n_codes)}
    weights: optional {name: float array (H, W)} summed over cells where finite
    Returns counts {name: (n, n_codes) float in pixel units}, sums {name: (n,)},
    nsum {name: (n,)} (cells contributing to each sum), fallback block indices.
    """
    n = len(geoms)
    H, W = shape
    tree = shapely.STRtree(geoms)
    counts = {k: np.zeros((n + 1, c)) for k, (_, c) in layers.items()}
    sums = {k: np.zeros(n + 1) for k in (weights or {})}
    nsum = {k: np.zeros(n + 1) for k in (weights or {})}
    cell = 1.0 / factor ** 2
    for r0 in range(0, H, STRIP):
        r1 = min(r0 + STRIP, H)
        lab = strip_labels(geoms, tree, tf, W, r0, r1, factor)
        if lab is None:
            continue
        fr, fc = np.nonzero(lab)
        if len(fr) == 0:
            continue
        L = lab[fr, fc]
        cr, cc = r0 + fr // factor, fc // factor
        for k, (arr, c) in layers.items():
            code = arr[cr, cc].astype(np.int64)
            counts[k] += np.bincount(L * c + code, minlength=(n + 1) * c).reshape(n + 1, c) * cell
        for k, warr in (weights or {}).items():
            v = warr[cr, cc]
            ok = np.isfinite(v)
            sums[k] += np.bincount(L[ok], weights=v[ok], minlength=n + 1) * cell
            nsum[k] += np.bincount(L[ok], minlength=n + 1) * cell
        del lab, fr, fc, L, cr, cc
    counts = {k: v[1:] for k, v in counts.items()}
    sums = {k: v[1:] for k, v in sums.items()}
    nsum = {k: v[1:] for k, v in nsum.items()}
    # blocks holding no sample: value of the pixel under the representative point
    any_layer = next(iter(counts.values()))
    empty = np.flatnonzero(any_layer.sum(axis=1) == 0)
    if len(empty):
        pts = shapely.point_on_surface(geoms[empty])
        inv = ~tf
        for i, pt in zip(empty, pts):
            col, row = inv * (pt.x, pt.y)
            r, c_ = int(math.floor(row)), int(math.floor(col))
            if not (0 <= r < H and 0 <= c_ < W):
                continue
            for k, (arr, _) in layers.items():
                counts[k][i, int(arr[r, c_])] = 1.0
            for k, warr in (weights or {}).items():
                if np.isfinite(warr[r, c_]):
                    sums[k][i], nsum[k][i] = float(warr[r, c_]), 1.0
    return counts, sums, nsum, empty


def coverage_check(geoms, tf, shape, label):
    H, W = shape
    x0, y0 = tf * (0, H)
    x1, y1 = tf * (W, 0)
    b = shapely.bounds(geoms)
    inside = (b[:, 0] >= x0) & (b[:, 1] >= y0) & (b[:, 2] <= x1) & (b[:, 3] <= y1)
    print(f"  extent check ({label}): {int(inside.sum()):,} of {len(geoms):,} blocks wholly "
          f"inside the raster window; outside: {int((~inside).sum())}", flush=True)
    return int((~inside).sum())


def save_ck(name, df):
    df.to_csv(CK / name, index=False)
    print(f"  checkpoint written: {name}", flush=True)


# --------------------------------------------------------------------------
# sea level rise (polygons)
# --------------------------------------------------------------------------

def wet_area(land, pieces):
    """Area of each block's land covered by the union of inundation pieces.

    Same overlay as process_slr.inundated_area, grouped by sorting so it stays
    fast with ~24,000 blocks.
    """
    tree = shapely.STRtree(pieces)
    ui, fi = tree.query(land, predicate="intersects")
    inter = shapely.intersection(land[ui], pieces[fi])
    order = np.argsort(ui, kind="stable")
    ui, inter = ui[order], inter[order]
    area = np.zeros(len(land))
    if len(ui) == 0:
        return area
    starts = np.flatnonzero(np.r_[True, ui[1:] != ui[:-1]])
    ends = np.r_[starts[1:], len(ui)]
    for s0, e0 in zip(starts, ends):
        g = inter[s0] if e0 - s0 == 1 else shapely.union_all(inter[s0:e0])
        area[ui[s0]] = shapely.area(g)
    return area


def run_slr(blocks):
    todo = {l: k for l, k in SLR_KEYS.items() if not (CK / f"slr_{k}.csv").exists()}
    if not todo:
        print("slr: all checkpoints exist, skipping")
        return
    sec("SEA LEVEL RISE (NOAA polygons on block land, EPSG:6346)")
    _, county_land, county_bbox = pslr.load_land_units()
    shapely.prepare(county_land)
    land = blocks.geometry.values
    area = shapely.area(land)
    for layer, key in todo.items():
        t0 = time.time()
        g = gpd.read_file(pslr.GPKG, layer=layer, bbox=county_bbox, columns=[])
        geoms = g.to_crs(AREA_CRS).geometry.values
        del g
        geoms, _ = pslr.repair(geoms, layer)
        geoms = geoms[shapely.intersects(county_land, geoms)]
        geoms = shapely.intersection(geoms, county_land)
        geoms = pslr.subdivide(geoms[~shapely.is_empty(geoms)])
        wet = wet_area(land, geoms)
        frac = np.clip(wet / np.where(area > 0, area, 1), 0, 1)
        save_ck(f"slr_{key}.csv", pd.DataFrame({"GEOID20": blocks.GEOID20, "frac": frac,
                                                 "wet_m2": wet}))
        print(f"  {layer}: {int((wet > 0).sum()):,} blocks touched, max raw ratio "
              f"{(wet / np.where(area > 0, area, 1)).max():.6f} ({time.time() - t0:.0f}s)", flush=True)
        del geoms
        gc.collect()


# --------------------------------------------------------------------------
# storm surge (raster)
# --------------------------------------------------------------------------

def surge_grid(units=None):
    """The exact reference window process_surge.py used (county land bounds)."""
    units = units or psurge.load_land_units("EPSG:4269")
    bounds = shapely.union_all(units["tract"]["land"].values).bounds
    return psurge.reference_grid(bounds)


def surge_codes(a):
    code = np.full(a.shape, 9, dtype=np.uint8)            # 9 = unexpected
    code[a == psurge.NODATA] = DRY
    code[(a >= 1) & (a <= 3)] = SHALLOW
    code[(a >= 4) & (a <= 21)] = DEEP
    code[a == psurge.LEVEE] = LEVEE
    if (code == 9).any():
        raise SystemExit(f"surge: unexpected values {np.unique(a[code == 9])[:10]}")
    return code


def run_surge(blocks):
    todo = [v for v in SURGE_VERSIONS if not (CK / f"surge_{v}.csv").exists()]
    if not todo:
        print("surge: all checkpoints exist, skipping")
        return
    sec("STORM SURGE (NHC SLOSH MOM, raw values, fractional coverage)")
    ref_tf, ref_shape = surge_grid()
    geoms = blocks.to_crs("EPSG:4269").geometry.values
    coverage_check(geoms, ref_tf, ref_shape, "surge window")
    for v in todo:
        t0 = time.time()
        if v != "cat5max":
            a = psurge.read_window(int(v[-1]), ref_tf, ref_shape)
            layers = {v: (surge_codes(a), 4)}
        else:
            mx = np.zeros(ref_shape, dtype=np.uint8)
            levee = np.zeros(ref_shape, dtype=bool)
            wet_1to4 = np.zeros(ref_shape, dtype=bool)
            for cat in range(1, 6):
                a = psurge.read_window(cat, ref_tf, ref_shape)
                depth = np.where((a >= 1) & (a <= 21), a, 0).astype(np.uint8)
                np.maximum(mx, depth, out=mx)
                levee |= a == psurge.LEVEE
                if cat < 5:
                    wet_1to4 |= depth > 0
                else:
                    hole = (wet_1to4 & (depth == 0) & (a == psurge.NODATA)).astype(np.uint8)
                del a, depth
            merged = np.where(mx > 0, mx, np.where(levee, psurge.LEVEE, psurge.NODATA)).astype(np.uint8)
            np.save(CK / "_cat5max_window.npy", merged)  # reused for the unit land shares
            layers = {v: (surge_codes(merged), 4), "hole": (hole, 2)}
            del mx, levee, wet_1to4, merged
        out = {"GEOID20": blocks.GEOID20}
        for fac, tag in ((FACTOR, "frac"), (1, "ctr")):
            counts, _, _, empty = zonal(geoms, ref_tf, ref_shape, layers, fac)
            c = counts[v]
            tot = c.sum(axis=1)
            d = np.where(tot > 0, tot, np.nan)
            out[f"any_{tag}"] = (c[:, SHALLOW] + c[:, DEEP]) / d
            out[f"over3_{tag}"] = c[:, DEEP] / d
            out[f"levee_{tag}"] = c[:, LEVEE] / d
            out[f"cells_{tag}"] = tot
            if "hole" in counts:
                h = counts["hole"]
                out[f"hole_{tag}"] = h[:, 1] / np.where(h.sum(axis=1) > 0, h.sum(axis=1), np.nan)
            print(f"  {v} [{tag}] blocks on representative-point fallback: {len(empty):,} "
                  f"({blocks.people.values[empty].sum():,.0f} residents)", flush=True)
        save_ck(f"surge_{v}.csv", pd.DataFrame(out))
        print(f"  {v}: {time.time() - t0:.0f}s", flush=True)
        del layers
        gc.collect()


def surge_cat5max_land_shares():
    """Unit land shares for cat5max, pixel-centre on unit land, as process_surge.py."""
    path = CK / "surge_cat5max_landshare.csv"
    if path.exists():
        return pd.read_csv(path, dtype={"GEOID": str})
    sec("SURGE cat5max land shares (tract, block group), process_surge method")
    units = psurge.load_land_units("EPSG:4269")
    ref_tf, ref_shape = surge_grid(units)
    a = np.load(CK / "_cat5max_window.npy")
    rows = []
    for grain in ("tract", "bg"):
        u = units[grain]
        lab = psurge.label_grid(u["land"].values, ref_tf, ref_shape)
        s = psurge.summarise(u["GEOID"].values, psurge.class_counts(lab, a, len(u)), "x")
        rows.append(s[["GEOID", "x_area_share", "x_over3ft_share"]])
    out = pd.concat(rows).rename(columns={"x_area_share": "surge_cat5max_any_land_share",
                                          "x_over3ft_share": "surge_cat5max_over3ft_land_share"})
    save_ck(path.name, out)
    return out


# --------------------------------------------------------------------------
# surface heat (raster)
# --------------------------------------------------------------------------

def county_land_mask(tf, shape, crs):
    units, _, _ = pslr.load_land_units()
    land = units["tract"]["land"]
    g = gpd.GeoSeries(land.values, crs=AREA_CRS).to_crs(crs).values
    return rasterize(((x, 1) for x in g if not x.is_empty), out_shape=shape, transform=tf,
                     fill=0, dtype="uint8").astype(bool), units


def heat_thresholds():
    path = CK / "heat_thresholds.json"
    if path.exists():
        return json.loads(path.read_text())
    sec("SURFACE HEAT raster and county percentiles")
    with rasterio.open(LST_TIF) as r:
        a = r.read(1)
        prof = {"crs": str(r.crs), "res": r.res, "shape": r.shape, "nodata": str(r.nodata),
                "dtype": r.dtypes[0], "band_description": r.descriptions[0],
                "bounds": list(r.bounds)}
        land, _ = county_land_mask(r.transform, r.shape, r.crs)
    valid = np.isfinite(a)
    on_land = a[land & valid]
    meta = {
        "profile": prof,
        "land_pixels": int(land.sum()), "land_valid_pixels": int((land & valid).sum()),
        "land_nodata_share": float(1 - (land & valid).sum() / land.sum()),
        "all_valid_pixels": int(valid.sum()),
        "p75": float(np.percentile(on_land, 75)), "p95": float(np.percentile(on_land, 95)),
        "pct_land": {str(p): round(float(np.percentile(on_land, p)), 2) for p in (5, 25, 50, 75, 95, 99)},
        "pct_all_valid": {str(p): round(float(np.percentile(a[valid], p)), 2) for p in (5, 25, 50, 75, 95, 99)},
        "min_land": float(on_land.min()), "max_land": float(on_land.max()),
    }
    print(json.dumps(meta, indent=2))
    path.write_text(json.dumps(meta, indent=2))
    return meta


def heat_buckets(thr):
    """Sorted cut points; code 0 = nodata, 1 = below the first cut, k+1 = at/above cut k."""
    # round(p95) only feeds the comparison with the website's whole-degree columns
    cuts = sorted(set([thr["p75"], thr["p95"], float(round(thr["p95"])), *HEAT_FIXED]))
    return cuts


def run_heat(blocks, thr):
    if (CK / "heat.csv").exists():
        print("heat: checkpoint exists, skipping")
        return
    sec("SURFACE HEAT on block land (fractional coverage)")
    cuts = heat_buckets(thr)
    with rasterio.open(LST_TIF) as r:
        a = r.read(1)
        tf, shape, crs = r.transform, r.shape, r.crs
    code = np.zeros(shape, dtype=np.uint8)
    valid = np.isfinite(a)
    code[valid] = 1 + np.searchsorted(np.array(cuts), a[valid], side="right")
    geoms = blocks.to_crs(crs).geometry.values
    coverage_check(geoms, tf, shape, "LST raster")
    out = {"GEOID20": blocks.GEOID20}
    for fac, tag in ((FACTOR, "frac"), (1, "ctr")):
        counts, sums, nsum, empty = zonal(geoms, tf, shape, {"h": (code, len(cuts) + 2)}, fac,
                                          weights={"lst": a})
        c = counts["h"]
        tot = c.sum(axis=1)
        val = tot - c[:, 0]
        out[f"cells_{tag}"] = tot
        out[f"nodata_{tag}"] = c[:, 0] / np.where(tot > 0, tot, np.nan)
        for j, t in enumerate(cuts):
            above = c[:, 2 + j:].sum(axis=1)
            out[f"ge_{t:.4f}_{tag}"] = np.where(val > 0, above / np.where(val > 0, val, 1), np.nan)
        out[f"mean_{tag}"] = np.where(nsum["lst"] > 0, sums["lst"] / np.where(nsum["lst"] > 0, nsum["lst"], 1), np.nan)
        print(f"  heat [{tag}] fallback blocks: {len(empty):,}; blocks with no valid pixel: "
              f"{int((val == 0).sum()):,} ({blocks.people.values[val == 0].sum():,.0f} residents)", flush=True)
    save_ck("heat.csv", pd.DataFrame(out))


def heat_land_shares(thr):
    path = CK / "heat_landshare.csv"
    if path.exists():
        return pd.read_csv(path, dtype={"GEOID": str})
    sec("SURFACE HEAT land shares (pixel-centre on unit land)")
    with rasterio.open(LST_TIF) as r:
        a = r.read(1)
        tf, shape, crs = r.transform, r.shape, r.crs
    units, _, _ = pslr.load_land_units()
    cuts = {"heat_p75": thr["p75"], "heat_p95": thr["p95"],
            **{f"heat_{int(t)}f": t for t in HEAT_FIXED}}
    valid = np.isfinite(a)
    frames = []
    for grain in ("tract", "bg"):
        u = units[grain]
        g = gpd.GeoSeries(u["land"].values, crs=AREA_CRS).to_crs(crs).values
        lab = rasterize(((x, i + 1) for i, x in enumerate(g) if not x.is_empty), out_shape=shape,
                        transform=tf, fill=0, dtype="int32").ravel()
        n = len(u) + 1
        tot = np.bincount(lab, minlength=n)[1:]
        nv = np.bincount(lab[valid.ravel()], minlength=n)[1:]
        df = pd.DataFrame({"GEOID": u["GEOID"].values})
        df["heat_land_nodata_share"] = np.where(tot > 0, 1 - nv / np.maximum(tot, 1), np.nan)
        for k, t in cuts.items():
            ge = np.bincount(lab[(valid & (a >= t)).ravel()], minlength=n)[1:]
            df[f"{k}_land_share"] = np.where(nv > 0, ge / np.maximum(nv, 1), np.nan)
        frames.append(df)
    out = pd.concat(frames)
    save_ck(path.name, out)
    return out


# --------------------------------------------------------------------------
# assemble
# --------------------------------------------------------------------------

def scenario_fracs(blocks, thr):
    """Block-level exposed share per scenario: {key: (frac, ctr or None)}."""
    f = {}
    for key in SLR_KEYS.values():
        c = pd.read_csv(CK / f"slr_{key}.csv", dtype={"GEOID20": str})
        f[key] = (c["frac"].to_numpy(), None)
    hole = {}
    for v in SURGE_VERSIONS:
        c = pd.read_csv(CK / f"surge_{v}.csv", dtype={"GEOID20": str})
        f[f"surge_{v}_any"] = (c["any_frac"].to_numpy(), c["any_ctr"].to_numpy())
        f[f"surge_{v}_over3ft"] = (c["over3_frac"].to_numpy(), c["over3_ctr"].to_numpy())
        if v == "cat5max":
            hole = {"frac": c["hole_frac"].to_numpy(), "ctr": c["hole_ctr"].to_numpy()}
        lev = c["levee_frac"].fillna(0).sum()
        if lev:
            print(f"  WARNING {v}: levee share present ({lev})")
    h = pd.read_csv(CK / "heat.csv", dtype={"GEOID20": str})
    cuts = {"heat_p75": thr["p75"], "heat_p95": thr["p95"],
            **{f"heat_{int(t)}f": t for t in HEAT_FIXED}}
    for k, t in cuts.items():
        f[k] = (h[f"ge_{t:.4f}_frac"].to_numpy(), h[f"ge_{t:.4f}_ctr"].to_numpy())
    t = float(round(thr["p95"]))
    cmp95 = (h[f"ge_{t:.4f}_frac"].to_numpy(), h[f"ge_{t:.4f}_ctr"].to_numpy())
    return f, hole, h, cmp95


def aggregate(blocks, fracs, hole, heat, thr):
    people = blocks.people.to_numpy()
    acs_bg = load_population("bg").set_index("GEOID")["population"]
    acs_tr = load_population("tract").set_index("GEOID")["population"]
    out = {}
    for grain, n_chars in (("bg", 12), ("tract", 11)):
        units = load_units(grain)[["GEOID", "ALAND"]].copy()
        key = blocks.GEOID20.str[:n_chars]
        df = units.set_index("GEOID")
        pop = (acs_bg.groupby(acs_bg.index.str[:n_chars]).sum()).reindex(df.index).fillna(0)
        df["population"] = pop
        df["block_people_sum"] = pd.Series(people).groupby(key.values).sum().reindex(df.index).fillna(0)
        has = df["population"] > 0
        for k, (fr, ctr) in fracs.items():
            ok = np.isfinite(fr)
            exp = pd.Series(people * np.where(ok, fr, 0)).groupby(key.values).sum()
            df[f"{k}_pop_exposed"] = exp.reindex(df.index).fillna(0)
            if k.startswith("heat_"):
                # heat: denominator is residents in blocks with at least one valid pixel
                base = pd.Series(people * ok).groupby(key.values).sum().reindex(df.index).fillna(0)
            else:
                base = df["population"]
            df[f"{k}_pop_share"] = np.where(base > 0, df[f"{k}_pop_exposed"] / base.where(base > 0, 1), np.nan)
        # continuous heat
        m = heat["mean_frac"].to_numpy()
        ok = np.isfinite(m)
        num = pd.Series(people * np.where(ok, m, 0)).groupby(key.values).sum().reindex(df.index)
        den = pd.Series(people * ok).groupby(key.values).sum().reindex(df.index)
        df["heat_lst_popwt_mean_f"] = np.where(den > 0, num / den.where(den > 0, 1), np.nan)
        # heat nodata share: share of the unit's populated-block land with no valid pixel
        land = blocks.land_m2.to_numpy()
        nd = heat["nodata_frac"].fillna(1).to_numpy()
        a_nd = pd.Series(land * nd).groupby(key.values).sum().reindex(df.index)
        a_all = pd.Series(land).groupby(key.values).sum().reindex(df.index)
        df["heat_nodata_share"] = np.where(a_all > 0, a_nd / a_all.where(a_all > 0, 1), np.nan)
        df["heat_pop_no_valid_pixel"] = pd.Series(people * ~ok).groupby(key.values).sum().reindex(df.index).fillna(0)
        # category 5 hole
        hp = pd.Series(people * np.nan_to_num(hole["frac"])).groupby(key.values).sum().reindex(df.index).fillna(0)
        df["surge_cat5_hole_pop"] = hp
        df["surge_cat5_hole_pop_share"] = np.where(has, hp / df["population"].where(has, 1), np.nan)
        df["surge_cat5_hole_flag"] = (df["surge_cat5_hole_pop_share"] >= 0.01).astype(int)
        df["low_pop_flag"] = (df["population"] < LOW_POP).astype(int)
        for k in [c for c in df if c.endswith("_pop_share")]:
            df.loc[~has, k] = np.nan
        out[grain] = df
    # block group survey reliability
    path, col, prefix = POP_FILES["bg"]
    raw = pd.read_csv(path, dtype=str, skiprows=[1])
    raw["GEOID"] = raw["GEO_ID"].str.replace(prefix, "", regex=False)
    moe = pd.to_numeric(raw.set_index("GEOID")["B01003_001M"], errors="coerce")
    bg = out["bg"]
    bg["bg_pop_moe"] = moe.reindex(bg.index)
    bg["bg_pop_cv"] = np.where(bg["population"] > 0, bg["bg_pop_moe"] / 1.645 / bg["population"].where(bg["population"] > 0, 1), np.nan)
    bg["bg_low_reliability"] = (bg["bg_pop_cv"] > CV_LOW).astype("Int64").where(bg["bg_pop_cv"].notna())
    tr = out["tract"]
    tr["acs_tract_population"] = acs_tr.reindex(tr.index)
    lowrel = bg["bg_low_reliability"].fillna(0).astype(int).groupby(bg.index.str[:11]).sum()
    tr["n_bg_low_reliability"] = lowrel.reindex(tr.index).fillna(0).astype(int)
    return out


def add_land_shares(out, thr):
    slr = {"tract": pd.read_csv(paths.HAZARDS_DIR / "slr_tract.csv", dtype={"GEOID": str}),
           "bg": pd.read_csv(paths.HAZARDS_DIR / "slr_blockgroup.csv", dtype={"GEOID": str})}
    surge = {"tract": pd.read_csv(paths.HAZARDS_DIR / "surge_tract.csv", dtype={"GEOID": str}),
             "bg": pd.read_csv(paths.HAZARDS_DIR / "surge_blockgroup.csv", dtype={"GEOID": str})}
    c5 = surge_cat5max_land_shares()
    hl = heat_land_shares(thr)
    for grain, df in out.items():
        s = slr[grain].set_index("GEOID")
        for k in SLR_KEYS.values():
            df[f"{k}_land_share"] = s[f"{k}_area_share"].reindex(df.index)
        g = surge[grain].set_index("GEOID")
        for cat in range(1, 6):
            df[f"surge_cat{cat}_any_land_share"] = g[f"surge_cat{cat}_area_share"].reindex(df.index)
            df[f"surge_cat{cat}_over3ft_land_share"] = g[f"surge_cat{cat}_over3ft_share"].reindex(df.index)
        c = c5.set_index("GEOID")
        for k in c:
            df[k] = c[k].reindex(df.index)
        h = hl.set_index("GEOID")
        for k in h:
            df[k] = h[k].reindex(df.index)
        df["jurisdiction"] = assign_municipality(load_units(grain)).reindex(df.index)
    return out


def order_columns(df, grain):
    keys = (list(SLR_KEYS.values())
            + [f"surge_{v}_{t}" for v in SURGE_VERSIONS for t in ("any", "over3ft")]
            + ["heat_p75", "heat_p95"] + [f"heat_{int(t)}f" for t in HEAT_FIXED])
    cols = ["population", "jurisdiction"]
    for k in keys:
        cols += [c for c in (f"{k}_pop_exposed", f"{k}_pop_share", f"{k}_land_share") if c in df]
    cols += ["heat_lst_popwt_mean_f", "heat_nodata_share", "heat_pop_no_valid_pixel",
             "heat_land_nodata_share", "surge_cat5_hole_pop", "surge_cat5_hole_pop_share",
             "surge_cat5_hole_flag", "low_pop_flag"]
    cols += (["bg_pop_moe", "bg_pop_cv", "bg_low_reliability"] if grain == "bg"
             else ["acs_tract_population", "n_bg_low_reliability"])
    cols += ["ALAND"]
    return df[cols]


# --------------------------------------------------------------------------
# validation
# --------------------------------------------------------------------------

def validate(blocks, out, fracs, thr):
    sec("VALIDATION")
    people = blocks.people.to_numpy()
    acs = load_population("bg")["population"].fillna(0).sum()
    print(f"residents over blocks {people.sum():,.1f} vs ACS county {acs:,.0f}: "
          f"{'OK' if math.isclose(people.sum(), acs, rel_tol=1e-9) else 'MISMATCH'}")
    tr, bg = out["tract"], out["bg"]
    for grain, df in out.items():
        print(f"{grain}: rows {len(df):,} (expected {EXPECTED[grain]:,}), GEOID unique "
              f"{df.index.is_unique}, all 12086 {df.index.str.startswith('12086').all()}")
        d = (df["population"] - df["block_people_sum"]).abs().max()
        print(f"  unit population vs sum of its blocks: max abs diff {d:.6f}")
    d = (tr["population"] - tr["acs_tract_population"]).abs()
    print(f"tract population (sum of ACS BG) vs ACS tract table B01001: {int((d > 0.5).sum())} tracts "
          f"differ, max {d.max():.0f}")
    print("\nshares in [0, 1] and exposed <= population:")
    bad_any = 0
    for grain, df in out.items():
        for c in [c for c in df if c.endswith("_pop_share")]:
            s = df[c]
            n_out = int(((s < -1e-12) | (s > 1 + 1e-9)).sum())
            e = c.replace("_pop_share", "_pop_exposed")
            if e not in df:
                e = c.replace("_pop_share", "_pop")  # surge_cat5_hole_pop
            n_ex = int((df[e] > df["population"] + 1e-6).sum())
            bad_any += n_out + n_ex
            if n_out or n_ex:
                print(f"  {grain} {c}: out of range {n_out}, exposed > population {n_ex}")
    print(f"  violations: {bad_any}")
    print("\nblock groups summed to tracts (pop_exposed):")
    worst = 0
    for c in [c for c in bg if c.endswith("_pop_exposed")] + ["population"]:
        s = bg[c].groupby(bg.index.str[:11]).sum().reindex(tr.index).fillna(0)
        worst = max(worst, float((s - tr[c]).abs().max()))
    print(f"  max abs difference over all count columns: {worst:.6f}")
    print("\nmonotonicity:")
    seqs = [["slr_1ft", "slr_2ft", "slr_3ft", "slr_6ft"],
            ["heat_100f", "heat_105f", "heat_110f"],
            sorted(["heat_p75", "heat_p95", "heat_100f", "heat_105f", "heat_110f"],
                   key=lambda k: thr["p75"] if k == "heat_p75" else thr["p95"] if k == "heat_p95"
                   else float(k[5:8]))]
    for grain, df in out.items():
        for seq in seqs:
            for lo, hi in zip(seq, seq[1:]):
                n = int((df[f"{hi}_pop_exposed"] > df[f"{lo}_pop_exposed"] + 1e-6).sum()) if lo.startswith("heat") \
                    else int((df[f"{hi}_pop_exposed"] < df[f"{lo}_pop_exposed"] - 1e-6).sum())
                print(f"  {grain} {lo} -> {hi}: {n} violations")
    print("\nsurge reversals (higher category exposes fewer residents), reported, not forced:")
    for grain, df in out.items():
        for t in ("any", "over3ft"):
            for lo, hi in [(1, 2), (2, 3), (3, 4), (4, 5)]:
                a, b = df[f"surge_cat{lo}_{t}_pop_exposed"], df[f"surge_cat{hi}_{t}_pop_exposed"]
                rev = (b < a - 0.5)
                print(f"  {grain} {t} cat{lo}->cat{hi}: {int(rev.sum())} units, residents lost "
                      f"{(a - b)[rev].sum():,.0f}")
            a, b = df[f"surge_cat4_{t}_pop_exposed"], df[f"surge_cat5max_{t}_pop_exposed"]
            print(f"  {grain} {t} cat4->cat5max: {int((b < a - 0.5).sum())} units (must be 0)")
    print(f"\nflags: tract low_pop {int(tr.low_pop_flag.sum())}, bg low_pop {int(bg.low_pop_flag.sum())}, "
          f"bg low reliability {int(bg.bg_low_reliability.fillna(0).sum())} of "
          f"{int(bg.bg_low_reliability.notna().sum())} with a CV, cat5 hole tracts "
          f"{int(tr.surge_cat5_hole_flag.sum())}, bgs {int(bg.surge_cat5_hole_flag.sum())}")
    cv = bg["bg_pop_cv"].dropna()
    print(f"  bg CV bands: <=12% {int((cv <= .12).sum())}, 12-40% {int(((cv > .12) & (cv <= .40)).sum())}, "
          f">40% {int((cv > .40).sum())}")

    sec("COUNTY TOTALS: fractional vs pixel-centre, and against the website")
    total = people.sum()
    web_slr = {s["ft"]: s["people"] for s in json.loads((VIZ_DATA / "slr.json").read_text())["stats"]}
    web_surge = {s["category"]: s["people"] for s in json.loads((VIZ_DATA / "surge.json").read_text())["stats"]}
    web_heat = json.loads((VIZ_DATA / "heat.json").read_text())["people_at_or_above"]
    rows = []
    for k, (fr, ctr) in fracs.items():
        ef = float(np.nansum(people * fr))
        ec = float(np.nansum(people * ctr)) if ctr is not None else np.nan
        web = np.nan
        if k.startswith("slr_"):
            web = web_slr.get(float(k[4]), np.nan)
        elif k.startswith("surge_") and k.endswith("_any"):
            cat = 5 if "cat5max" in k else int(k[9])
            web = web_surge[cat] if ("cat5max" in k or cat < 5) else np.nan
        elif k.startswith("heat_") and k.endswith("f"):
            web = web_heat.get(k[5:8], np.nan)
        rows.append({"scenario": k, "residents_fractional": round(ef), "share_fractional": ef / total,
                     "residents_pixel_centre": None if np.isnan(ec) else round(ec),
                     "frac_minus_centre": None if np.isnan(ec) else round(ef - ec),
                     "website_people": None if (isinstance(web, float) and np.isnan(web)) else web})
    t = pd.DataFrame(rows)
    t["frac_vs_website_pct"] = (t["residents_fractional"] / t["website_people"] - 1) * 100
    print(t.to_string(index=False, float_format=lambda v: f"{v:,.4f}"))
    t.to_csv(paths.OUT_EXPOSURE_A / "exposure_county_totals.csv", index=False)


def compare_website_blocks(blocks, out, fracs, thr, cmp95):
    """Tract totals against src/exposure/data/exposure_blocks.json summed to tracts."""
    sec("TRACT TOTALS AGAINST exposure_blocks.json (website, summed to tracts)")
    e = json.loads((VIZ_DATA / "exposure_blocks.json").read_text())
    cols = e["columns"]
    w = pd.DataFrame([[r[0]] + r[4:] for r in e["blocks"]], columns=["GEOID20"] + cols[4:])
    w["tract"] = w.GEOID20.str[:11]
    t95 = int(round(thr["p95"]))
    tr = out["tract"]
    people = blocks.people.to_numpy()
    key = blocks.GEOID20.str[:11].values
    def tract_sum(v):
        return pd.Series(people * np.nan_to_num(v)).groupby(key).sum().reindex(tr.index).fillna(0)
    # surge: the website counts land wet at Category 3 OR LOWER (cumulative);
    # the per-block maximum of categories 1-3 is a lower bound of that union
    cum3 = np.fmax(np.fmax(fracs["surge_cat1_any"][0], fracs["surge_cat2_any"][0]), fracs["surge_cat3_any"][0])
    cases = [
        ("slr_3ft", "slr_3.0", fracs["slr_3ft"][0], None, None),
        ("surge_cat3_any", "surge_3", fracs["surge_cat3_any"][0], fracs["surge_cat3_any"][1], cum3),
        (f"heat at {t95} F (p95 = {thr['p95']:.2f} F)", f"heat_{t95}", cmp95[0], cmp95[1], None),
    ]
    h = pd.read_csv(CK / "heat.csv", dtype={"GEOID20": str})
    rows = []
    for name, wcol, frac, ctr, cum in cases:
        web = w.groupby("tract")[wcol].sum().reindex(tr.index).fillna(0)
        mine = tract_sum(frac)
        r = {"layer": name, "website_column": wcol, "website_total": web.sum(), "ours_fractional": mine.sum()}
        if ctr is not None:
            r["ours_pixel_centre"] = tract_sum(ctr).sum()
        if cum is not None:
            r["ours_cumulative_lower_bound"] = tract_sum(cum).sum()
        d = mine - web
        r.update({"spearman_tracts": pd.concat([mine, web], axis=1)[tr.population > 0].corr(method="spearman").iloc[0, 1],
                  "tracts_abs_diff_gt_100": int((d.abs() > 100).sum()),
                  "median_abs_diff": d.abs().median(), "max_abs_diff": d.abs().max()})
        rows.append(r)
        big = pd.DataFrame({"ours": mine, "website": web, "diff": d,
                            "jurisdiction": tr.get("jurisdiction")}).reindex(d.abs().sort_values(ascending=False).index)
        print(f"\n--- {name}: largest tract differences ---")
        print(big.head(8).to_string(float_format=lambda v: f"{v:,.0f}"))
    res = pd.DataFrame(rows)
    print(res.T.to_string())
    res.to_csv(paths.OUT_EXPOSURE_A / "exposure_vs_website_blocks.csv", index=False)
    print(f"note: the website heat columns are whole degrees, so the comparison uses {t95} F "
          f"for both; the exposure tables use the exact p95 of {thr['p95']:.2f} F")


def main():
    CK.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    blocks = blocks_table()
    print(f"  blocks whose land equals the whole block (no mapped water removed): {int(blocks.full_shape.sum())}")
    run_slr(blocks)
    run_surge(blocks)
    thr = heat_thresholds()
    run_heat(blocks, thr)
    fracs, hole, heat, cmp95 = scenario_fracs(blocks, thr)
    out = aggregate(blocks, fracs, hole, heat, thr)
    out = add_land_shares(out, thr)
    validate(blocks, out, fracs, thr)
    compare_website_blocks(blocks, out, fracs, thr, cmp95)
    for grain, df in out.items():
        o = order_columns(df, grain).reset_index()
        o["GEOID"] = o["GEOID"].astype(str)
        o.to_csv(OUT[grain], index=False)
        print(f"wrote {OUT[grain].name}: {len(o):,} rows x {o.shape[1]} columns")
    print(f"total {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
