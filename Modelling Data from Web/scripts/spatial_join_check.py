"""Step 4: point-in-polygon feasibility check of project pins against
Census TIGER/Line 2024 tract and block-group boundaries for Miami-Dade.

Counts only - it reports how many points land where, and how many geographic
units receive nothing. It does NOT write an aggregated table.

Boundaries: TIGER/Line 2024, Florida (state FIPS 12), downloaded to
boundaries/ by fetch_boundaries.sh. CRS EPSG:4269 (NAD83) as shipped; project
points are assumed WGS84/EPSG:4326 and are reprojected to match. The NAD83 vs
WGS84 difference is sub-meter here and cannot flip a tract assignment except
for a point sitting exactly on a boundary line.

Usage: python scripts/spatial_join_check.py
"""
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scaler_projects import BOUNDARY_DIR, ensure_output_dir, load_typed  # noqa: E402

COUNTY_FIPS = "086"
STATE_FIPS = "12"


def load_boundaries(zip_name, layer_label):
    path = BOUNDARY_DIR / zip_name
    if not path.exists():
        raise SystemExit(f"missing {path} - run scripts/fetch_boundaries.sh first")
    g = gpd.read_file(f"zip://{path}")
    g["GEOID"] = g["GEOID"].astype(str)
    md = g[(g["STATEFP"] == STATE_FIPS) & (g["COUNTYFP"] == COUNTY_FIPS)].copy()
    print(f"{layer_label}: {len(g)} statewide -> {len(md)} in Miami-Dade "
          f"(CRS {g.crs.to_string()})")
    # ALAND==0 units are pure-water polygons (Biscayne Bay, ocean); they are
    # real census units and stay in the denominator, but flag the count.
    water_only = int((md["ALAND"] == 0).sum())
    print(f"  of those, {water_only} have zero land area (water-only polygons)")
    return md


def join(points, polys, label, expected):
    j = gpd.sjoin(points, polys[["GEOID", "ALAND", "geometry"]],
                  how="left", predicate="within")
    # a point exactly on a shared edge can match two polygons; keep the first
    j = j[~j.index.duplicated(keep="first")]
    matched = j["GEOID"].notna()
    print(f"\n--- {label} ---")
    print(f"units in Miami-Dade (TIGER 2024)     : {len(polys)}  "
          f"(you expected ~{expected})")
    print(f"project points offered to the join   : {len(points)}")
    print(f"points that landed inside a unit     : {int(matched.sum())}")
    print(f"points that failed to join           : {int((~matched).sum())}")
    hit = j.loc[matched, "GEOID"]
    distinct = hit.nunique()
    print(f"DISTINCT units receiving >=1 project : {distinct}")
    print(f"units receiving ZERO projects        : {len(polys) - distinct}"
          f"  ({(len(polys) - distinct) / len(polys) * 100:.1f}% of units)")
    land = polys[polys["ALAND"] > 0]
    distinct_land = j.loc[matched].merge(
        land[["GEOID"]], on="GEOID", how="inner")["GEOID"].nunique()
    print(f"  land-bearing units only            : {len(land)} units, "
          f"{distinct_land} hit, {len(land) - distinct_land} zero "
          f"({(len(land) - distinct_land) / len(land) * 100:.1f}%)")
    if (~matched).sum():
        print("\nfailed-to-join records:")
        cols = ["Project_ID", "Project_Name", "Jurisdiction", "scale",
                "lat_num", "lon_num", "cost_num"]
        with pd.option_context("display.max_colwidth", 50):
            print(j.loc[~matched, cols].to_string(index=False))
        print(f"dollars that fail to join: "
              f"${j.loc[~matched, 'cost_num'].sum():,.0f}")
    counts = hit.value_counts()
    print(f"\nprojects per receiving unit: mean {counts.mean():.2f}, "
          f"median {counts.median():.0f}, max {counts.max()}")
    print("distribution of project counts across ALL units "
          "(the zero-inflation picture):")
    full = pd.Series(0, index=polys["GEOID"])
    full.update(counts)
    print(full.value_counts().sort_index().rename("n_units").to_frame()
          .rename_axis("projects_in_unit").head(15).to_string())
    print(f"\nshare of units with 0 projects: "
          f"{(full == 0).mean() * 100:.1f}%")
    print(f"share of units with 1 project : {(full == 1).mean() * 100:.1f}%")
    print(f"share of units with >=5       : {(full >= 5).mean() * 100:.1f}%")
    print("\nby scale tag - where each scale's pins land:")
    print(j.assign(joined=matched).groupby("scale")["joined"]
          .agg(n="size", joined="sum").to_string())
    return j


def zero_sensitivity(j, polys, label):
    """How the zero count moves if large-footprint scales are excluded.
    Evidence for decision (b) - no exclusion is applied anywhere else."""
    print(f"\n--- {label}: ZERO-COUNT SENSITIVITY TO SCALE EXCLUSION ---")
    n_units = len(polys)
    subsets = {
        "all records": None,
        "drop County": ["County"],
        "drop County+Municipality": ["County", "Municipality"],
        "drop County+Municipality+Neighborhood": ["County", "Municipality",
                                                  "Neighborhood"],
        "drop County+Muni+Neighborhood+Corridor (parcel only)":
            ["County", "Municipality", "Neighborhood", "Corridor"],
    }
    rows = []
    for name, drop in subsets.items():
        sub = j if drop is None else j[~j["scale"].isin(drop)]
        hit = sub.loc[sub["GEOID"].notna(), "GEOID"].nunique()
        rows.append({"subset": name, "n_records": len(sub),
                     "units_hit": hit, "units_zero": n_units - hit,
                     "pct_zero": f"{(n_units - hit) / n_units * 100:.1f}%"})
    print(pd.DataFrame(rows).to_string(index=False))


def main():
    df = load_typed()
    valid = df[df["coord_ok"]].copy()
    print(f"project records            : {len(df)}")
    print(f"with parseable coordinates : {len(valid)}")
    print(f"inside the Miami-Dade bbox : {int(df['in_bbox'].sum())}")
    print("(all parseable points are offered to the join; the bbox is a"
          " sanity screen, not a filter)\n")
    pts = gpd.GeoDataFrame(
        valid,
        geometry=gpd.points_from_xy(valid["lon_num"], valid["lat_num"]),
        crs="EPSG:4326",
    )

    tracts = load_boundaries("tl_2024_12_tract.zip", "tracts")
    bgs = load_boundaries("tl_2024_12_bg.zip", "block groups")
    pts_t = pts.to_crs(tracts.crs)

    jt = join(pts_t, tracts, "TRACTS", 698)
    zero_sensitivity(jt, tracts, "TRACTS")
    jb = join(pts_t.to_crs(bgs.crs), bgs, "BLOCK GROUPS", 1843)
    zero_sensitivity(jb, bgs, "BLOCK GROUPS")

    out = ensure_output_dir()
    # diagnostic join keys only - NOT an aggregated analysis table
    keys = pd.DataFrame({
        "Project_ID": df["Project_ID"],
    }).set_index(df.index)
    keys["tract_GEOID"] = jt["GEOID"]
    keys["bg_GEOID"] = jb["GEOID"]
    keys.to_csv(out / "project_join_keys.csv", index=False)
    print(f"\nwrote {out / 'project_join_keys.csv'} "
          "(per-project tract/BG id, diagnostic only - no aggregation)")


if __name__ == "__main__":
    main()
