"""Add residents exposed to the Exposure page stats (/exposure).

Counts are read off the animation images themselves (slr.png, surge.png,
heat.png), so they match what the map draws at every step.

Population:
  how many  ACS 2020-2024 total population per block group (B01003, the same
            2,738,356 the gap map uses), via allocation.load_population
  where     Census 2020 blocks (TIGER/Line tl_2020_12_tabblock20, POP20):
            each block group's ACS count is split across its blocks in
            proportion to their 2020 counts, then spread evenly over each
            block's land (block minus TIGER 2024 areawater)

Each image pixel whose centre falls on a block's land gets an equal share of
that block's residents. Blocks too small to hold a pixel centre put all of
their residents on the pixel under their representative point, so the grid
total always equals the county total.

Inputs (git-ignored, in boundaries/):
  tl_2020_12_tabblock20.zip  from
    https://www2.census.gov/geo/tiger/TIGER2020/TABBLOCK20/tl_2020_12_tabblock20.zip
  tl_2024_12086_areawater.zip

Writes, in src/exposure/data/:
  slr.json    people, pct_people on each stats entry
  surge.json  people, pct_people on each stats entry
  heat.json   people_at_or_above {"80": n, ...}
  plus population_total / population_source / population_method on each.
  exposure_blocks.json
              every populated census block's land outline with its residents
              and residents exposed at every animation step, for the
              "Population exposure" view (see block_exposure)

Usage: python scripts/build_population_exposure.py
"""
import json
import math
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import shapely
from PIL import Image
from rasterio.features import rasterize
from rasterio.transform import from_bounds

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scaler_projects import BOUNDARY_DIR  # noqa: E402
from allocation import load_population  # noqa: E402

BASE = Path(__file__).resolve().parent.parent
VIZ_DATA = BASE.parent / "src" / "exposure" / "data"
BLOCKS_ZIP = BOUNDARY_DIR / "tl_2020_12_tabblock20.zip"
MERC = "EPSG:3857"

SLR_CODE_STEP = 18  # slr.png: 18 * (1 + 2 * first flooded level in ft)
SURGE_CODE_STEP = 40  # surge.png: 40 * first flooding category
SOURCE = ("ACS 2020-2024 5-year total population by block group (B01003), "
          "placed with Census 2020 block counts (P1, TIGER/Line tabblock20)")
HEAT_STEPS = range(88, 126)  # whole degrees across the heat slider (125 down to 88 °F)
SIMPLIFY_M = 4  # block outline simplification, metres; well under one 30 m pixel
METHOD = ("Each block group's ACS population is split across its 2020 blocks in "
          "proportion to their 2020 counts and spread evenly over each block's land "
          "(block minus TIGER 2024 area water); summed over the animation image's "
          "pixels at each step.")


def merc_x(lng):
    return math.radians(lng) * 6378137


def merc_y(lat):
    return math.log(math.tan(math.pi / 4 + math.radians(lat) / 2)) * 6378137


def load_blocks():
    """Blocks in Web Mercator with their share of ACS 2020-2024 residents and land geometry."""
    blocks = gpd.read_file(f"zip://{BLOCKS_ZIP}", where="COUNTYFP20='086'")
    blocks["bg"] = blocks["GEOID20"].str[:12]
    acs = load_population("bg").set_index("GEOID")["population"].fillna(0)
    missing = set(blocks["bg"]) ^ set(acs.index)
    if missing:
        raise SystemExit(f"block groups do not match between 2020 blocks and ACS: {sorted(missing)[:5]}")

    pop20 = blocks["POP20"].astype(float)
    bg_pop20 = pop20.groupby(blocks["bg"]).transform("sum")
    bg_land = blocks["ALAND20"].astype(float).groupby(blocks["bg"]).transform("sum")
    # Block groups empty in 2020 but populated in ACS fall back to land area.
    weight = np.where(bg_pop20 > 0, pop20 / bg_pop20.where(bg_pop20 > 0, 1),
                      blocks["ALAND20"] / bg_land.where(bg_land > 0, 1))
    blocks["people"] = blocks["bg"].map(acs).to_numpy() * weight
    total = float(acs.sum())
    if not math.isclose(blocks["people"].sum(), total, rel_tol=1e-9):
        raise SystemExit(f"block allocation lost people: {blocks['people'].sum():,.1f} vs {total:,.0f}")

    blocks = blocks[blocks["people"] > 0].to_crs(MERC).reset_index(drop=True)
    water = gpd.read_file(f"zip://{BOUNDARY_DIR / 'tl_2024_12086_areawater.zip'}").to_crs(MERC)
    water_union = shapely.union_all(shapely.make_valid(water.geometry.values))
    geoms = shapely.make_valid(blocks.geometry.values)
    land = shapely.difference(geoms, water_union)
    # A populated block entirely under mapped water keeps its full shape.
    blocks["land"] = np.where(shapely.is_empty(land), geoms, land)
    print(f"{len(blocks):,} populated blocks, {total:,.0f} residents", flush=True)
    return blocks, total


def people_grid(blocks, total, coordinates, width, height):
    """Residents per pixel on an animation image's grid (columns linear in x, rows in Mercator y).

    Also returns, for per-block counts, each pixel's block (labels, 0 = none),
    each block's residents per pixel, and the (block, row, col) of blocks
    placed on a single pixel because they hold no pixel centre.
    """
    (west, north), (east, _), (_, south), _ = coordinates
    tf = from_bounds(merc_x(west), merc_y(south), merc_x(east), merc_y(north), width, height)
    labels = rasterize(((g, i + 1) for i, g in enumerate(blocks["land"])), out_shape=(height, width),
                       transform=tf, fill=0, dtype="int32")
    n = len(blocks)
    counts = np.bincount(labels.ravel(), minlength=n + 1)[1:]
    people = blocks["people"].to_numpy()
    per_pixel = np.concatenate([[0.0], np.divide(people, counts, out=np.zeros(n), where=counts > 0)])
    grid = per_pixel[labels]

    small = np.flatnonzero(counts == 0)
    placed = []
    if len(small):
        pts = shapely.point_on_surface(blocks.geometry.values[small])
        inv = ~tf
        for i, pt in zip(small, pts):
            col, row = inv * (pt.x, pt.y)
            r = min(max(int(row), 0), height - 1)
            c = min(max(int(col), 0), width - 1)
            grid[r, c] += people[i]
            placed.append((i, r, c))
    print(f"  grid {width}x{height}: {len(small):,} blocks placed by point, "
          f"{people[small].sum():,.0f} residents", flush=True)
    if not math.isclose(grid.sum(), total, rel_tol=1e-9):
        raise SystemExit(f"grid lost people: {grid.sum():,.1f} vs {total:,.0f}")
    return grid, labels, per_pixel, placed


def per_block(index, n, people_per_pixel, placed, people, reached):
    """Residents of each block whose pixels are reached (reached: bool grid)."""
    out = np.bincount(index, weights=people_per_pixel * reached.ravel(), minlength=n + 1)[1:]
    for i, r, c in placed:
        out[i] += people[i] * reached[r, c]
    return out


def block_exposure(blocks, main, heat_parts, slr, slr_ft, surge, surge_cat, temp):
    """Each populated block's land outline, land area and residents reached at every step.

    Counts come from the same pixels as the panel totals, so they add up to them.
    """
    n = len(blocks)
    people = blocks["people"].to_numpy()
    columns = [people]
    labels, per_pixel, placed = main
    index = labels.ravel()
    own = per_pixel[labels].ravel()
    columns += [per_block(index, n, own, placed, people, slr_ft <= s["ft"] + 1e-6) for s in slr["stats"]]
    columns += [per_block(index, n, own, placed, people, (surge_cat > 0) & (surge_cat <= s["category"]))
                for s in surge["stats"]]
    labels, per_pixel, placed = heat_parts
    index = labels.ravel()
    own = per_pixel[labels].ravel()
    columns += [per_block(index, n, own, placed, people, temp >= t) for t in HEAT_STEPS]
    table = np.rint(np.column_stack(columns)).astype(np.int64)

    # Land area from the Census (ALAND20); outlines are the land part, simplified, in lon/lat.
    area_km2 = np.maximum(blocks["ALAND20"].to_numpy(dtype=float), 1000) / 1e6
    outlines = gpd.GeoSeries(shapely.simplify(blocks["land"].values, SIMPLIFY_M, preserve_topology=True),
                             crs=MERC).to_crs("EPSG:4326")
    rows = []
    for i, geom in enumerate(outlines):
        if table[i, 0] <= 0 or geom.is_empty:
            continue
        shape = json.loads(shapely.to_geojson(shapely.set_precision(geom, 1e-5)))
        rows.append([blocks["GEOID20"].iat[i], round(float(area_km2[i]), 5), shape["type"],
                     shape["coordinates"], *table[i].tolist()])
    return {
        "columns": (["geoid", "land_km2", "type", "coordinates", "people"]
                    + [f"slr_{s['ft']}" for s in slr["stats"]]
                    + [f"surge_{s['category']}" for s in surge["stats"]]
                    + [f"heat_{t}" for t in HEAT_STEPS]),
        "source": SOURCE,
        "method": METHOD + " Outlines are each block's land (block minus area water), simplified by "
                  f"{SIMPLIFY_M} m; land area is the Census ALAND20 (at least 0.001 km2).",
        "blocks": rows,
    }


def red(path):
    return np.asarray(Image.open(path).convert("RGBA"))[..., 0].astype(np.int32)


def with_source(meta, total):
    meta["population_total"] = round(total)
    meta["population_source"] = SOURCE
    meta["population_method"] = METHOD
    return meta


def main():
    blocks, total = load_blocks()
    pct = lambda n: round(100 * n / total, 1)  # noqa: E731

    slr = json.loads((VIZ_DATA / "slr.json").read_text())
    surge = json.loads((VIZ_DATA / "surge.json").read_text())
    heat = json.loads((VIZ_DATA / "heat.json").read_text())
    if slr["coordinates"] != surge["coordinates"]:
        raise SystemExit("slr.png and surge.png are expected to share one grid")

    slr_code = red(VIZ_DATA / "slr.png")
    grid, *main_parts = people_grid(blocks, total, slr["coordinates"], slr_code.shape[1], slr_code.shape[0])

    # slr code v floods at (v / 18 - 1) / 2 ft; 0 is dry through 6 ft.
    slr_ft = np.where(slr_code > 0, (slr_code / SLR_CODE_STEP - 1) / 2, np.inf)
    for s in slr["stats"]:
        n = float(grid[slr_ft <= s["ft"] + 1e-6].sum())
        s["people"], s["pct_people"] = round(n), pct(n)

    surge_cat = red(VIZ_DATA / "surge.png") // SURGE_CODE_STEP
    for s in surge["stats"]:
        n = float(grid[(surge_cat > 0) & (surge_cat <= s["category"])].sum())
        s["people"], s["pct_people"] = round(n), pct(n)

    heat_code = red(VIZ_DATA / "heat.png")
    heat_grid, *heat_parts = people_grid(blocks, total, heat["coordinates"], heat_code.shape[1], heat_code.shape[0])
    lo, hi = heat["encoding"]["min_f"], heat["encoding"]["max_f"]
    temp = np.where(heat_code > 0, lo + (heat_code - 1) / 254 * (hi - lo), -np.inf)
    on_heat = float(heat_grid[heat_code > 0].sum())
    heat["people_at_or_above"] = {str(t): round(float(heat_grid[temp >= t].sum())) for t in range(80, 136)}
    heat["people_with_surface_temperature"] = round(on_heat)

    exposure = block_exposure(blocks, main_parts, heat_parts, slr, slr_ft, surge, surge_cat, temp)
    (VIZ_DATA / "exposure_blocks.json").write_text(json.dumps(exposure, separators=(",", ":")) + "\n")
    cols = exposure["columns"]
    sums = {c: sum(b[cols.index(c)] for b in exposure["blocks"]) for c in ("people", "slr_6.0", "surge_3", "heat_104")}
    print(f"blocks: {len(exposure['blocks']):,} outlines; totals {sums}", flush=True)

    for name, meta in (("slr", slr), ("surge", surge), ("heat", heat)):
        (VIZ_DATA / f"{name}.json").write_text(json.dumps(with_source(meta, total), indent=2) + "\n")

    print("slr:  ", [(s["ft"], s["people"], s["pct_people"]) for s in slr["stats"]])
    print("surge:", [(s["category"], s["people"], s["pct_people"]) for s in surge["stats"]])
    print("heat: ", {t: heat["people_at_or_above"][str(t)] for t in (88, 95, 100, 104, 110, 125)},
          f"(residents on pixels with a temperature: {on_heat:,.0f})")


if __name__ == "__main__":
    main()
