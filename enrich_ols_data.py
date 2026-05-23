"""
Enrich the existing OLS tract dataset with FEMA National Risk Index (NRI)
census-tract features for Miami-Dade County.

Inputs (same folder as this script):
  - NRI_Table_CensusTracts_Florida.csv  (or national equivalent)
  - ols_tract_data.csv

Output (same folder):
  - ols_tract_data_enriched.csv
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent

# Candidate filenames, in order of preference: Florida-only, then national.
NRI_CANDIDATES = [
    "NRI_Table_CensusTracts_Florida.csv",
    "NRI_Table_CensusTracts.csv",
]
OLS_CSV = SCRIPT_DIR / "ols_tract_data.csv"
OUTPUT_CSV = SCRIPT_DIR / "ols_tract_data_enriched.csv"

MIAMI_DADE_STATEFIPS = 12
MIAMI_DADE_COUNTYFIPS = 86

NRI_COLUMNS = [
    "TRACTFIPS",
    # Exposure
    "POPULATION", "BUILDVALUE", "AGRIVALUE", "AREA",
    # Composite Risk and EAL
    "RISK_VALUE", "RISK_SCORE", "RISK_RATNG", "RISK_SPCTL",
    "EAL_SCORE", "EAL_RATNG", "EAL_SPCTL", "EAL_VALT",
    "EAL_VALB", "EAL_VALP", "EAL_VALPE", "EAL_VALA",
    "ALR_VALB", "ALR_VALP", "ALR_VALA", "ALR_NPCTL", "ALR_VRA_NPCTL",
    # Social Vulnerability
    # NOTE: RESL_SCORE / RESL_RATNG / RESL_SPCTL / RESL_VALUE / CRF_VALUE
    # are intentionally excluded — they are county-level values that are
    # constant across all Miami-Dade tracts (zero variance, unusable as
    # regressors). SOVI_* vary at tract level and are kept.
    "SOVI_SCORE", "SOVI_RATNG", "SOVI_SPCTL",
    # Hazard-specific risk and EAL scores
    "CFLD_RISKS", "CFLD_EALS",
    "IFLD_RISKS", "IFLD_EALS",
    "HRCN_RISKS", "HRCN_EALS",
    "HWAV_RISKS", "HWAV_EALS",
]

HAZARD_COLUMNS = [
    "CFLD_RISKS", "CFLD_EALS",
    "IFLD_RISKS", "IFLD_EALS",
    "HRCN_RISKS", "HRCN_EALS",
    "HWAV_RISKS", "HWAV_EALS",
]

SUMMARY_COLUMNS = [
    "RISK_SCORE", "SOVI_SCORE",
    "CFLD_RISKS", "IFLD_RISKS", "HRCN_RISKS",
]


def _print_header(title: str) -> None:
    bar = "=" * 72
    print(f"\n{bar}\n{title}\n{bar}")


def _normalize_tract_id(series: pd.Series) -> pd.Series:
    """Cast to string, strip trailing .0 from floats, zero-pad to 11 chars."""
    return (
        series.astype(str)
        .str.replace(r"\.0$", "", regex=True)
        .str.zfill(11)
    )


def _to_int_series(series: pd.Series) -> pd.Series:
    """Coerce a FIPS column that may be int or string into a nullable Int64."""
    cleaned = series.astype(str).str.replace(r"\.0$", "", regex=True)
    return pd.to_numeric(cleaned, errors="coerce").astype("Int64")


def _find_nri_csv() -> Path | None:
    for name in NRI_CANDIDATES:
        candidate = SCRIPT_DIR / name
        if candidate.is_file():
            return candidate
    return None


def main() -> int:
    # -----------------------------------------------------------------------
    # Step 1 — Load and filter NRI table
    # -----------------------------------------------------------------------
    _print_header("Step 1 — Load and filter NRI table")

    nri_path = _find_nri_csv()
    if nri_path is None:
        print(
            "ERROR: Could not find an NRI census-tracts CSV in "
            f"{SCRIPT_DIR}. Looked for: {', '.join(NRI_CANDIDATES)}",
            file=sys.stderr,
        )
        return 1

    print(f"NRI source: {nri_path.name}")
    nri = pd.read_csv(nri_path, low_memory=False)
    print(f"  Total NRI rows loaded: {len(nri):,}")

    for col in ("STATEFIPS", "COUNTYFIPS", "TRACTFIPS"):
        if col not in nri.columns:
            print(
                f"ERROR: Required column '{col}' not found in NRI CSV.",
                file=sys.stderr,
            )
            return 1

    state_int = _to_int_series(nri["STATEFIPS"])
    county_int = _to_int_series(nri["COUNTYFIPS"])
    mask = (state_int == MIAMI_DADE_STATEFIPS) & (county_int == MIAMI_DADE_COUNTYFIPS)
    nri_md = nri.loc[mask].copy()

    print(f"Miami-Dade tracts found in NRI table: {len(nri_md)}")

    nri_md["TRACTFIPS"] = _normalize_tract_id(nri_md["TRACTFIPS"])
    sample_tracts = nri_md["TRACTFIPS"].head(5).tolist()
    print(f"  Sample TRACTFIPS (normalized): {sample_tracts}")

    # -----------------------------------------------------------------------
    # Step 2 — Select target columns
    # -----------------------------------------------------------------------
    _print_header("Step 2 — Select target NRI columns")

    present = [c for c in NRI_COLUMNS if c in nri_md.columns]
    missing = [c for c in NRI_COLUMNS if c not in nri_md.columns]

    if missing:
        print(
            "WARNING: the following requested NRI columns are missing and "
            "will be skipped:"
        )
        for c in missing:
            print(f"  - {c}")
    else:
        print("All 32 requested NRI columns are present.")

    nri_selection = nri_md[present].copy()
    print(f"NRI selection shape: {nri_selection.shape}")

    # -----------------------------------------------------------------------
    # Step 3 — Join onto ols_tract_data.csv
    # -----------------------------------------------------------------------
    _print_header("Step 3 — Join onto ols_tract_data.csv")

    if not OLS_CSV.is_file():
        print(f"ERROR: ols_tract_data.csv not found at {OLS_CSV}", file=sys.stderr)
        return 1

    ols = pd.read_csv(OLS_CSV, low_memory=False)
    print(f"Loaded ols_tract_data.csv with {len(ols)} rows, {len(ols.columns)} columns")

    if "GEOID" not in ols.columns:
        print("ERROR: 'GEOID' column not found in ols_tract_data.csv", file=sys.stderr)
        return 1

    ols["GEOID"] = _normalize_tract_id(ols["GEOID"])

    enriched = ols.merge(
        nri_selection,
        how="left",
        left_on="GEOID",
        right_on="TRACTFIPS",
    )

    if "TRACTFIPS" in enriched.columns:
        enriched = enriched.drop(columns=["TRACTFIPS"])

    # Match diagnostics: a "match" means at least one NRI column came back non-null.
    nri_value_cols = [c for c in present if c != "TRACTFIPS"]
    if nri_value_cols:
        matched_mask = enriched[nri_value_cols].notna().any(axis=1)
    else:
        matched_mask = pd.Series(False, index=enriched.index)
    n_matched = int(matched_mask.sum())
    n_unmatched = len(enriched) - n_matched

    print(f"Tracts in ols_tract_data:          {len(ols)}")
    print(f"Tracts matched to NRI table:       {n_matched}")
    print(f"Tracts with no NRI match:          {n_unmatched}")

    # -----------------------------------------------------------------------
    # Step 4 — Diagnostics
    # -----------------------------------------------------------------------
    _print_header("Step 4 — Diagnostics")

    print(f"Final dataframe shape: {enriched.shape}")

    print("\nColumns in the enriched output:")
    for c in enriched.columns:
        print(f"  - {c}")

    print("\nNull counts for hazard-specific columns:")
    for c in HAZARD_COLUMNS:
        if c in enriched.columns:
            print(f"  {c}: {int(enriched[c].isna().sum())}")
        else:
            print(f"  {c}: (column not present)")

    print("\nSummary stats (min, max, mean):")
    for c in SUMMARY_COLUMNS:
        if c in enriched.columns:
            s = pd.to_numeric(enriched[c], errors="coerce")
            print(
                f"  {c:<12s} min={s.min()}, max={s.max()}, mean={s.mean()}"
            )
        else:
            print(f"  {c:<12s} (column not present)")

    # -----------------------------------------------------------------------
    # Step 5 — Save output
    # -----------------------------------------------------------------------
    _print_header("Step 5 — Save output")

    enriched.to_csv(OUTPUT_CSV, index=False)
    print(
        f"Saved ols_tract_data_enriched.csv — "
        f"{len(enriched)} rows, {len(enriched.columns)} columns"
    )
    print(f"Full path: {OUTPUT_CSV}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
