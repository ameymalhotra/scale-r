"""Stage 2: build NHC SLOSH MOM storm surge exposure variables for Miami-Dade.

Data preparation only. Builds standalone tract and block-group files; does not
join them to the analysis tables, model, or correlate anything with investment.

Source (see surge_inspection.md): NHC National Storm Surge Hazard Map v4,
reprocessed 06/2026, MOM, high tide, one uint8 GeoTIFF per category 1 to 5.
  classes 1-21  depth above ground in 1 ft bins (21 = more than 20 ft)
  99            leveed area, never a depth (absent in Miami-Dade, still handled)
  255           nodata tag; on Miami-Dade land it means "not inundated"
  0             not used

Method, per category:
  1. the raster is never reprojected (categorical data); TIGER units are
     already NAD83 (EPSG:4269), the raster's CRS
  2. unit land geometry = unit polygon minus TIGER areawater, rasterized once
     per grain into a label grid (pixel-centre rule) on the Miami-Dade window
  3. read only the Miami-Dade window of the raster, raw values (no masked
     read: 255 on land is dry land and must stay in the denominator)
  4. per unit, count pixels by class; numerator and denominator are both
     pixel counts within the unit's land-only shape

Coding:  area_share        = class 1-21 pixels / land pixels
         over3ft_share     = class 4-21 pixels / land pixels  (more than 3 ft)
         mean_depth_class  = mean class over inundated land pixels; NA if none
         levee_share       = class 99 pixels / land pixels
         any               = 1 if any land pixel is class 1-21
         unit with no inundation   -> 0 on shares and any (not missing)
         unit with no land pixels  -> NA on everything

Checkpointing: each category's result is written to output/surge_checkpoints/
the moment it completes; categories with an existing checkpoint are skipped,
so a restart resumes. Final files are assembled only when all five exist.

Usage: python scripts/process_surge.py
"""
import gc
import sys
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
import shapely
from rasterio.features import rasterize
from rasterio.transform import array_bounds
from rasterio.windows import from_bounds

sys.path.insert(0, str(Path(__file__).resolve().parent))
from allocation import BOUNDARY_DIR, load_units  # noqa: E402

BASE = Path(__file__).resolve().parent.parent
SURGE_DIR = (BASE / "tract-level" / "Physical Indicators"
             / "US_SLOSH_MOM_Inundation_v4_20260617")
CHECKPOINTS = BASE / "output" / "surge_checkpoints"
EXPECTED = {"tract": 707, "bg": 1843}
OUT_FILES = {"tract": BASE / "surge_tract.csv", "bg": BASE / "surge_blockgroup.csv"}

CATEGORIES = [1, 2, 3, 4, 5]
DEPTH_MIN, DEPTH_MAX, OVER3_MIN = 1, 21, 4
LEVEE, NODATA = 99, 255
ALLOWED = set(range(DEPTH_MIN, DEPTH_MAX + 1)) | {LEVEE, NODATA}


def sec(t):
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78, flush=True)


def raster_path(cat):
    return SURGE_DIR / f"us_Category{cat}_MOM_Inundation_HIGH.tif"


def checkpoint_path(cat, grain):
    return CHECKPOINTS / f"cat{cat}_{grain}.csv"


def repair(geoms, label):
    """Validity check on every geometry; make_valid only where needed."""
    invalid = ~shapely.is_valid(geoms)
    n = int(invalid.sum())
    if n:
        geoms = geoms.copy()
        geoms[invalid] = shapely.make_valid(geoms[invalid])
    print(f"  {label}: {len(geoms):,} geometries, {n:,} invalid -> "
          f"{'repaired with make_valid' if n else 'no repair needed'}",
          flush=True)
    return geoms, n


def load_land_units(crs):
    """Units in the raster CRS with a land-only geometry (unit minus areawater)."""
    water = gpd.read_file(f"zip://{BOUNDARY_DIR / 'tl_2024_12086_areawater.zip'}")
    wgeoms, _ = repair(water.to_crs(crs).geometry.values, "TIGER areawater")
    water_union = shapely.union_all(wgeoms)
    units = {}
    for grain in ("tract", "bg"):
        u = load_units(grain).to_crs(crs)
        g, _ = repair(u.geometry.values, f"TIGER {grain}")
        u["land"] = shapely.difference(g, water_union)
        units[grain] = u[["GEOID", "ALAND", "land"]]
    return units


def reference_grid(county_bounds):
    """Miami-Dade window on the category 1 grid, padded by 2 pixels."""
    with rasterio.open(raster_path(1)) as r:
        pad = 2 * r.res[0]
        w, s, e, n = county_bounds
        win = from_bounds(w - pad, s - pad, e + pad, n + pad, r.transform)
        win = win.round_offsets().round_lengths()
        tf = r.window_transform(win)
        shape = (int(win.height), int(win.width))
    return tf, shape


def label_grid(land, tf, shape):
    """int16 grid: unit index + 1 where the pixel centre is on the unit's land."""
    shapes = ((g, i + 1) for i, g in enumerate(land) if not g.is_empty)
    return rasterize(shapes, out_shape=shape, transform=tf, fill=0, dtype="int16")


def read_window(cat, ref_tf, ref_shape):
    """Raw values of one category on the reference window; never the full raster."""
    with rasterio.open(raster_path(cat)) as r:
        if r.crs.to_epsg() != 4269 or r.count != 1 or r.dtypes[0] != "uint8":
            raise SystemExit(f"cat {cat}: unexpected raster profile {r.profile}")
        bounds = array_bounds(*ref_shape, ref_tf)
        bounds = (bounds[0], bounds[1], bounds[2], bounds[3])
        win = from_bounds(*bounds, r.transform).round_offsets().round_lengths()
        tf = r.window_transform(win)
        # category 5 has a different extent; its window must land on the same
        # geographic pixels as the grid the labels were rasterized on
        if (int(win.height), int(win.width)) != ref_shape or not np.allclose(
                tuple(tf)[:6], tuple(ref_tf)[:6], rtol=0, atol=1e-9):
            raise SystemExit(f"cat {cat}: window does not align with reference grid")
        return r.read(1, window=win)


def class_counts(labels, a, n):
    """(n, 256) pixel counts by unit and class value, labelled pixels only."""
    lab = labels.ravel()
    m = lab > 0
    key = lab[m].astype(np.int32) * 256 + a.ravel()[m]
    return np.bincount(key, minlength=(n + 1) * 256).reshape(n + 1, 256)[1:]


def summarise(geoids, counts, prefix):
    land = counts.sum(axis=1)
    depth = counts[:, DEPTH_MIN:DEPTH_MAX + 1]
    inund = depth.sum(axis=1)
    over3 = counts[:, OVER3_MIN:DEPTH_MAX + 1].sum(axis=1)
    levee = counts[:, LEVEE]
    class_sum = (depth * np.arange(DEPTH_MIN, DEPTH_MAX + 1)).sum(axis=1)
    has_land = land > 0
    denom = np.where(has_land, land, 1)
    out = pd.DataFrame({"GEOID": geoids, "land_px": land, "inund_px": inund,
                        "over3_px": over3, "levee_px": levee})
    out[f"{prefix}_area_share"] = np.where(has_land, inund / denom, np.nan)
    out[f"{prefix}_over3ft_share"] = np.where(has_land, over3 / denom, np.nan)
    out[f"{prefix}_mean_depth_class"] = np.where(
        inund > 0, class_sum / np.maximum(inund, 1), np.nan)
    out[f"{prefix}_levee_share"] = np.where(has_land, levee / denom, np.nan)
    out[f"{prefix}_any"] = pd.Series((inund > 0).astype(int)).astype("Int64").where(has_land)
    return out


def process_category(cat, units, labels, ref_tf, ref_shape):
    todo = [gr for gr in ("tract", "bg") if not checkpoint_path(cat, gr).exists()]
    if not todo:
        print(f"category {cat}: both checkpoints exist, skipping", flush=True)
        return
    sec(f"CATEGORY {cat} -> surge_cat{cat}  (grains: {', '.join(todo)})")
    t0 = time.time()
    a = read_window(cat, ref_tf, ref_shape)
    vals = np.bincount(a.ravel(), minlength=256)
    present = {int(v) for v in np.flatnonzero(vals)}
    print(f"  read window {a.shape[1]:,} x {a.shape[0]:,} ({time.time() - t0:.1f}s); "
          f"values present: {sorted(present)}", flush=True)
    if present - ALLOWED:
        raise SystemExit(f"cat {cat}: unexpected pixel values {sorted(present - ALLOWED)}")
    for grain in todo:
        t = time.time()
        u = units[grain]
        counts = class_counts(labels[grain], a, len(u))
        out = summarise(u["GEOID"].values, counts, f"surge_cat{cat}")
        out.to_csv(checkpoint_path(cat, grain), index=False)
        print(f"  {grain}: {len(out):,} units, {int((out.inund_px > 0).sum()):,} "
              f"inundated, levee px {int(out.levee_px.sum()):,}, "
              f"checkpoint written ({time.time() - t:.1f}s)", flush=True)
        del counts
    del a
    gc.collect()
    print(f"  category total {time.time() - t0:.1f}s", flush=True)


def assemble(grain):
    df, land_px, counts = None, None, {}
    for cat in CATEGORIES:
        c = pd.read_csv(checkpoint_path(cat, grain), dtype={"GEOID": str})
        c[f"surge_cat{cat}_any"] = c[f"surge_cat{cat}_any"].astype("Int64")
        px = c.pop("land_px")
        # same label grid for every category, so the denominator must not move
        if land_px is not None and not px.equals(land_px):
            raise SystemExit(f"{grain}: land pixel counts differ across categories")
        land_px = px
        counts[cat] = c[["GEOID", "inund_px", "over3_px", "levee_px"]].copy()
        c = c.drop(columns=["inund_px", "over3_px", "levee_px"])
        df = c if df is None else df.merge(c, on="GEOID", how="outer", validate="1:1")
    df.insert(1, "surge_land_px", land_px.values)
    return df.sort_values("GEOID").reset_index(drop=True), counts


def validate(grain, df, counts):
    sec(f"VALIDATION: {grain}")
    ok = len(df) == EXPECTED[grain]
    print(f"rows: {len(df):,} (expected {EXPECTED[grain]:,}) -> {'OK' if ok else 'MISMATCH'}")
    print(f"GEOID all string, prefix 12086: {df.GEOID.str.startswith('12086').all()}, "
          f"unique: {df.GEOID.is_unique}")
    no_land = df.GEOID[df.surge_land_px == 0].tolist()
    print(f"units with no land pixels (NA): {no_land}")
    print(f"land pixels per unit: min {df.surge_land_px[df.surge_land_px > 0].min():,}, "
          f"median {df.surge_land_px.median():,.0f}")

    for cat in CATEGORIES:
        p = f"surge_cat{cat}"
        print(f"\n  category {cat}")
        for s in ("area_share", "over3ft_share", "levee_share"):
            v = df[f"{p}_{s}"]
            outside = v[(v < 0) | (v > 1)]
            print(f"    {s:14s} NA {v.isna().sum()}  zero {(v == 0).sum():>5,}  "
                  f">0 {(v > 0).sum():>5,}  mean {v.mean():.4f}  max {v.max():.4f}  "
                  f"outside [0,1]: {len(outside)}")
        m = df[f"{p}_mean_depth_class"]
        inund = df[f"{p}_area_share"] > 0
        print(f"    mean_depth_class NA {m.isna().sum()} (= units with no inundation "
              f"or no land: {m.isna().sum() == (~inund).sum()}), range "
              f"{m.min():.2f} to {m.max():.2f}, within [1,21]: "
              f"{m.dropna().between(DEPTH_MIN, DEPTH_MAX).all()}")
        print(f"    any=1 {int(df[f'{p}_any'].sum()):,}, matches area_share > 0: "
              f"{(df[f'{p}_any'].fillna(0).astype(bool) == inund).all()}")
        has_land = df.surge_land_px > 0
        print(f"    over3ft_share <= area_share: "
              f"{(df[f'{p}_over3ft_share'] <= df[f'{p}_area_share'] + 1e-12)[has_land].all()}")
    levee = sum(int(c.levee_px.sum()) for c in counts.values())
    print(f"\nclass 99 pixels across all categories: {levee:,} "
          f"(counted only in levee_share, never in depth variables)")

    print("\nmonotonicity across categories (inundated pixel counts, same denominator):")
    pairs = list(zip(CATEGORIES, CATEGORIES[1:])) + [(1, 3), (3, 5)]
    for lo, hi in pairs:
        for s in ("area_share", "over3ft_share"):
            a, b = df[f"surge_cat{lo}_{s}"], df[f"surge_cat{hi}_{s}"]
            bad = df[b < a - 1e-12]
            print(f"  cat{hi} >= cat{lo} {s:14s}: {len(bad)} violations"
                  + (f", largest drop {(a - b)[bad.index].max():.6f}" if len(bad) else ""))
            if len(bad):
                print(bad[["GEOID", f"surge_cat{lo}_{s}", f"surge_cat{hi}_{s}"]]
                      .head(20).to_string(index=False))


def nesting_check(bg_counts, tract_counts):
    sec("NESTING: block groups summed to tracts vs tracts")
    for cat in CATEGORIES:
        b = bg_counts[cat].assign(tract=lambda d: d.GEOID.str[:11])
        b = b.groupby("tract")[["inund_px", "over3_px"]].sum()
        t = tract_counts[cat].set_index("GEOID")[["inund_px", "over3_px"]]
        diff = (t - b.reindex(t.index).fillna(0)).abs()
        print(f"  cat {cat}: tracts with differing inundated px {int((diff.inund_px > 0).sum())}, "
              f"max abs diff {int(diff.inund_px.max())} px; over3 differing "
              f"{int((diff.over3_px > 0).sum())}")


def top_tracts(df):
    sec("GEOGRAPHY SANITY: top 10 tracts by surge_cat3_area_share")
    places = gpd.read_file(f"zip://{BOUNDARY_DIR / 'tl_2024_12_place.zip'}").to_crs(4269)
    tr = load_units("tract").to_crs(4269)
    top = df.sort_values(["surge_cat3_area_share", "surge_cat3_mean_depth_class"],
                         ascending=False).head(10)[
        ["GEOID", "surge_land_px", "surge_cat1_area_share", "surge_cat3_area_share",
         "surge_cat3_over3ft_share", "surge_cat3_mean_depth_class", "surge_cat5_area_share"]]
    pts = tr.set_index("GEOID").loc[top.GEOID].representative_point()
    pts = gpd.GeoDataFrame(geometry=pts.values, index=pts.index, crs=4269)
    j = gpd.sjoin(pts, places[["NAME", "geometry"]], how="left", predicate="within")
    j = j[~j.index.duplicated()]
    top["place"] = top.GEOID.map(j["NAME"]).fillna("(unincorporated, no CDP)")
    n_full = int((df.surge_cat3_area_share == 1).sum())
    print(f"tracts with cat 3 share == 1: {n_full} (ties broken by mean depth class)")
    print(top.round(3).to_string(index=False))


def main():
    missing = [str(raster_path(c)) for c in CATEGORIES if not raster_path(c).exists()]
    if missing:
        raise SystemExit(f"rasters not found: {missing}")
    CHECKPOINTS.mkdir(parents=True, exist_ok=True)

    sec("UNITS, LAND MASK AND LABEL GRIDS")
    with rasterio.open(raster_path(1)) as r:
        crs = r.crs
    units = load_land_units(crs)
    county_bounds = shapely.union_all(units["tract"]["land"].values).bounds
    ref_tf, ref_shape = reference_grid(county_bounds)
    print(f"  reference window {ref_shape[1]:,} x {ref_shape[0]:,} px, "
          f"bounds {tuple(round(b, 4) for b in array_bounds(*ref_shape, ref_tf))}")
    labels = {}
    for grain, u in units.items():
        t = time.time()
        labels[grain] = label_grid(u["land"].values, ref_tf, ref_shape)
        px = np.bincount(labels[grain].ravel(), minlength=len(u) + 1)[1:]
        empty = u.GEOID[(px == 0) & (u.ALAND > 0)].tolist()
        print(f"  {grain}: {len(u):,} units, ALAND == 0: {u.GEOID[u.ALAND == 0].tolist()}, "
              f"land but no pixel centre: {empty} ({time.time() - t:.1f}s)", flush=True)

    for cat in CATEGORIES:
        process_category(cat, units, labels, ref_tf, ref_shape)
    del labels
    gc.collect()

    missing = [str(checkpoint_path(c, g)) for c in CATEGORIES for g in ("tract", "bg")
               if not checkpoint_path(c, g).exists()]
    if missing:
        raise SystemExit(f"checkpoints missing, not assembling: {missing}")

    frames, counts = {}, {}
    for grain in ("tract", "bg"):
        frames[grain], counts[grain] = assemble(grain)
        frames[grain].to_csv(OUT_FILES[grain], index=False)
        print(f"\nwrote {OUT_FILES[grain].name}: {len(frames[grain]):,} rows x "
              f"{frames[grain].shape[1]} cols")

    for grain, df in frames.items():
        validate(grain, df, counts[grain])
    nesting_check(counts["bg"], counts["tract"])
    top_tracts(frames["tract"])


if __name__ == "__main__":
    main()
