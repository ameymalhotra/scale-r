"""
Build a Miami-Dade Heat & Health Index (HHI) layer for /admin/layers.

Input: a CDC Tracking Network export of "Heat & Health Index | Overall Heat &
Health Index Rank" by ZIP Code Tabulation Area (ZCTA), e.g. heat index/data_223624.csv.
The value is a percentile rank from 0 to 1; higher means more vulnerable to
heat-related illness.

Steps:
  1. Read the CSV. CDC prefixes each ZCTA with the state FIPS (1233125 -> 33125).
  2. Load 2020 ZCTA boundaries (Census cartographic boundary file) and keep the
     ones that overlap Miami-Dade land, clipped to the county's land area (the
     county's 2024 block groups minus TIGER water areas).
  3. Name each ZCTA after the 2024 Census place (city or census-designated
     place) its interior point falls in.
  4. Write a simplified EPSG:4326 GeoJSON.

Usage:
  scripts/python/.venv-lst/bin/python scripts/python/build_hhi_layer.py
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path

import shapefile
import shapely
from shapely.geometry import mapping, shape

from build_lst_layer import BOUNDARIES, REPO_ROOT, load_block_groups, round_coords, to_utm, to_wgs84

ZCTA_ZIP = BOUNDARIES / "cb_2020_us_zcta520_500k.zip"
PLACE_ZIP = BOUNDARIES / "tl_2024_12_place.zip"
LEVELS = [
    (0.25, "Low (0-25th percentile)"),
    (0.50, "Moderate (25-50th percentile)"),
    (0.75, "High (50-75th percentile)"),
    (1.01, "Very high (75-100th percentile)"),
]


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--csv", type=Path, default=REPO_ROOT / "heat index" / "data_223624.csv")
    p.add_argument("--min-share", type=float, default=10.0, help="Keep ZCTAs with at least this %% of their land in the county")
    p.add_argument("--simplify-m", type=float, default=10.0, help="Geometry simplification tolerance in metres")
    p.add_argument("--out", type=Path, default=REPO_ROOT / "output" / "hhi" / "hhi_zcta_miami_dade.geojson")
    return p.parse_args()


def read_hhi(path: Path) -> tuple[dict[str, float], str]:
    values, years = {}, set()
    with open(path, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            raw = (row.get("Value") or "").strip()
            if not raw:
                continue
            values[row["ZCTA"].strip()[-5:]] = float(raw)
            years.add(row["Year"].strip())
    return values, "/".join(sorted(years))


def load_places() -> list[tuple[str, object]]:
    reader = shapefile.Reader(str(PLACE_ZIP))
    return [
        (sr.record["NAME"], shapely.make_valid(to_utm(shape(sr.shape.__geo_interface__))))
        for sr in reader.iterShapeRecords()
    ]


def level(rank: float) -> str:
    return next(label for cutoff, label in LEVELS if rank < cutoff)


def main() -> None:
    args = parse_args()
    hhi, year = read_hhi(args.csv)
    print(f"HHI values: {len(hhi)} ZCTAs ({year})")

    county = shapely.union_all([g["geom"] for g in load_block_groups(clip_water=True)])
    shapely.prepare(county)
    places = load_places()
    place_tree = shapely.STRtree([g for _, g in places])

    reader = shapefile.Reader(str(ZCTA_ZIP))
    features, dropped, missing = [], [], []
    for sr in reader.iterShapeRecords():
        zcta = sr.record["ZCTA5CE20"]
        if not zcta.startswith("3"):
            continue
        geom = shapely.make_valid(to_utm(shape(sr.shape.__geo_interface__)))
        if not county.intersects(geom):
            continue
        inside = shapely.make_valid(geom.intersection(county))
        share = inside.area / geom.area * 100 if geom.area else 0
        if share < args.min_share:
            dropped.append((zcta, round(share, 1)))
            continue
        rank = hhi.get(zcta)
        if rank is None:
            missing.append(zcta)

        point = inside.representative_point()
        hits = place_tree.query(point, predicate="within")
        place = places[hits[0]][0] if len(hits) else "Unincorporated Miami-Dade"

        out = to_wgs84(inside.simplify(args.simplify_m, preserve_topology=True))
        polys = [p for p in getattr(out, "geoms", [out]) if p.geom_type in ("Polygon", "MultiPolygon")]
        if not polys:
            continue
        out = shapely.make_valid(shapely.union_all(polys))
        gj = mapping(out)
        features.append(
            {
                "type": "Feature",
                "properties": {
                    "ZCTA": zcta,
                    "NAME": f"ZIP {zcta} ({place})",
                    "hhi_rank": round(rank, 4) if rank is not None else None,
                    "hhi_percentile": round(rank * 100, 1) if rank is not None else None,
                    "hhi_level": level(rank) if rank is not None else None,
                    "pct_in_county": round(min(share, 100.0), 1),
                    "year": year,
                    "source": "CDC Heat & Health Index, overall rank",
                },
                "geometry": {"type": gj["type"], "coordinates": round_coords(gj["coordinates"])},
            }
        )

    features.sort(key=lambda f: f["properties"]["ZCTA"])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        json.dump({"type": "FeatureCollection", "features": features}, f, separators=(",", ":"))

    ranks = sorted(f["properties"]["hhi_rank"] for f in features if f["properties"]["hhi_rank"] is not None)
    print(f"Wrote {args.out.relative_to(REPO_ROOT)} ({os.path.getsize(args.out) / 1e6:.1f} MB, {len(features)} ZCTAs)")
    print(f"Rank: min {ranks[0]}  median {ranks[len(ranks) // 2]}  max {ranks[-1]}")
    print(f"No HHI value (drawn grey): {missing}")
    print(f"Dropped, under {args.min_share}% in county: {dropped}")


if __name__ == "__main__":
    main()
