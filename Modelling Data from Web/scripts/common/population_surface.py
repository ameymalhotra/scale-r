"""Block-level population surface for the population exposure layers (prompt 21).

The same logic as load_blocks() in build_population_exposure.py (the website
Exposure page script), returned in a chosen CRS. It is a copy rather than an
import because that script hard-codes Web Mercator and must not be changed;
keep the two in step if either is edited.

  how many  ACS 2020-2024 total population per block group (B01003), via
            allocation.load_population
  where     Census 2020 blocks (tl_2020_12_tabblock20, POP20): each block
            group's ACS count is split across its blocks in proportion to their
            2020 counts (land area where a block group was empty in 2020)
  land      block minus every TIGER 2024 areawater feature; a populated block
            entirely under mapped water keeps its full shape
"""
import math

import geopandas as gpd
import numpy as np
import shapely

from allocation import load_population
from scaler_projects import BOUNDARY_DIR

BLOCKS_ZIP = BOUNDARY_DIR / "tl_2020_12_tabblock20.zip"
WATER_ZIP = BOUNDARY_DIR / "tl_2024_12086_areawater.zip"


def load_blocks(crs):
    """Populated blocks in `crs` with residents ("people") and land geometry ("land")."""
    blocks = gpd.read_file(f"zip://{BLOCKS_ZIP}", where="COUNTYFP20='086'")
    blocks["bg"] = blocks["GEOID20"].str[:12]
    acs = load_population("bg").set_index("GEOID")["population"].fillna(0)
    missing = set(blocks["bg"]) ^ set(acs.index)
    if missing:
        raise SystemExit(f"block groups do not match between 2020 blocks and ACS: {sorted(missing)[:5]}")

    pop20 = blocks["POP20"].astype(float)
    bg_pop20 = pop20.groupby(blocks["bg"]).transform("sum")
    bg_land = blocks["ALAND20"].astype(float).groupby(blocks["bg"]).transform("sum")
    weight = np.where(bg_pop20 > 0, pop20 / bg_pop20.where(bg_pop20 > 0, 1),
                      blocks["ALAND20"] / bg_land.where(bg_land > 0, 1))
    blocks["people"] = blocks["bg"].map(acs).to_numpy() * weight
    total = float(acs.sum())
    if not math.isclose(blocks["people"].sum(), total, rel_tol=1e-9):
        raise SystemExit(f"block allocation lost people: {blocks['people'].sum():,.1f} vs {total:,.0f}")

    blocks = blocks[blocks["people"] > 0].to_crs(crs).reset_index(drop=True)
    water = gpd.read_file(f"zip://{WATER_ZIP}").to_crs(crs)
    water_union = shapely.union_all(shapely.make_valid(water.geometry.values))
    geoms = shapely.make_valid(blocks.geometry.values)
    land = shapely.difference(geoms, water_union)
    blocks["land"] = np.where(shapely.is_empty(land), geoms, land)
    print(f"{len(blocks):,} populated blocks, {total:,.0f} residents", flush=True)
    return blocks, total
