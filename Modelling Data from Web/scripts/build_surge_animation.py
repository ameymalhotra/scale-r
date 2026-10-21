"""Build the storm surge layer for the admin exposure animation (/admin/viz/exposure).

Source (see surge_inspection.md): NHC National Storm Surge Hazard Map v4,
reprocessed 06/2026, Maximum of MOMs, high tide, one uint8 GeoTIFF per
hurricane category 1 to 5. Classes 1-21 are depth above ground in 1 ft bins,
255 is nodata (on Miami-Dade land: not inundated), 99 is leveed area.

Output, written next to slr.png / heat.png in src/admin/viz/data/:
  surge.png   RGBA on the same extent and size as slr.png, rows in Web Mercator
              (Mapbox stretches image sources linearly in Mercator):
                R = 40 * first category that floods the pixel (0 = dry through Cat 5)
                G = depth class at Category 5 (0 = dry, 21 = more than 20 ft)
                B = 0, A = 255
  surge.json  extent, encoding and per-category county stats

Each output pixel takes the native 10 m pixel under its centre (nearest
neighbour; the classes are categorical). Areas are counted on the native grid,
land only (tracts minus TIGER areawater), as in process_surge.py. Project
counts sample the output image exactly as the browser does.

Usage: python scripts/build_surge_animation.py
"""
import json
import math
import sys
import urllib.request
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
import shapely
from PIL import Image
from rasterio.features import rasterize
from rasterio.windows import from_bounds

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scaler_projects import BOUNDARY_DIR  # noqa: E402
from allocation import load_units  # noqa: E402

BASE = Path(__file__).resolve().parent.parent
REPO = BASE.parent
SURGE_DIR = (BASE / "tract-level" / "Physical Indicators"
             / "US_SLOSH_MOM_Inundation_v4_20260617")
VIZ_DATA = REPO / "src" / "admin" / "viz" / "data"
PROJECTS_URL = ("https://mmlqltdcpsuxirbqhugw.supabase.co/storage/v1/object/public/"
                "project-data/projects_merged_conf1.geojson")

CATEGORIES = [1, 2, 3, 4, 5]
CODE_STEP = 40  # R value per category; wide spacing so Mapbox's colour lookup never blurs them
DEPTH_MIN, DEPTH_MAX = 1, 21


def raster_path(cat):
    return SURGE_DIR / f"us_Category{cat}_MOM_Inundation_HIGH.tif"


def merc_y(lat):
    return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


def inv_merc_y(y):
    return math.degrees(2 * math.atan(math.exp(y)) - math.pi / 2)


def main():
    slr = json.loads((VIZ_DATA / "slr.json").read_text())
    (west, north), (east, _), (_, south), _ = slr["coordinates"]
    out_w, out_h = Image.open(VIZ_DATA / "slr.png").size

    with rasterio.open(raster_path(1)) as r:
        pad = 2 * r.res[0]
        win = from_bounds(west - pad, south - pad, east + pad, north + pad, r.transform)
        win = win.round_offsets().round_lengths()
        tf = r.window_transform(win)
        crs = r.crs
        pixel_m2 = (r.res[0] * 111320 * math.cos(math.radians((north + south) / 2))) * (r.res[1] * 110574)
    shape = (int(win.height), int(win.width))
    print(f"native window {shape[1]:,} x {shape[0]:,}, ~{pixel_m2:.1f} m2 per pixel", flush=True)

    # Land mask: tracts minus TIGER areawater, pixel centres, on the native grid.
    water = gpd.read_file(f"zip://{BOUNDARY_DIR / 'tl_2024_12086_areawater.zip'}").to_crs(crs)
    tracts = load_units("tract").to_crs(crs)
    land_geom = shapely.difference(
        shapely.union_all(shapely.make_valid(tracts.geometry.values)),
        shapely.union_all(shapely.make_valid(water.geometry.values)))
    land = rasterize([(land_geom, 1)], out_shape=shape, transform=tf, fill=0, dtype="uint8").astype(bool)
    land_pixels = int(land.sum())
    print(f"county land {land_pixels * pixel_m2 / 1e6:,.1f} km2", flush=True)

    first = np.zeros(shape, dtype=np.uint8)
    depth5 = np.zeros(shape, dtype=np.uint8)
    flooded_prev = np.zeros(shape, dtype=bool)
    stats, receded = [], {}
    for cat in CATEGORIES:
        with rasterio.open(raster_path(cat)) as r:
            v = r.read(1, window=from_bounds(*rasterio.transform.array_bounds(*shape, tf)[:4], r.transform)
                       .round_offsets().round_lengths(), boundless=True, fill_value=255)
        flooded = (v >= DEPTH_MIN) & (v <= DEPTH_MAX) & land
        first[flooded & (first == 0)] = cat
        # MOM envelopes are built per category, so a few cells flooded at one
        # category can be dry at the next; the animation keeps them flooded.
        receded[cat] = int((flooded_prev & ~flooded).sum())
        flooded_prev |= flooded
        if cat == 5:
            depth5 = np.where(flooded, v, 0).astype(np.uint8)
        km2 = flooded_prev.sum() * pixel_m2 / 1e6
        stats.append({"category": cat, "km2": round(float(km2), 1),
                      "pct_land": round(100 * float(flooded_prev.sum()) / land_pixels, 1)})
        print(f"  cat {cat}: {km2:,.1f} km2 cumulative, {receded[cat]:,} pixels dry again", flush=True)
        del v, flooded

    # Output grid: columns linear in longitude, rows linear in Mercator y.
    cols = ((west + (np.arange(out_w) + 0.5) / out_w * (east - west)) - tf.c) / tf.a
    top, span = merc_y(north), merc_y(north) - merc_y(south)
    lats = np.array([inv_merc_y(top - (i + 0.5) / out_h * span) for i in range(out_h)])
    rows = (lats - tf.f) / tf.e
    ci = np.clip(np.floor(cols).astype(int), 0, shape[1] - 1)
    ri = np.clip(np.floor(rows).astype(int), 0, shape[0] - 1)
    r_band = first[np.ix_(ri, ci)] * CODE_STEP
    g_band = depth5[np.ix_(ri, ci)]
    rgba = np.dstack([r_band, g_band, np.zeros_like(r_band), np.full_like(r_band, 255)]).astype(np.uint8)
    Image.fromarray(rgba, "RGBA").save(VIZ_DATA / "surge.png", optimize=True)

    # Project counts, sampled from the image the browser uses.
    with urllib.request.urlopen(PROJECTS_URL) as resp:
        features = json.load(resp)["features"]
    firsts = []
    for f in features:
        if f["properties"].get("Project__1") == "Planned":
            continue
        lng, lat = f["geometry"]["coordinates"][:2]
        c = math.floor((lng - west) / (east - west) * out_w)
        rr = math.floor((top - merc_y(lat)) / span * out_h)
        code = int(rgba[rr, c, 0]) if 0 <= c < out_w and 0 <= rr < out_h else 0
        firsts.append(code // CODE_STEP)
    for s in stats:
        s["projects"] = sum(1 for x in firsts if 0 < x <= s["category"])

    meta = {
        "source": "NHC National Storm Surge Hazard Map v4 (reprocessed 06/2026), "
                  "Maximum of MOMs, high tide, Categories 1-5",
        "encoding": {
            "red": f"{CODE_STEP} * first category that floods the pixel; 0 = dry through Category 5",
            "green": "depth class at Category 5: 1 = under 1 ft, n = n-1 to n ft, 21 = more than 20 ft; 0 = dry",
            "code_step": CODE_STEP,
        },
        "resolution": "native ~10 m, shown on the slr.png grid (~30 m), nearest neighbour",
        "land_mask": "Census tracts minus TIGER/Line 2024 area water",
        "county_land_km2": round(land_pixels * pixel_m2 / 1e6, 1),
        "projects_counted": len(firsts),
        "pixels_dry_again": receded,
        "coordinates": slr["coordinates"],
        "stats": stats,
    }
    (VIZ_DATA / "surge.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
