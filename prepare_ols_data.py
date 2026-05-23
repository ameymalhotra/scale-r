"""
Prepare tract-level data for OLS regression: join FEMA National Risk Index
tract features with aggregated Miami-Dade project metrics.
"""

from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths (repo layout: FEMA GeoJSON in public/; merged Excel from tract pipeline)
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
GEOJSON_PATH = SCRIPT_DIR / "public" / "femaindex.geojson"
EXCEL_PATH = (
    SCRIPT_DIR
    / "data"
    / "output"
    / "merged"
    / "MergedDataset_Original_plus_LMS_conf1_with_tract_geoid.xlsx"
)
OUTPUT_CSV = SCRIPT_DIR / "ols_tract_data.csv"

GEOID_COL = "L0Census_Tracts.GEOID"
FEMA_INDEX_COL = "T_FEMA_National_Risk_Index_$_.FEMAIndex"
FEMA_RATING_COL = "T_FEMA_National_Risk_Index_$_.FEMAIndexRating"


def _print_header(title: str) -> None:
    bar = "=" * 72
    print(f"\n{bar}\n{title}\n{bar}")


def _normalize_geoid(series: pd.Series) -> pd.Series:
    return series.astype(str).str.replace(r"\.0$", "", regex=True).str.zfill(11)


def _status_column(df: pd.DataFrame) -> str:
    if "Project_Status" in df.columns:
        return "Project_Status"
    if "Project__1" in df.columns:
        return "Project__1"
    raise KeyError(
        "Expected project status column 'Project_Status' or 'Project__1' in Excel."
    )


def main() -> int:
    # -----------------------------------------------------------------------
    # Step 1 — Load both files
    # -----------------------------------------------------------------------
    _print_header("Step 1 — Load both files")

    if not GEOJSON_PATH.is_file():
        print(f"ERROR: GeoJSON not found: {GEOJSON_PATH}", file=sys.stderr)
        return 1
    if not EXCEL_PATH.is_file():
        print(f"ERROR: Excel not found: {EXCEL_PATH}", file=sys.stderr)
        return 1

    tracts_gdf = gpd.read_file(GEOJSON_PATH)
    projects = pd.read_excel(EXCEL_PATH, sheet_name="Projects", engine="openpyxl")

    print(f"GeoJSON path: {GEOJSON_PATH}")
    print(f"  Feature rows: {len(tracts_gdf)}")
    if GEOID_COL in tracts_gdf.columns:
        sample_geo = (
            _normalize_geoid(tracts_gdf[GEOID_COL].dropna().head(5)).tolist()
        )
        print(f"  Sample GEOIDs (normalized): {sample_geo}")
    else:
        print(
            f"  WARNING: Column '{GEOID_COL}' not found. "
            f"Available columns sample: {list(tracts_gdf.columns)[:15]} ..."
        )

    print(f"\nExcel path: {EXCEL_PATH}")
    print(f"  Projects sheet rows: {len(projects)}")
    if "TRACT_GEOID" in projects.columns:
        sample_proj = (
            _normalize_geoid(projects["TRACT_GEOID"].dropna().head(5)).tolist()
        )
        print(f"  Sample TRACT_GEOID (normalized): {sample_proj}")
    else:
        print("  ERROR: Column 'TRACT_GEOID' not found in Projects sheet.")
        return 1

    # -----------------------------------------------------------------------
    # Step 2 — Aggregate projects to tract level
    # -----------------------------------------------------------------------
    _print_header("Step 2 — Aggregate projects to tract level")

    status_col = _status_column(projects)
    p = projects.copy()
    p["tract_geoid"] = _normalize_geoid(p["TRACT_GEOID"])
    p["cost"] = pd.to_numeric(p["Estimated_"], errors="coerce").fillna(0.0)
    p["infrastruc"] = p["Infrastruc"].fillna("").astype(str)
    p["disaster_f"] = p["Disaster_F"].fillna("").astype(str)
    p["status"] = p[status_col].fillna("").astype(str)

    def contains_ci(s: pd.Series, needle: str) -> pd.Series:
        return s.str.contains(needle, case=False, regex=False, na=False)

    p["is_grey"] = contains_ci(p["infrastruc"], "Grey")
    p["is_green"] = contains_ci(p["infrastruc"], "Green")
    p["is_blue"] = contains_ci(p["infrastruc"], "Blue")
    p["is_hybrid"] = contains_ci(p["infrastruc"], "Hybrid")
    p["is_complete"] = contains_ci(p["status"], "Complet")
    p["is_multi_hazard"] = contains_ci(p["disaster_f"], "Multi")
    p["is_flood"] = contains_ci(p["disaster_f"], "Flood")
    p["is_surge"] = contains_ci(p["disaster_f"], "Surge")

    def dominant_hazard_series(s: pd.Series) -> str:
        vals = s.replace("", np.nan).dropna()
        if vals.empty:
            return "None"
        vc = vals.astype(str).value_counts()
        return str(vc.index[0])

    grouped = p.groupby("tract_geoid", dropna=False)

    agg = grouped.agg(
        project_count=("tract_geoid", "count"),
        total_investment=("cost", "sum"),
        _grey=("is_grey", "sum"),
        _green=("is_green", "sum"),
        _blue=("is_blue", "sum"),
        _hybrid=("is_hybrid", "sum"),
        _complete=("is_complete", "sum"),
        multi_hazard_count=("is_multi_hazard", "sum"),
        flood_count=("is_flood", "sum"),
        surge_count=("is_surge", "sum"),
    ).reset_index()

    dom = (
        grouped["disaster_f"]
        .agg(dominant_hazard_series)
        .rename("dominant_hazard")
        .reset_index()
    )
    agg = agg.merge(dom, on="tract_geoid", how="left")

    n = agg["project_count"].replace(0, np.nan)
    agg["pct_grey"] = (agg["_grey"] / n * 100).fillna(0.0)
    agg["pct_green"] = (agg["_green"] / n * 100).fillna(0.0)
    agg["pct_blue"] = (agg["_blue"] / n * 100).fillna(0.0)
    agg["pct_hybrid"] = (agg["_hybrid"] / n * 100).fillna(0.0)
    agg["pct_complete"] = (agg["_complete"] / n * 100).fillna(0.0)
    agg = agg.drop(columns=["_grey", "_green", "_blue", "_hybrid", "_complete"])

    agg = agg.rename(columns={"tract_geoid": "GEOID"})
    print(f"Aggregated tracts with ≥1 project row: {len(agg)}")

    # -----------------------------------------------------------------------
    # Step 3 — Build the full tract table
    # -----------------------------------------------------------------------
    _print_header("Step 3 — Build the full tract table")

    if GEOID_COL not in tracts_gdf.columns:
        print(
            f"ERROR: GeoJSON missing expected GEOID column '{GEOID_COL}'.",
            file=sys.stderr,
        )
        return 1
    if FEMA_INDEX_COL not in tracts_gdf.columns or FEMA_RATING_COL not in tracts_gdf.columns:
        print(
            f"ERROR: GeoJSON missing FEMA columns. "
            f"Have FEMA index: {FEMA_INDEX_COL in tracts_gdf.columns}, "
            f"rating: {FEMA_RATING_COL in tracts_gdf.columns}",
            file=sys.stderr,
        )
        return 1

    base = pd.DataFrame(
        {
            "GEOID": _normalize_geoid(tracts_gdf[GEOID_COL]),
            "fema_index": pd.to_numeric(tracts_gdf[FEMA_INDEX_COL], errors="coerce"),
            "fema_rating": tracts_gdf[FEMA_RATING_COL].astype(str).replace(
                "nan", np.nan
            ),
        }
    )

    out = base.merge(agg, on="GEOID", how="left")

    fill_zero = [
        "project_count",
        "total_investment",
        "pct_grey",
        "pct_green",
        "pct_blue",
        "pct_hybrid",
        "pct_complete",
        "multi_hazard_count",
        "flood_count",
        "surge_count",
    ]
    for c in fill_zero:
        out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0.0)

    out["dominant_hazard"] = out["dominant_hazard"].fillna("None")
    mask_no_projects = out["project_count"] == 0
    out.loc[mask_no_projects, "dominant_hazard"] = "None"

    final_cols = [
        "GEOID",
        "fema_index",
        "fema_rating",
        "project_count",
        "total_investment",
        "pct_grey",
        "pct_green",
        "pct_blue",
        "pct_hybrid",
        "pct_complete",
        "dominant_hazard",
        "multi_hazard_count",
        "flood_count",
        "surge_count",
    ]
    out = out[final_cols]

    # -----------------------------------------------------------------------
    # Step 4 — Diagnostics
    # -----------------------------------------------------------------------
    _print_header("Step 4 — Diagnostics")

    total_tracts = len(out)
    tracts_with_projects = int((out["project_count"] > 0).sum())
    tracts_without_projects = int((out["project_count"] == 0).sum())

    print(f"Total tracts: {total_tracts} (expected 706)")
    print(f"Tracts with projects: {tracts_with_projects} (expected 265)")
    print(f"Tracts without projects: {tracts_without_projects} (expected 441)")

    print("\nDistribution of fema_rating (value_counts):")
    print(out["fema_rating"].value_counts(dropna=False).to_string())

    print("\nSummary stats for fema_index (min, max, mean, std):")
    fi = pd.to_numeric(out["fema_index"], errors="coerce")
    print(
        f"  min={fi.min()}, max={fi.max()}, mean={fi.mean()}, std={fi.std()}"
    )

    print("\nSummary stats for project_count:")
    pc = out["project_count"]
    print(f"  min={pc.min()}, max={pc.max()}, mean={pc.mean()}, std={pc.std()}")

    print("\nSummary stats for total_investment:")
    ti = out["total_investment"]
    print(f"  min={ti.min()}, max={ti.max()}, mean={ti.mean()}, std={ti.std()}")

    x_numeric = [
        "project_count",
        "total_investment",
        "pct_grey",
        "pct_green",
        "pct_blue",
        "pct_hybrid",
        "pct_complete",
        "multi_hazard_count",
        "flood_count",
        "surge_count",
    ]
    print("\nCorrelation of each numeric X with fema_index (pairwise):")
    y = pd.to_numeric(out["fema_index"], errors="coerce")
    for col in x_numeric:
        r = out[col].corr(y)
        print(f"  {col}: {r}")

    null_fema = int(out["fema_index"].isna().sum())
    print(
        f"\nRows where fema_index is null (flag for OLS; not dropped here): {null_fema}"
    )

    # -----------------------------------------------------------------------
    # Step 5 — Save output
    # -----------------------------------------------------------------------
    _print_header("Step 5 — Save output")

    out.to_csv(OUTPUT_CSV, index=False)
    print(f'Saved ols_tract_data.csv — {len(out)} rows')
    print(f"Full path: {OUTPUT_CSV}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
