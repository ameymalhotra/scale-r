"""Shared loader for the SCALE-R project/investment database.

Profiling only: this module parses types and flags problems. It never drops,
imputes, or edits a record. Every derived column is additive.
"""
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent.parent
PROJECT_CSV = BASE / "SCALE-R_Database.csv"
BOUNDARY_DIR = BASE / "boundaries"
OUTPUT_DIR = BASE / "output"

# Rough Miami-Dade bounding box supplied with the profiling request.
MD_LAT_MIN, MD_LAT_MAX = 25.1, 25.98
MD_LON_MIN, MD_LON_MAX = -80.87, -80.12

COST_COL = "Estimated_Cost"
SCALE_COL = "Spatial_Resolution"
LAT_COL, LON_COL = "Latitude", "Longitude"
YEAR_COL = "Reported_Year"


def load_raw(path: Path = PROJECT_CSV) -> pd.DataFrame:
    """Load every column as string, so nothing is silently coerced on read."""
    return pd.read_csv(path, dtype=str, encoding="utf-8-sig")


def load_typed(path: Path = PROJECT_CSV) -> pd.DataFrame:
    """Raw frame plus parsed numeric columns and in-bounds flags (additive)."""
    df = load_raw(path)
    df["cost_num"] = pd.to_numeric(df[COST_COL], errors="coerce")
    df["lat_num"] = pd.to_numeric(df[LAT_COL], errors="coerce")
    df["lon_num"] = pd.to_numeric(df[LON_COL], errors="coerce")
    df["year_num"] = pd.to_numeric(df[YEAR_COL], errors="coerce")
    df["scale"] = df[SCALE_COL].str.strip()
    df["coord_ok"] = df["lat_num"].notna() & df["lon_num"].notna()
    df["in_bbox"] = (
        df["lat_num"].between(MD_LAT_MIN, MD_LAT_MAX)
        & df["lon_num"].between(MD_LON_MIN, MD_LON_MAX)
    )
    return df


def ensure_output_dir() -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    return OUTPUT_DIR
