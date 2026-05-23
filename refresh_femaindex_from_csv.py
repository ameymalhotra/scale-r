#!/usr/bin/env python3
"""
Refresh FEMA National Risk Index fields in public/femaindex.geojson from
fema_miami_dade_dec_2025.csv (December 2025 NRI export).

Updates per tract (matched on 11-digit GEOID):
  - T_FEMA_National_Risk_Index_$_.FEMAIndexRating  <- RISK_RATNG
  - T_FEMA_National_Risk_Index_$_.FEMAIndex         <- RISK_SCORE
  - T_FEMA_National_Risk_Index_$_.Geo_ID            <- NRI_ID

Geometry and non-FEMA properties are preserved.

Usage:
  python3 refresh_femaindex_from_csv.py
  python3 refresh_femaindex_from_csv.py --dry-run
  npm run refresh-femaindex
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_GEOJSON = SCRIPT_DIR / "public" / "femaindex.geojson"
DEFAULT_CSV = SCRIPT_DIR / "fema_miami_dade_dec_2025.csv"

GEOJSON_GEOID_COL = "L0Census_Tracts.GEOID"
GEOJSON_RATING_COL = "T_FEMA_National_Risk_Index_$_.FEMAIndexRating"
GEOJSON_SCORE_COL = "T_FEMA_National_Risk_Index_$_.FEMAIndex"
GEOJSON_GEO_ID_COL = "T_FEMA_National_Risk_Index_$_.Geo_ID"

CSV_GEOID_COL = "TRACTFIPS"
CSV_RATING_COL = "RISK_RATNG"
CSV_SCORE_COL = "RISK_SCORE"
CSV_NRI_ID_COL = "NRI_ID"


def _normalize_geoid(value) -> str:
    s = str(value).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s.zfill(11)


def load_csv_lookup(path: Path) -> dict[str, dict]:
    df = pd.read_csv(
        path,
        usecols=[CSV_GEOID_COL, CSV_RATING_COL, CSV_SCORE_COL, CSV_NRI_ID_COL],
        dtype={CSV_GEOID_COL: str},
    )
    lookup: dict[str, dict] = {}
    for row in df.itertuples(index=False):
        geoid = _normalize_geoid(getattr(row, CSV_GEOID_COL))
        if geoid in lookup:
            continue
        lookup[geoid] = {
            "rating": str(getattr(row, CSV_RATING_COL)).strip(),
            "score": float(getattr(row, CSV_SCORE_COL)),
            "nri_id": str(getattr(row, CSV_NRI_ID_COL)).strip(),
        }
    return lookup


def refresh_geojson(geojson_path: Path, lookup: dict[str, dict], dry_run: bool) -> dict:
    with geojson_path.open(encoding="utf-8") as f:
        geojson = json.load(f)

    features = geojson.get("features") or []
    updated = 0
    missing_in_csv: list[str] = []
    missing_geoid = 0

    for feature in features:
        props = feature.setdefault("properties", {})
        raw_geoid = props.get(GEOJSON_GEOID_COL)
        if raw_geoid is None or (isinstance(raw_geoid, float) and pd.isna(raw_geoid)):
            missing_geoid += 1
            continue

        geoid = _normalize_geoid(raw_geoid)
        row = lookup.get(geoid)
        if row is None:
            missing_in_csv.append(geoid)
            continue

        props[GEOJSON_RATING_COL] = row["rating"]
        props[GEOJSON_SCORE_COL] = row["score"]
        props[GEOJSON_GEO_ID_COL] = row["nri_id"]
        updated += 1

    stats = {
        "features": len(features),
        "updated": updated,
        "missing_geoid": missing_geoid,
        "missing_in_csv": len(missing_in_csv),
        "csv_tracts": len(lookup),
    }

    if not dry_run:
        with geojson_path.open("w", encoding="utf-8") as f:
            json.dump(geojson, f, separators=(",", ":"))

    return stats


def run_reproject() -> None:
    subprocess.run(
        ["npm", "run", "reproject-femaindex"],
        cwd=SCRIPT_DIR,
        check=True,
    )


def run_compare() -> None:
    subprocess.run(
        ["python3", str(SCRIPT_DIR / "compare_fema_ratings.py")],
        cwd=SCRIPT_DIR,
        check=False,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Refresh FEMA NRI rating/score in femaindex.geojson from CSV."
    )
    parser.add_argument("--geojson", type=Path, default=DEFAULT_GEOJSON)
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report changes without writing files",
    )
    parser.add_argument(
        "--skip-reproject",
        action="store_true",
        help="Do not regenerate public/femaindex-4326.geojson",
    )
    parser.add_argument(
        "--skip-compare",
        action="store_true",
        help="Do not run compare_fema_ratings.py after refresh",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.csv.is_file():
        print(f"ERROR: CSV not found: {args.csv}", file=sys.stderr)
        return 1
    if not args.geojson.is_file():
        print(f"ERROR: GeoJSON not found: {args.geojson}", file=sys.stderr)
        return 1

    print(f"Loading CSV lookup: {args.csv}")
    lookup = load_csv_lookup(args.csv)
    print(f"  {len(lookup)} tracts in CSV")

    if args.dry_run:
        print("DRY RUN — no files will be written")

    print(f"Refreshing: {args.geojson}")
    stats = refresh_geojson(args.geojson, lookup, dry_run=args.dry_run)

    print("\nRefresh summary:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    if stats["missing_in_csv"]:
        print(
            f"WARNING: {stats['missing_in_csv']} GeoJSON tracts had no CSV match.",
            file=sys.stderr,
        )
        return 1

    if stats["updated"] != stats["features"]:
        print(
            f"WARNING: updated {stats['updated']} of {stats['features']} features.",
            file=sys.stderr,
        )

    if args.dry_run:
        return 0

    if not args.skip_reproject:
        print("\nReprojecting to femaindex-4326.geojson...")
        run_reproject()

    if not args.skip_compare:
        print("\nRunning tract rating comparison...")
        run_compare()

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
