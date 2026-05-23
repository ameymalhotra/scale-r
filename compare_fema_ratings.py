#!/usr/bin/env python3
"""
Compare FEMA National Risk Index ratings tract-by-tract between:
  - public/femaindex.geojson (map layer source)
  - fema_miami_dade_dec_2025.csv (December 2025 NRI export)

Join key: 11-digit census tract GEOID (TRACTFIPS in CSV, L0Census_Tracts.GEOID in GeoJSON).

Usage:
  python3 compare_fema_ratings.py
  python3 compare_fema_ratings.py --geojson path/to/femaindex.geojson --csv path/to.csv
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_GEOJSON = SCRIPT_DIR / "public" / "femaindex.geojson"
DEFAULT_CSV = SCRIPT_DIR / "fema_miami_dade_dec_2025.csv"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "data" / "output" / "fema_rating_comparison"

GEOJSON_GEOID_COL = "L0Census_Tracts.GEOID"
GEOJSON_RATING_COL = "T_FEMA_National_Risk_Index_$_.FEMAIndexRating"
GEOJSON_SCORE_COL = "T_FEMA_National_Risk_Index_$_.FEMAIndex"

CSV_GEOID_COL = "TRACTFIPS"
CSV_RATING_COL = "RISK_RATNG"
CSV_SCORE_COL = "RISK_SCORE"
CSV_NRI_ID_COL = "NRI_ID"


def _normalize_geoid(series: pd.Series) -> pd.Series:
    return series.astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(11)


def _normalize_rating(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip()


def load_geojson_ratings(path: Path) -> pd.DataFrame:
    with path.open(encoding="utf-8") as f:
        geojson = json.load(f)

    features = geojson.get("features") or []
    rows = []
    for feature in features:
        props = feature.get("properties") or {}
        geoid = props.get(GEOJSON_GEOID_COL)
        if geoid is None or (isinstance(geoid, float) and pd.isna(geoid)):
            continue
        rows.append(
            {
                "GEOID": geoid,
                "geojson_rating": props.get(GEOJSON_RATING_COL),
                "geojson_score": props.get(GEOJSON_SCORE_COL),
            }
        )

    if not rows:
        raise ValueError(f"No tract features with {GEOJSON_GEOID_COL} in {path}")

    df = pd.DataFrame(rows)
    df["GEOID"] = _normalize_geoid(df["GEOID"])
    df["geojson_rating"] = _normalize_rating(df["geojson_rating"])
    df["geojson_score"] = pd.to_numeric(df["geojson_score"], errors="coerce")

    dupes = df["GEOID"].duplicated().sum()
    if dupes:
        print(f"WARNING: {dupes} duplicate GEOIDs in GeoJSON; keeping first occurrence.", file=sys.stderr)
        df = df.drop_duplicates(subset="GEOID", keep="first")

    return df


def load_csv_ratings(path: Path) -> pd.DataFrame:
    usecols = [CSV_GEOID_COL, CSV_RATING_COL, CSV_SCORE_COL, CSV_NRI_ID_COL]
    df = pd.read_csv(path, usecols=usecols, dtype={CSV_GEOID_COL: str})
    df = df.rename(
        columns={
            CSV_GEOID_COL: "GEOID",
            CSV_RATING_COL: "csv_rating",
            CSV_SCORE_COL: "csv_score",
            CSV_NRI_ID_COL: "nri_id",
        }
    )
    df["GEOID"] = _normalize_geoid(df["GEOID"])
    df["csv_rating"] = _normalize_rating(df["csv_rating"])
    df["csv_score"] = pd.to_numeric(df["csv_score"], errors="coerce")

    dupes = df["GEOID"].duplicated().sum()
    if dupes:
        print(f"WARNING: {dupes} duplicate GEOIDs in CSV; keeping first occurrence.", file=sys.stderr)
        df = df.drop_duplicates(subset="GEOID", keep="first")

    return df


def compare_tract_ratings(geo_df: pd.DataFrame, csv_df: pd.DataFrame) -> pd.DataFrame:
    merged = geo_df.merge(csv_df, on="GEOID", how="outer", indicator=True)

    merged["in_geojson"] = merged["_merge"].isin(["left_only", "both"])
    merged["in_csv"] = merged["_merge"].isin(["right_only", "both"])

    both = merged["_merge"] == "both"
    merged["ratings_match"] = False
    merged.loc[both, "ratings_match"] = (
        merged.loc[both, "geojson_rating"] == merged.loc[both, "csv_rating"]
    )

    merged["match_status"] = "unmatched"
    merged.loc[merged["_merge"] == "left_only", "match_status"] = "geojson_only"
    merged.loc[merged["_merge"] == "right_only", "match_status"] = "csv_only"
    merged.loc[both & merged["ratings_match"], "match_status"] = "match"
    merged.loc[both & ~merged["ratings_match"], "match_status"] = "mismatch"

    score_both = both & merged["geojson_score"].notna() & merged["csv_score"].notna()
    merged["score_delta"] = pd.NA
    merged.loc[score_both, "score_delta"] = (
        merged.loc[score_both, "csv_score"] - merged.loc[score_both, "geojson_score"]
    )

    return merged.drop(columns=["_merge"]).sort_values("GEOID")


def print_summary(comparison: pd.DataFrame) -> None:
    bar = "=" * 72
    print(f"\n{bar}\nFEMA risk rating comparison (tract-level)\n{bar}")

    n_geo = int(comparison["in_geojson"].sum())
    n_csv = int(comparison["in_csv"].sum())
    n_both = int((comparison["in_geojson"] & comparison["in_csv"]).sum())
    n_match = int((comparison["match_status"] == "match").sum())
    n_mismatch = int((comparison["match_status"] == "mismatch").sum())
    n_geo_only = int((comparison["match_status"] == "geojson_only").sum())
    n_csv_only = int((comparison["match_status"] == "csv_only").sum())

    print(f"Tracts in GeoJSON:     {n_geo}")
    print(f"Tracts in CSV:         {n_csv}")
    print(f"Tracts in both:        {n_both}")
    print(f"Ratings match:         {n_match}")
    print(f"Ratings mismatch:      {n_mismatch}")
    print(f"GeoJSON only:          {n_geo_only}")
    print(f"CSV only:              {n_csv_only}")

    if n_both:
        pct = 100.0 * n_match / n_both
        print(f"Agreement (both sides): {pct:.1f}%")

    print("\nGeoJSON rating distribution:")
    print(comparison["geojson_rating"].value_counts(dropna=False).to_string())

    print("\nCSV rating distribution:")
    print(comparison["csv_rating"].value_counts(dropna=False).to_string())

    mismatches = comparison[comparison["match_status"] == "mismatch"]
    if len(mismatches):
        print("\nMismatch transitions (geojson_rating -> csv_rating):")
        ctab = pd.crosstab(
            mismatches["geojson_rating"],
            mismatches["csv_rating"],
            dropna=False,
        )
        print(ctab.to_string())

    score_pairs = comparison.dropna(subset=["geojson_score", "csv_score"])
    if len(score_pairs):
        corr = score_pairs["geojson_score"].corr(score_pairs["csv_score"])
        print(f"\nScore correlation (geojson vs csv): {corr:.4f}")
        print(
            f"Mean score delta (csv - geojson): "
            f"{score_pairs['score_delta'].mean():.4f}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare FEMA NRI tract ratings between femaindex.geojson and CSV."
    )
    parser.add_argument(
        "--geojson",
        type=Path,
        default=DEFAULT_GEOJSON,
        help=f"Path to femaindex GeoJSON (default: {DEFAULT_GEOJSON.name})",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_CSV,
        help=f"Path to FEMA CSV export (default: {DEFAULT_CSV.name})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for comparison CSV outputs",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.geojson.is_file():
        print(f"ERROR: GeoJSON not found: {args.geojson}", file=sys.stderr)
        return 1
    if not args.csv.is_file():
        print(f"ERROR: CSV not found: {args.csv}", file=sys.stderr)
        return 1

    print(f"Loading GeoJSON: {args.geojson}")
    geo_df = load_geojson_ratings(args.geojson)

    print(f"Loading CSV: {args.csv}")
    csv_df = load_csv_ratings(args.csv)

    comparison = compare_tract_ratings(geo_df, csv_df)
    print_summary(comparison)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    all_path = args.output_dir / "fema_rating_comparison.csv"
    mismatch_path = args.output_dir / "fema_rating_mismatches.csv"

    out_cols = [
        "GEOID",
        "nri_id",
        "geojson_rating",
        "csv_rating",
        "ratings_match",
        "match_status",
        "geojson_score",
        "csv_score",
        "score_delta",
        "in_geojson",
        "in_csv",
    ]
    comparison[out_cols].to_csv(all_path, index=False)
    comparison[comparison["match_status"] == "mismatch"][out_cols].to_csv(
        mismatch_path, index=False
    )

    print(f"\nWrote full comparison: {all_path}")
    print(f"Wrote mismatches only: {mismatch_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
