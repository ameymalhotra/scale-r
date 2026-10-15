"""Stage 2: build NOAA sea level rise exposure variables for Miami-Dade.

Data preparation only. Builds standalone tract and block-group files; does not
join them to the analysis tables, model, or correlate anything with investment.

Layers (decided after Stage 1, see slr_inspection.md):
  FL_SE_slr_1_0ft, _2_0ft, _3_0ft, _6_0ft  ocean-connected inundation, primary
  FL_SE_low_3_0ft                          unconnected low-lying, sensitivity
The gridcode attribute is ignored; only geometry is used.

Method, per layer:
  1. read only the Miami-Dade bounding box (GeoPackage rtree index), so the
     4 GB file is never held in memory; one layer at a time, released after
  2. reproject to EPSG:6346 (UTM 17N, NAD83(2011)) before any area math
  3. check validity of every feature read; make_valid only the invalid ones
  4. clip to the Miami-Dade land mask
  5. subdivide into pieces of <= 2,000 vertices (the ocean-connected surface is
     one ~2.2M vertex polygon; unsplit, it made one layer take 30+ minutes)
  6. intersect with each unit's LAND geometry and take the area of the union

Why land geometry: NOAA's inundation polygons include existing open water (the
bay is 100% covered even at 1 ft) and TIGER units extend into the bay. The
unit polygon minus TIGER areawater is used as the land footprint, so the
numerator is inundated land and the ALAND denominator is comparable.

Coding:  share = inundated land area / ALAND;  any = 1 if share area > 0.
         unit with no inundation   -> 0 (not missing)
         unit with ALAND == 0      -> NA for both (no land to inundate)

Checkpointing: each layer's result is written to output/slr_checkpoints/ the
moment it completes; layers with an existing checkpoint are skipped, so a
restart resumes. Final files are assembled only when all five exist.

Usage: python scripts/process_slr.py
"""
import gc
import sys
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

sys.path.insert(0, str(Path(__file__).resolve().parent))
from allocation import BOUNDARY_DIR, load_units  # noqa: E402

BASE = Path(__file__).resolve().parent.parent
GPKG = (BASE / "tract-level" / "Physical Indicators" / "FL_SE_slr_data_dist"
        / "FL_SE_slr_final_dist.gpkg")
CHECKPOINTS = BASE / "output" / "slr_checkpoints"
AREA_CRS = "EPSG:6346"  # UTM 17N, NAD83(2011); matches the rest of the project
EXPECTED = {"tract": 707, "bg": 1843}
# UTM area runs ~0.07% below the Census ALAND, so a fully flooded unit tops
# out near 0.9993, never exactly 1; "entirely inundated" means share >= this
FULL_SHARE = 0.99
OUT_FILES = {"tract": BASE / "slr_tract.csv", "bg": BASE / "slr_blockgroup.csv"}

# layer name -> variable prefix
LAYERS = {
    "FL_SE_slr_1_0ft": "slr_1ft",
    "FL_SE_slr_2_0ft": "slr_2ft",
    "FL_SE_slr_3_0ft": "slr_3ft",
    "FL_SE_slr_6_0ft": "slr_6ft",
    "FL_SE_low_3_0ft": "low_3ft",
}
SLR_SEQUENCE = ["slr_1ft", "slr_2ft", "slr_3ft", "slr_6ft"]


def sec(t):
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78, flush=True)


def checkpoint_path(layer, grain):
    return CHECKPOINTS / f"{layer}_{grain}.csv"


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


def load_land_units():
    """Units in EPSG:6346 with a land-only geometry (unit minus areawater)."""
    water = gpd.read_file(f"zip://{BOUNDARY_DIR / 'tl_2024_12086_areawater.zip'}")
    # 3 stream polygons (H3010) carry ALAND > 0, AWATER == 0: the Census counts
    # them as land, so removing them would put the geometry out of step with
    # ALAND (one block group dropped to 30% of its ALAND). Remove water only.
    counted_as_land = water["AWATER"] == 0
    print(f"  areawater: {len(water):,} features, {int(counted_as_land.sum())} "
          f"counted as land by the Census (AWATER == 0), kept as land", flush=True)
    water = water[~counted_as_land].to_crs(AREA_CRS)
    wgeoms, _ = repair(water.geometry.values, "TIGER areawater")
    water_union = shapely.union_all(wgeoms)
    units = {}
    for grain in ("tract", "bg"):
        u = load_units(grain).to_crs(AREA_CRS)
        g, _ = repair(u.geometry.values, f"TIGER {grain}")
        u["land"] = shapely.difference(g, water_union)
        ratio = shapely.area(u["land"].values) / u["ALAND"].replace(0, np.nan)
        print(f"  {grain}: land-geometry area / ALAND  median {ratio.median():.4f}, "
              f"min {ratio.min():.4f}, max {ratio.max():.4f}", flush=True)
        units[grain] = u[["GEOID", "ALAND", "land"]]
    county_land = shapely.union_all(units["tract"]["land"].values)
    county_bbox = tuple(load_units("tract").total_bounds)  # EPSG:4269, as the gpkg
    return units, county_land, county_bbox


def subdivide(geoms, max_vertices=2000):
    """Split geometries into pieces of at most max_vertices by recursive halving.

    Same idea as PostGIS ST_Subdivide. Without it, the ~2.2 million vertex
    ocean-connected polygon is re-processed for every unit it touches. Pieces
    tile the original exactly, so areas are unchanged.
    """
    out, todo = [], list(geoms)
    while todo:
        g = todo.pop()
        if shapely.get_num_coordinates(g) <= max_vertices:
            out.append(g)
            continue
        x0, y0, x1, y1 = g.bounds
        if x1 - x0 >= y1 - y0:
            xm = (x0 + x1) / 2
            halves = [shapely.box(x0, y0, xm, y1), shapely.box(xm, y0, x1, y1)]
        else:
            ym = (y0 + y1) / 2
            halves = [shapely.box(x0, y0, x1, ym), shapely.box(x0, ym, x1, y1)]
        for h in halves:
            part = shapely.intersection(g, h)
            # keep polygonal output only; slivers on the cut line are lines/points
            part = shapely.get_parts(part)
            part = part[np.isin(shapely.get_type_id(part), [3, 6])]
            todo.extend(p for p in part if not p.is_empty)
    return np.array(out, dtype=object)


def inundated_area(unit_land, inund):
    """Area of each unit's land covered by the union of inundation features."""
    tree = shapely.STRtree(inund)
    unit_idx, feat_idx = tree.query(unit_land, predicate="intersects")
    pieces = shapely.intersection(unit_land[unit_idx], inund[feat_idx])
    area = np.zeros(len(unit_land))
    for i in np.unique(unit_idx):
        # union per unit so overlapping features are never double counted
        area[i] = shapely.area(shapely.union_all(pieces[unit_idx == i]))
    return area


def process_layer(layer, prefix, units, county_land, county_bbox):
    todo = [gr for gr in ("tract", "bg") if not checkpoint_path(layer, gr).exists()]
    if not todo:
        print(f"{layer}: both checkpoints exist, skipping", flush=True)
        return None
    sec(f"{layer} -> {prefix}  (grains: {', '.join(todo)})")
    t0 = time.time()
    g = gpd.read_file(GPKG, layer=layer, bbox=county_bbox, columns=[])
    print(f"  read {len(g):,} features in Miami-Dade bbox "
          f"({time.time() - t0:.0f}s)", flush=True)
    geoms = g.to_crs(AREA_CRS).geometry.values
    del g
    geoms, n_repaired = repair(geoms, layer)

    t = time.time()
    # the bbox read over-reaches into Broward, Collier, Monroe and open water;
    # drop features off the county land, then clip the rest to it
    shapely.prepare(county_land)
    geoms = geoms[shapely.intersects(county_land, geoms)]
    geoms = shapely.intersection(geoms, county_land)
    geoms = geoms[~shapely.is_empty(geoms)]
    print(f"  clipped to Miami-Dade land: {len(geoms):,} features "
          f"({time.time() - t:.0f}s)", flush=True)
    t = time.time()
    before = shapely.area(geoms).sum()
    geoms = subdivide(geoms)
    after = shapely.area(geoms).sum()
    print(f"  subdivided to {len(geoms):,} pieces, area change "
          f"{(after - before) / before:+.2e} ({time.time() - t:.0f}s)", flush=True)

    for grain in todo:
        t = time.time()
        u = units[grain]
        area = inundated_area(u["land"].values, geoms)
        has_land = u["ALAND"] > 0
        out = pd.DataFrame({"GEOID": u["GEOID"]})
        out[f"{prefix}_area_share"] = np.where(has_land, area / u["ALAND"].where(has_land), np.nan)
        out[f"{prefix}_any"] = pd.Series((area > 0).astype(int)).astype("Int64").where(has_land)
        out["invalid_repaired"] = n_repaired
        out.to_csv(checkpoint_path(layer, grain), index=False)
        print(f"  {grain}: {len(out):,} units, {int((area > 0).sum()):,} touched, "
              f"checkpoint written ({time.time() - t:.0f}s)", flush=True)
    del geoms
    gc.collect()
    print(f"  layer total {time.time() - t0:.0f}s", flush=True)
    return n_repaired


def assemble(grain):
    df = None
    repairs = {}
    for layer, prefix in LAYERS.items():
        c = pd.read_csv(checkpoint_path(layer, grain), dtype={"GEOID": str})
        repairs[layer] = int(c.pop("invalid_repaired").iloc[0])
        c[f"{prefix}_any"] = c[f"{prefix}_any"].astype("Int64")
        df = c if df is None else df.merge(c, on="GEOID", how="outer", validate="1:1")
    return df.sort_values("GEOID").reset_index(drop=True), repairs


def validate(grain, df):
    sec(f"VALIDATION: {grain}")
    ok = len(df) == EXPECTED[grain]
    print(f"rows: {len(df):,} (expected {EXPECTED[grain]:,}) -> {'OK' if ok else 'MISMATCH'}")
    print(f"GEOID all string, prefix 12086: {df.GEOID.str.startswith('12086').all()}, "
          f"unique: {df.GEOID.is_unique}")
    share_cols = [c for c in df if c.endswith("_area_share")]
    for c in share_cols:
        s = df[c]
        outside = s[(s < 0) | (s > 1)]
        any_c = c.replace("_area_share", "_any")
        print(f"  {c:20s} NA {s.isna().sum()}  zero {(s == 0).sum():>5,}  "
              f">0 {(s > 0).sum():>5,}  mean {s.mean():.4f}  max {s.max():.6f}  "
              f"outside [0,1]: {len(outside)}  any=1: {int(df[any_c].sum()):,}")
        if len(outside):
            print(df.loc[outside.index, ["GEOID", c]].to_string(index=False))
    na = df[df[share_cols].isna().any(axis=1)]
    print(f"units with NA share (ALAND == 0): {na.GEOID.tolist()}")

    print(f"\nper scenario (entirely inundated = share >= {FULL_SHARE}):")
    for c in share_cols:
        s = df[c].dropna()
        print(f"  {c:20s} dry {(s == 0).sum():>5,}  entirely inundated "
              f"{(s >= FULL_SHARE).sum():>4,}  mean {s.mean():.4f}  "
              f"median {s.median():.4f}  median among wet {s[s > 0].median():.4f}")

    print("\ndry -> wet between consecutive slr scenarios:")
    for lo, hi in zip(SLR_SEQUENCE, SLR_SEQUENCE[1:]):
        a, b = df[f"{lo}_any"], df[f"{hi}_any"]
        print(f"  {lo} -> {hi}: dry->wet {int(((a == 0) & (b == 1)).sum()):,}  "
              f"wet->dry {int(((a == 1) & (b == 0)).sum()):,} (must be 0)")

    print("\nmonotonicity across slr scenarios (tolerance 1e-9):")
    for lo, hi in zip(SLR_SEQUENCE, SLR_SEQUENCE[1:]):
        a, b = df[f"{lo}_area_share"], df[f"{hi}_area_share"]
        bad = df[(b < a - 1e-9)]
        print(f"  {hi} >= {lo}: {len(bad)} violations"
              + (f", largest drop {(a - b)[bad.index].max():.6f}" if len(bad) else ""))
        if len(bad):
            print(bad[["GEOID", f"{lo}_area_share", f"{hi}_area_share"]]
                  .head(20).to_string(index=False))


def check_nesting(tract, bg):
    """Block groups tile tracts, so wet BGs must sit in wet tracts and the
    inundated land area of a tract must equal the sum over its block groups."""
    sec("CROSS-GRAIN NESTING: block groups within tracts")
    aland = {g: load_units(g).set_index("GEOID")["ALAND"] for g in ("tract", "bg")}
    parent = bg.GEOID.str[:11]
    print(f"every BG's parent tract present: {parent.isin(tract.GEOID).all()}")
    for prefix in LAYERS.values():
        wet_t = set(tract.GEOID[tract[f"{prefix}_any"] == 1])
        wet_bg = bg[bg[f"{prefix}_any"] == 1]
        orphans = wet_bg.GEOID[~wet_bg.GEOID.str[:11].isin(wet_t)].tolist()
        empty = sorted(wet_t - set(wet_bg.GEOID.str[:11]))
        t_area = (tract.set_index("GEOID")[f"{prefix}_area_share"]
                  * aland["tract"]).fillna(0)
        bg_area = ((bg.set_index("GEOID")[f"{prefix}_area_share"] * aland["bg"])
                   .fillna(0).groupby(lambda g: g[:11]).sum())
        gap = (t_area - bg_area.reindex(t_area.index, fill_value=0)).abs().max()
        print(f"  {prefix}: wet BGs in dry tracts {len(orphans)} {orphans[:10]}  "
              f"wet tracts with no wet BG {len(empty)} {empty[:10]}  "
              f"max |tract - sum BG| area {gap:.2f} m2")


def compare_slr_low(grain, df):
    sec(f"SLR vs LOW at 3 ft: {grain}")
    d = df.dropna(subset=["slr_3ft_area_share", "low_3ft_area_share"])
    s, l = d["slr_3ft_area_share"], d["low_3ft_area_share"]
    print(f"units: {len(d):,}")
    print(f"mean share  slr {s.mean():.4f}  low {l.mean():.4f}  "
          f"slr+low {(s + l).mean():.4f}")
    print(f"units touched  slr {(s > 0).sum():,}  low {(l > 0).sum():,}  "
          f"either {((s > 0) | (l > 0)).sum():,}  low-only {((s == 0) & (l > 0)).sum():,}")
    print(f"Pearson r  {s.corr(l):.3f}")
    print(f"Spearman   {s.corr(l, method='spearman'):.3f}")
    # does adding the unconnected layer re-rank units?
    combo = s + l
    print(f"Spearman slr vs slr+low {s.corr(combo, method='spearman'):.3f}")
    rs = s.rank(ascending=False, method="min")
    rc = combo.rank(ascending=False, method="min")
    shift = (rs - rc).abs()
    print(f"rank shift slr -> slr+low: median {shift.median():.0f}, "
          f"90th pct {shift.quantile(.9):.0f}, max {shift.max():.0f}")
    for k in (10, 50, 100):
        top_s = set(d.GEOID[rs <= k])
        top_c = set(d.GEOID[rc <= k])
        top_l = set(d.GEOID[l.rank(ascending=False, method='min') <= k])
        print(f"top-{k:<3d} overlap: slr vs slr+low {len(top_s & top_c)}/{k}, "
              f"slr vs low {len(top_s & top_l)}/{k}")


def top_tracts(df):
    sec("GEOGRAPHY SANITY: top 10 tracts by slr_3ft_area_share")
    places = gpd.read_file(f"zip://{BOUNDARY_DIR / 'tl_2024_12_place.zip'}").to_crs(AREA_CRS)
    tr = load_units("tract").to_crs(AREA_CRS)
    top = df.nlargest(10, "slr_3ft_area_share")[
        ["GEOID", "slr_1ft_area_share", "slr_3ft_area_share",
         "slr_6ft_area_share", "low_3ft_area_share"]]
    pts = tr.set_index("GEOID").loc[top.GEOID].representative_point()
    pts = gpd.GeoDataFrame(geometry=pts.values, index=pts.index, crs=AREA_CRS)
    j = gpd.sjoin(pts, places[["NAME", "geometry"]], how="left", predicate="within")
    j = j[~j.index.duplicated()]
    top["place"] = top.GEOID.map(j["NAME"]).fillna("(unincorporated, no CDP)")
    top["ALAND_km2"] = top.GEOID.map(tr.set_index("GEOID")["ALAND"] / 1e6).round(2)
    print(top.round(3).to_string(index=False))


def main():
    if not GPKG.exists():
        raise SystemExit(f"GeoPackage not found at {GPKG}")
    CHECKPOINTS.mkdir(parents=True, exist_ok=True)
    sec("UNITS AND LAND MASK")
    units, county_land, county_bbox = load_land_units()
    for grain, u in units.items():
        print(f"  {grain}: {len(u):,} units, ALAND == 0: "
              f"{u.GEOID[u.ALAND == 0].tolist()}")

    for layer, prefix in LAYERS.items():
        process_layer(layer, prefix, units, county_land, county_bbox)

    missing = [str(checkpoint_path(l, g)) for l in LAYERS for g in ("tract", "bg")
               if not checkpoint_path(l, g).exists()]
    if missing:
        raise SystemExit(f"checkpoints missing, not assembling: {missing}")

    frames = {}
    for grain in ("tract", "bg"):
        df, repairs = assemble(grain)
        frames[grain] = df
        df.to_csv(OUT_FILES[grain], index=False)
        print(f"\nwrote {OUT_FILES[grain].name}: {len(df):,} rows x {df.shape[1]} cols")
    print(f"geometry repairs per layer (make_valid): {repairs}")

    for grain, df in frames.items():
        validate(grain, df)
        compare_slr_low(grain, df)
    check_nesting(frames["tract"], frames["bg"])
    top_tracts(frames["tract"])


if __name__ == "__main__":
    main()
