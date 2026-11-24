"""
Build a Miami-Dade Land Surface Temperature (LST) layer for /admin/layers.

Pipeline:
  1. Search Landsat 8/9 Collection 2 Level-2 scenes (Microsoft Planetary Computer)
     for the chosen summer months and years.
  2. Warp each scene's surface temperature band (lwir11 / ST_B10) and QA band
     onto one 30 m UTM 17N grid covering the county, dropping fill, cloud,
     dilated cloud, cirrus, cloud shadow and water pixels.
  3. Take the per-pixel median across scenes (pixels need --min-obs clear
     observations) and convert to degrees Fahrenheit.
  4. Clip Miami-Dade census block groups (TIGER 2024) to land, compute the mean,
     max and valid-pixel share of the composite per block group, and write a
     simplified EPSG:4326 GeoJSON. lst_anomaly_f is relative to the average of
     all block-group means.

Usage:
  uv venv --python 3.12 scripts/python/.venv-lst
  VIRTUAL_ENV=scripts/python/.venv-lst uv pip install -r scripts/python/requirements.txt
  scripts/python/.venv-lst/bin/python scripts/python/build_lst_layer.py

Outputs (in --out-dir, default output/lst/):
  lst_blockgroups_miami_dade.geojson   upload this on /admin/layers
  lst_composite_f.tif                  30 m composite in degrees F, for QA
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import numpy as np
import planetary_computer
import pystac_client
import rasterio
import shapefile
import shapely
from pyproj import Transformer
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.features import rasterize
from rasterio.transform import from_origin
from rasterio.warp import reproject
from shapely.geometry import mapping, shape

REPO_ROOT = Path(__file__).resolve().parents[2]
BOUNDARIES = REPO_ROOT / "Modelling Data from Web" / "data" / "raw" / "boundaries"
STAC_URL = "https://planetarycomputer.microsoft.com/api/stac/v1"

STATE_FP = "12"
COUNTY_FP = "086"
UTM_CRS = CRS.from_epsg(32617)
PIXEL = 30.0
# Landsat Collection 2 UTM pixel edges fall on multiples of 30 m offset by 15 m.
GRID_OFFSET = 15.0

ST_SCALE = 0.00341802
ST_OFFSET = 149.0
# QA_PIXEL bits: 0 fill, 1 dilated cloud, 2 cirrus, 3 cloud, 4 cloud shadow, 7 water.
QA_REJECT_MASK = (1 << 0) | (1 << 1) | (1 << 2) | (1 << 3) | (1 << 4) | (1 << 7)

GDAL_ENV = {
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "GDAL_HTTP_MULTIRANGE": "YES",
    "GDAL_HTTP_MERGE_CONSECUTIVE_RANGES": "YES",
    "GDAL_HTTP_MAX_RETRY": "5",
    "GDAL_HTTP_RETRY_DELAY": "2",
    "VSI_CACHE": "TRUE",
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--years", default="2021-2024", help="Year or inclusive range, e.g. 2023 or 2021-2024")
    p.add_argument("--months", default="6-9", help="Inclusive month range, e.g. 6-9 for June to September")
    p.add_argument("--max-cloud", type=float, default=30.0, help="Maximum scene cloud cover in percent")
    p.add_argument("--min-obs", type=int, default=3, help="Clear observations a pixel needs to be kept")
    p.add_argument("--min-valid-pct", type=float, default=20.0, help="Block groups below this valid share get nulls")
    p.add_argument("--simplify-m", type=float, default=10.0, help="Geometry simplification tolerance in metres")
    p.add_argument("--workers", type=int, default=4, help="Parallel scene downloads")
    p.add_argument("--no-water-clip", action="store_true", help="Keep block-group polygons over open water")
    p.add_argument("--rebuild", action="store_true", help="Ignore a cached composite and rebuild it")
    p.add_argument("--out-dir", type=Path, default=REPO_ROOT / "output" / "lst")
    return p.parse_args()


def parse_range(text: str) -> tuple[int, int]:
    lo, _, hi = text.partition("-")
    return int(lo), int(hi or lo)


def period_label(years: tuple[int, int], months: tuple[int, int]) -> str:
    names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    m = names[months[0] - 1] if months[0] == months[1] else f"{names[months[0] - 1]}-{names[months[1] - 1]}"
    y = str(years[0]) if years[0] == years[1] else f"{years[0]}-{years[1]}"
    return f"{m} {y} Landsat 8/9"


# ── Boundaries ──────────────────────────────────────────────────────────────


def to_utm(geom):
    t = Transformer.from_crs("EPSG:4269", UTM_CRS, always_xy=True)
    return shapely.transform(geom, lambda xy: np.column_stack(t.transform(xy[:, 0], xy[:, 1])))


def to_wgs84(geom):
    t = Transformer.from_crs(UTM_CRS, "EPSG:4326", always_xy=True)
    return shapely.transform(geom, lambda xy: np.column_stack(t.transform(xy[:, 0], xy[:, 1])))


def tract_label(tractce: str) -> str:
    whole, dec = int(tractce[:4]), tractce[4:]
    return f"{whole}" if dec == "00" else f"{whole}.{dec}"


def load_block_groups(clip_water: bool) -> list[dict]:
    reader = shapefile.Reader(str(BOUNDARIES / "tl_2024_12_bg.zip"))
    groups = []
    for sr in reader.iterShapeRecords():
        rec = sr.record.as_dict()
        if rec["STATEFP"] != STATE_FP or rec["COUNTYFP"] != COUNTY_FP or rec["ALAND"] <= 0:
            continue
        geom = shapely.make_valid(to_utm(shape(sr.shape.__geo_interface__)))
        groups.append(
            {
                "GEOID": rec["GEOID"],
                "NAME": f"Block Group {rec['BLKGRPCE']}, Tract {tract_label(rec['TRACTCE'])}",
                "geom": geom,
            }
        )
    if not groups:
        sys.exit("No Miami-Dade block groups found in tl_2024_12_bg.zip")

    if clip_water:
        water_reader = shapefile.Reader(str(BOUNDARIES / "tl_2024_12086_areawater.zip"))
        water = [shapely.make_valid(to_utm(shape(s.__geo_interface__))) for s in water_reader.shapes()]
        tree = shapely.STRtree(water)
        for g in groups:
            hits = tree.query(g["geom"], predicate="intersects")
            if len(hits):
                g["geom"] = shapely.make_valid(g["geom"].difference(shapely.union_all([water[i] for i in hits])))
        groups = [g for g in groups if not g["geom"].is_empty and g["geom"].area > 0]
    print(f"Block groups: {len(groups)}")
    return groups


def county_grid(groups: list[dict]) -> tuple[rasterio.Affine, int, int]:
    minx, miny, maxx, maxy = shapely.union_all([g["geom"] for g in groups]).bounds
    minx = math.floor((minx - GRID_OFFSET) / PIXEL) * PIXEL + GRID_OFFSET - PIXEL
    maxy = math.ceil((maxy - GRID_OFFSET) / PIXEL) * PIXEL + GRID_OFFSET + PIXEL
    width = int(math.ceil((maxx - minx) / PIXEL)) + 1
    height = int(math.ceil((maxy - miny) / PIXEL)) + 1
    return from_origin(minx, maxy, PIXEL, PIXEL), width, height


# ── Landsat composite ───────────────────────────────────────────────────────


def search_scenes(groups, years, months, max_cloud) -> list:
    bbox = to_wgs84(shapely.union_all([g["geom"] for g in groups]).envelope).bounds
    catalog = pystac_client.Client.open(STAC_URL, modifier=planetary_computer.sign_inplace)
    items = []
    for year in range(years[0], years[1] + 1):
        last_day = 30 if months[1] in (4, 6, 9, 11) else (28 if months[1] == 2 else 31)
        search = catalog.search(
            collections=["landsat-c2-l2"],
            bbox=bbox,
            datetime=f"{year}-{months[0]:02d}-01/{year}-{months[1]:02d}-{last_day}",
            query={"eo:cloud_cover": {"lt": max_cloud}, "platform": {"in": ["landsat-8", "landsat-9"]}},
        )
        items.extend(search.items())
    items.sort(key=lambda i: i.datetime)
    print(f"Scenes: {len(items)}")
    return items


def warp_band(href: str, transform, width: int, height: int, dtype) -> np.ndarray:
    out = np.zeros((height, width), dtype=dtype)
    with rasterio.open(href) as src:
        reproject(
            source=rasterio.band(src, 1),
            destination=out,
            dst_transform=transform,
            dst_crs=UTM_CRS,
            src_nodata=0,
            dst_nodata=0,
            resampling=Resampling.nearest,
        )
    return out


def clear_scene(item, transform, width, height) -> np.ndarray:
    """Surface temperature DN with rejected pixels set to 0."""
    item = planetary_computer.sign(item)
    with rasterio.Env(**GDAL_ENV):
        st = warp_band(item.assets["lwir11"].href, transform, width, height, np.uint16)
        qa = warp_band(item.assets["qa_pixel"].href, transform, width, height, np.uint16)
    st[(qa == 0) | ((qa & QA_REJECT_MASK) != 0)] = 0
    return st


def build_composite(items, transform, width, height, min_obs, workers, scratch: Path) -> np.ndarray:
    stack = np.lib.format.open_memmap(scratch, mode="w+", dtype=np.uint16, shape=(len(items), height, width))
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(clear_scene, item, transform, width, height): i for i, item in enumerate(items)}
        for fut in as_completed(futures):
            i = futures[fut]
            try:
                stack[i] = fut.result()
            except Exception as exc:  # one bad scene should not sink the composite
                print(f"  skipped {items[i].id}: {exc}")
                stack[i] = 0
            done += 1
            clear = np.count_nonzero(stack[i]) / stack[i].size * 100
            print(f"  [{done}/{len(items)}] {items[i].id}  clear {clear:.0f}%")

    composite = np.full((height, width), np.nan, dtype=np.float32)
    rows = 256
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for r0 in range(0, height, rows):
            block = stack[:, r0 : r0 + rows].astype(np.float32)
            block[block == 0] = np.nan
            obs = np.sum(np.isfinite(block), axis=0)
            med = np.nanmedian(block, axis=0)
            med[obs < min_obs] = np.nan
            composite[r0 : r0 + rows] = med
    del stack
    scratch.unlink(missing_ok=True)

    kelvin = composite * ST_SCALE + ST_OFFSET
    return ((kelvin - 273.15) * 9.0 / 5.0 + 32.0).astype(np.float32)


def write_composite(path: Path, data: np.ndarray, transform) -> None:
    profile = {
        "driver": "GTiff",
        "height": data.shape[0],
        "width": data.shape[1],
        "count": 1,
        "dtype": "float32",
        "crs": UTM_CRS,
        "transform": transform,
        "nodata": np.nan,
        "compress": "deflate",
        "predictor": 3,
        "tiled": True,
    }
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(data, 1)
        dst.set_band_description(1, "Land surface temperature (degrees F), median composite")


# ── Block-group statistics ──────────────────────────────────────────────────


def zonal_stats(groups, composite, transform):
    labels = rasterize(
        ((g["geom"], i + 1) for i, g in enumerate(groups)),
        out_shape=composite.shape,
        transform=transform,
        fill=0,
        dtype="int32",
    ).ravel()
    values = composite.ravel()
    n = len(groups) + 1
    valid = np.isfinite(values) & (labels > 0)

    total = np.bincount(labels, minlength=n)
    count = np.bincount(labels[valid], minlength=n)
    sums = np.bincount(labels[valid], weights=values[valid], minlength=n)
    maxes = np.full(n, -np.inf)
    np.maximum.at(maxes, labels[valid], values[valid])
    return total, count, sums, maxes


def anomaly_baseline(total, count, sums, min_valid_pct) -> float:
    """Average of block-group means. A pixel-weighted county mean is dominated by the cooler Everglades."""
    with np.errstate(divide="ignore", invalid="ignore"):
        valid_pct = np.where(total > 0, count / total * 100, 0)
        means = sums / count
    keep = (count > 0) & (valid_pct >= min_valid_pct)
    keep[0] = False
    return float(means[keep].mean())


def round_coords(obj, ndigits=5):
    if isinstance(obj, (list, tuple)):
        if obj and isinstance(obj[0], (int, float)):
            return [round(v, ndigits) for v in obj]
        return [round_coords(o, ndigits) for o in obj]
    return obj


def build_features(groups, total, count, sums, maxes, baseline, args, period):
    features = []
    for i, g in enumerate(groups):
        k = i + 1
        valid_pct = (count[k] / total[k] * 100) if total[k] else 0.0
        has_data = count[k] > 0 and valid_pct >= args.min_valid_pct
        mean_f = sums[k] / count[k] if has_data else None
        props = {
            "GEOID": g["GEOID"],
            "NAME": g["NAME"],
            "lst_mean_f": round(mean_f, 1) if has_data else None,
            "lst_mean_c": round((mean_f - 32) * 5 / 9, 1) if has_data else None,
            "lst_max_f": round(float(maxes[k]), 1) if has_data else None,
            "lst_anomaly_f": round(mean_f - baseline, 1) if has_data else None,
            "valid_pct": round(valid_pct, 1),
            "period": period,
        }
        geom = g["geom"].simplify(args.simplify_m, preserve_topology=True)
        geom = shapely.make_valid(to_wgs84(geom))
        polys = [p for p in getattr(geom, "geoms", [geom]) if p.geom_type in ("Polygon", "MultiPolygon")]
        if not polys:
            continue
        geom = shapely.union_all(polys) if len(polys) > 1 else polys[0]
        gj = mapping(geom)
        features.append(
            {"type": "Feature", "properties": props, "geometry": {"type": gj["type"], "coordinates": round_coords(gj["coordinates"])}}
        )
    return features


def main() -> None:
    args = parse_args()
    years, months = parse_range(args.years), parse_range(args.months)
    period = period_label(years, months)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    tif_path = args.out_dir / "lst_composite_f.tif"
    out_path = args.out_dir / "lst_blockgroups_miami_dade.geojson"

    groups = load_block_groups(clip_water=not args.no_water_clip)
    transform, width, height = county_grid(groups)
    print(f"Grid: {width} x {height} px at {PIXEL:.0f} m")

    if tif_path.exists() and not args.rebuild:
        print(f"Using cached composite {tif_path.relative_to(REPO_ROOT)} (pass --rebuild to refresh)")
        with rasterio.open(tif_path) as src:
            if src.transform != transform or src.shape != (height, width):
                sys.exit("Cached composite grid does not match; rerun with --rebuild")
            composite = src.read(1)
    else:
        items = search_scenes(groups, years, months, args.max_cloud)
        if not items:
            sys.exit("No Landsat scenes matched the filters")
        composite = build_composite(
            items, transform, width, height, args.min_obs, args.workers, args.out_dir / "_stack.npy"
        )
        write_composite(tif_path, composite, transform)
        print(f"Wrote {tif_path.relative_to(REPO_ROOT)}")

    total, count, sums, maxes = zonal_stats(groups, composite, transform)
    baseline = anomaly_baseline(total, count, sums, args.min_valid_pct)
    features = build_features(groups, total, count, sums, maxes, baseline, args, period)
    with open(out_path, "w") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f, separators=(",", ":"))

    means = np.array([ft["properties"]["lst_mean_f"] for ft in features if ft["properties"]["lst_mean_f"] is not None])
    nulls = sum(ft["properties"]["lst_mean_f"] is None for ft in features)
    print(f"Wrote {out_path.relative_to(REPO_ROOT)} ({os.path.getsize(out_path) / 1e6:.1f} MB, {len(features)} features)")
    print(f"County pixel mean: {float(np.nanmean(composite)):.1f} F; anomaly baseline (block-group average): {baseline:.1f} F")
    print(f"Block-group means: min {means.min():.1f}  median {np.median(means):.1f}  max {means.max():.1f} F; {nulls} null")


if __name__ == "__main__":
    main()
