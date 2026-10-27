"""
Build the exposure-animation layers for the Exposure page (src/exposure).

  slr   NOAA OCM ocean-connected inundation, 0-6 ft above MHHW in half-foot
        steps, rasterised at 30 m over Miami-Dade land. Each pixel stores the
        first level that floods it, so one PNG drives the whole animation.
  heat  Landsat 8/9 land surface temperature composite (output/lst),
        reprojected to Web Mercator and packed into a grayscale PNG for a
        Mapbox image source.

Read-only on every input.
Run with the repo venv:  .venv/bin/python scripts/python/build_viz_exposure.py slr heat
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import geopandas as gpd
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = ROOT / "src" / "exposure" / "data"
TRACTS = ROOT / "public" / "femaindex-4326.geojson"
SLR_GPKG = ROOT / "Modelling Data from Web/tract-level/Physical Indicators/FL_SE_slr_data_dist/FL_SE_slr_final_dist.gpkg"
LST_TIF = ROOT / "output/lst/lst_composite_f.tif"
WATER_ZIP = ROOT / "Modelling Data from Web/boundaries/tl_2024_12086_areawater.zip"
PROJECTS_URL = "https://mmlqltdcpsuxirbqhugw.supabase.co/storage/v1/object/public/project-data/projects_merged_conf1.geojson"

METRIC = "EPSG:6346"  # UTM 17N, NAD83(2011): same as the SCALE-R SLR processing
LEVELS = [x / 2 for x in range(0, 13)]  # 0.0 .. 6.0 ft
SLR_CODE_STEP = 18
SLR_WORKERS = 4  # each worker holds one level's polygons in memory
SLR_RES_M = 30  # grid for the flood-level raster; matches the NOAA DEM-derived detail closely enough for display

# Temperature packing for the PNG: value 1..255 maps linearly onto this range.
HEAT_MIN_F, HEAT_MAX_F = 70.0, 135.0


def county_land() -> gpd.GeoSeries:
    """Miami-Dade tract polygons; used as a mask, so they need not be merged."""
    return gpd.read_file(TRACTS).to_crs(METRIC).geometry


def build_slr() -> None:
    import urllib.request

    import rasterio
    from PIL import Image
    from rasterio.features import rasterize
    from rasterio.transform import from_origin
    from rasterio.warp import Resampling, calculate_default_transform, reproject

    tracts = gpd.read_file(TRACTS).to_crs(METRIC)
    water = gpd.read_file(f"zip://{WATER_ZIP}").to_crs(METRIC)
    left, bottom, right, top = tracts.total_bounds
    width, height = int((right - left) // SLR_RES_M) + 1, int((top - bottom) // SLR_RES_M) + 1
    transform = from_origin(left, top, SLR_RES_M, SLR_RES_M)
    shape_ = (height, width)

    # County land = census tracts minus Census water features, as in slr_tract.csv.
    land = rasterize(((g, 1) for g in tracts.geometry), out_shape=shape_, transform=transform, dtype="uint8").astype(bool)
    land &= ~rasterize(((g, 1) for g in water.geometry), out_shape=shape_, transform=transform, dtype="uint8").astype(bool)
    pixel_km2 = SLR_RES_M ** 2 / 1e6
    land_km2 = land.sum() * pixel_km2

    with urllib.request.urlopen(PROJECTS_URL) as resp:
        projects = gpd.GeoDataFrame.from_features(json.load(resp)["features"], crs="EPSG:4326")
    projects = projects[projects["Project__1"] != "Planned"].to_crs(METRIC)
    rows, cols = rasterio.transform.rowcol(transform, projects.geometry.x, projects.geometry.y)
    rows, cols = np.clip(rows, 0, height - 1), np.clip(cols, 0, width - 1)

    # code = 1 + 2 * (first level in ft that floods the pixel); 0 = dry through 6 ft.
    # Written x18 to the PNG so Mapbox's 256-entry raster-color lookup never blurs
    # adjacent levels together.
    code = np.zeros(shape_, dtype="uint8")
    bbox = tuple(tracts.to_crs("EPSG:4269").total_bounds)
    # Rasterising NOAA's detailed polygons takes minutes per level, so levels run
    # in parallel and each result is cached; delete scripts/python/_viz_cache/ to force a rebuild.
    from concurrent.futures import ProcessPoolExecutor
    jobs = [(level, bbox, tuple(transform), shape_) for level in LEVELS]
    with ProcessPoolExecutor(max_workers=SLR_WORKERS) as pool:
        wet_levels = dict(zip(LEVELS, pool.map(_wet_level, *zip(*jobs))))
    stats = []
    for level in LEVELS:
        name = slr_layer(level)
        wet = wet_levels[level] & land
        code[wet & (code == 0)] = int(1 + 2 * level)
        flooded = code > 0
        stats.append({
            "ft": level,
            "km2": round(float(flooded.sum() * pixel_km2), 1),
            "pct_land": round(float(100 * flooded.sum() / land.sum()), 1),
            "projects": int(flooded[rows, cols].sum()),
        })
        print(f"{name}: {stats[-1]}", flush=True)

    # Reproject the level codes to Web Mercator for a Mapbox image source. Codes are
    # shifted up by one first: rasterio treats 0 as nodata and fills it from
    # neighbours, which would mark dry land as flooded.
    dst_t, dst_w, dst_h = calculate_default_transform(METRIC, "EPSG:3857", width, height, left, bottom, right, top)
    merc = np.zeros((dst_h, dst_w), dtype="uint8")
    reproject(code + 1, merc, src_transform=transform, src_crs=METRIC, dst_transform=dst_t, dst_crs="EPSG:3857",
              resampling=Resampling.nearest, src_nodata=0, dst_nodata=0)
    merc = np.where(merc > 0, merc - 1, 0)
    packed = (merc.astype(int) * SLR_CODE_STEP).astype("uint8")
    save_value_png(packed, OUT / "slr.png")

    meta = {
        "source": "NOAA Office for Coastal Management, Sea Level Rise Inundation Data (FL_SE), ocean-connected _slr_ layers",
        "datum": "MHHW",
        "levels_ft": LEVELS,
        "resolution_m": SLR_RES_M,
        "encoding": "pixel value = 18 * (1 + 2 * first flooded level in ft); 0 = dry through 6 ft. Spaced by 18 so Mapbox raster-color lookups never blur adjacent levels.",
        "land_mask": "Census tracts minus TIGER/Line 2024 area water",
        "county_land_km2": round(float(land_km2), 1),
        "projects_counted": int(len(projects)),
        "coordinates": corners(dst_t, dst_w, dst_h),
        "stats": stats,
    }
    (OUT / "slr.json").write_text(json.dumps(meta, indent=2))
    print(f"wrote slr.png ({(OUT / 'slr.png').stat().st_size / 1e6:.1f} MB) {dst_w}x{dst_h}")


def slr_layer(level: float) -> str:
    return f"FL_SE_slr_{int(level)}_{int(level * 10) % 10}ft"


def _wet_level(level, bbox, transform, shape_) -> np.ndarray:
    """Boolean grid of pixels under ocean-connected water at `level` ft (cached)."""
    from affine import Affine
    from rasterio.features import rasterize

    cache = HERE / "_viz_cache" / f"{slr_layer(level)}_{SLR_RES_M}m.npz"
    if cache.exists():
        return np.unpackbits(np.load(cache)["wet"])[: shape_[0] * shape_[1]].reshape(shape_).astype(bool)
    layer = gpd.read_file(SLR_GPKG, layer=slr_layer(level), bbox=bbox, engine="pyogrio").to_crs(METRIC)
    wet = rasterize(((g, 1) for g in layer.geometry), out_shape=shape_, transform=Affine(*transform[:6]),
                    dtype="uint8").astype(bool)
    cache.parent.mkdir(exist_ok=True)
    np.savez_compressed(cache, wet=np.packbits(wet))
    print(f"rasterised {slr_layer(level)}", flush=True)
    return wet


def save_value_png(values: np.ndarray, path: Path) -> None:
    """Grayscale value image for Mapbox raster-color; value 0 is made transparent
    by the colour rule, so the image itself is opaque."""
    from PIL import Image

    Image.fromarray(values, "L").convert("RGBA").save(path, optimize=True)


def corners(transform, width, height) -> list[list[float]]:
    from pyproj import Transformer

    to_ll = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
    left, top = transform * (0, 0)
    right, bottom = transform * (width, height)
    return [[round(c, 6) for c in to_ll.transform(x, y)] for x, y in [(left, top), (right, top), (right, bottom), (left, bottom)]]


def build_heat() -> None:
    import rasterio
    from PIL import Image
    from rasterio.warp import Resampling, calculate_default_transform, reproject

    with rasterio.open(LST_TIF) as src:
        dst_crs = "EPSG:3857"
        # 60 m keeps the PNG small while staying sharper than block groups.
        transform, width, height = calculate_default_transform(
            src.crs, dst_crs, src.width, src.height, *src.bounds, resolution=60)
        data = np.full((height, width), np.nan, dtype="float32")
        reproject(rasterio.band(src, 1), data, src_transform=src.transform, src_crs=src.crs,
                  dst_transform=transform, dst_crs=dst_crs, resampling=Resampling.average,
                  src_nodata=src.nodata, dst_nodata=np.nan)

    # Only show land inside the county.
    county = county_land().to_crs("EPSG:3857")
    from rasterio.features import geometry_mask
    outside = geometry_mask(county.geometry, out_shape=data.shape, transform=transform)
    data[outside] = np.nan

    valid = ~np.isnan(data)
    scaled = np.clip((data - HEAT_MIN_F) / (HEAT_MAX_F - HEAT_MIN_F), 0, 1) * 254 + 1
    save_value_png(np.where(valid, scaled, 0).astype("uint8"), OUT / "heat.png")

    vals = data[valid]
    meta = {
        "source": "Landsat 8/9 land surface temperature, median composite, June-September 2021-2024 (output/lst/lst_composite_f.tif)",
        "units": "degrees F",
        "resolution_m": 60,
        "encoding": {"min_f": HEAT_MIN_F, "max_f": HEAT_MAX_F, "value_range": [1, 255]},
        "coordinates": corners(transform, width, height),
        "percentiles_f": {str(p): round(float(np.percentile(vals, p)), 1) for p in (5, 25, 50, 75, 95, 99)},
        # Share of county land at or above each threshold, for the on-map readout.
        "share_at_or_above": {str(t): round(float((vals >= t).mean() * 100), 1) for t in range(80, 136)},
    }
    (OUT / "heat.json").write_text(json.dumps(meta, indent=2))
    print(f"wrote heat.png ({(OUT / 'heat.png').stat().st_size / 1e6:.1f} MB) {width}x{height}", meta["percentiles_f"])


if __name__ == "__main__":
    for job in sys.argv[1:] or ["slr", "heat"]:
        {"slr": build_slr, "heat": build_heat}[job]()
