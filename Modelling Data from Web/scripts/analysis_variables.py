"""Central variable-list definitions shared by Parts 2-5, so every script
uses the exact same column sets. No modeling; this module only names columns.
"""
from pathlib import Path

import pandas as pd

from scaler_projects import BASE
from vulnerability_loaders import (
    ADI_VARS, CRE_VARS, EJ_ENV, EJ_HEALTH, EJ_SOCIO, NEW_BG_VARS,
)

# ---- SVI EP_* (24), fixed order matching the SVI file --------------------
SVI_VARS = ["EP_POV150", "EP_UNEMP", "EP_HBURD", "EP_NOHSDP", "EP_UNINSUR",
            "EP_AGE65", "EP_AGE17", "EP_DISABL", "EP_SNGPNT", "EP_LIMENG",
            "EP_MINRTY", "EP_MUNIT", "EP_MOBILE", "EP_CROWD", "EP_NOVEH",
            "EP_GROUPQ", "EP_NOINT", "EP_AFAM", "EP_HISP", "EP_ASIAN",
            "EP_AIAN", "EP_NHPI", "EP_TWOMORE", "EP_OTHERRACE"]

TRACT_VULN_VARS = SVI_VARS + CRE_VARS                       # 24 + 10 = 34
# 13+7+2+13+2 = 37 (Part 6 follow-up added no_vehicle, no_broadband, which
# were previously dropped from the ADI pull on the mistaken assumption that
# EJScreen carried them - see RESULTS_FOR_REVIEW.md Sec 4e).
BG_VULN_VARS = EJ_ENV + EJ_SOCIO + EJ_HEALTH + ADI_VARS + NEW_BG_VARS

# ---- PCA inputs, after the pre-PCA correlation screen ---------------------
# Decisions recorded in DATA_PROCESSING.md Sec 7 ("Variable reduction before
# PCA"). TRACT_VULN_VARS / BG_VULN_VARS above are kept unchanged so the
# Part 2-6 scripts still reproduce; the PCA reads only these lists. Neither
# list contains the seven out-of-scope SVI race adjuncts (EP_AFAM, EP_HISP,
# EP_ASIAN, EP_AIAN, EP_NHPI, EP_TWOMORE, EP_OTHERRACE), which remain in
# SVI_VARS and in tract_analysis.csv for traceability only.
PCA_TRACT_VARS = [                                            # 17 SVI + 2 ACS = 19
    "EP_POV150", "EP_UNEMP", "EP_HBURD", "EP_NOHSDP", "EP_UNINSUR",
    "EP_AGE65", "EP_AGE17", "EP_DISABL", "EP_SNGPNT", "EP_LIMENG",
    "EP_MINRTY", "EP_MUNIT", "EP_MOBILE", "EP_CROWD", "EP_NOVEH",
    "EP_GROUPQ", "EP_NOINT",
    "no_fulltime_worker_hh", "crowding_over100",
]
# dropped as ACS twins of a kept SVI indicator (|Spearman rho| >= 0.75)
PCA_TRACT_DROPPED = ["no_diploma_pop25", "age65plus", "no_broadband", "uninsured",
                     "no_vehicle", "poverty_under125", "limited_english_hh",
                     "disability"]
# 24 social indicators; the 13 EJ_ENV measures are excluded (provisional)
PCA_BG_VARS = EJ_SOCIO + EJ_HEALTH + ADI_VARS + NEW_BG_VARS    # 7+2+13+2 = 24
# block-group variables more than 20% missing; the reduced PCA omits them
PCA_BG_HIGH_MISSING = ["income_disparity", "median_gross_rent",
                       "median_monthly_mortgage"]
PCA_BG_VARS_REDUCED = [v for v in PCA_BG_VARS if v not in PCA_BG_HIGH_MISSING]  # 21

_RACE_ADJUNCTS = {"EP_AFAM", "EP_HISP", "EP_ASIAN", "EP_AIAN", "EP_NHPI",
                  "EP_TWOMORE", "EP_OTHERRACE"}
assert len(PCA_TRACT_VARS) == 19 and not _RACE_ADJUNCTS & set(PCA_TRACT_VARS)
assert len(PCA_BG_VARS) == 24 and not set(EJ_ENV) & set(PCA_BG_VARS)
assert not _RACE_ADJUNCTS & set(PCA_BG_VARS)

# ---- overlap pairs named in the prompt (Part 3) ---------------------------
# SVI EP_* <-> CRE ACS construct-level overlaps (tract)
TRACT_OVERLAP_PAIRS = [
    ("EP_POV150", "poverty_under125", "poverty (150% vs 125% threshold)"),
    ("EP_UNINSUR", "uninsured", "uninsured"),
    ("EP_DISABL", "disability", "disability"),
    ("EP_NOVEH", "no_vehicle", "no vehicle"),
    ("EP_AGE65", "age65plus", "age 65+"),
    ("EP_LIMENG", "limited_english_hh", "limited English HH"),
    ("EP_NOHSDP", "no_diploma_pop25", "no HS diploma (EP_NOHSDP is bachelor's-adjacent cut; check)"),
    ("EP_NOINT", "no_broadband", "no internet/broadband"),
    ("EP_CROWD", "crowding_over100", "crowding"),
]
# EJScreen socioeconomic <-> ADI - the 4 flagged as likely TRUE duplicates
BG_DUPLICATE_CANDIDATES = [
    ("no vehicle", None, None),   # EJScreen has no raw "no vehicle" column - see report
    ("no internet", None, None),  # EJScreen has no raw "no internet" column - see report
    ("UNEMPPCT", None, "unemployment - EJScreen has it; ADI dropped it as a duplicate (not pulled)"),
    ("LESSHSPCT", "no_diploma_under9yrs", "less-than-HS vs <9yrs (different thresholds, not identical)"),
]

# ---- outcome / composition columns ----------------------------------------
TYPE_COLS_TRACT = ["investment_type_blue", "investment_type_gray",
                   "investment_type_green", "investment_type_hybrid"]
SCALE_COLS_TRACT = ["investment_scale_parcel", "investment_scale_neighborhood",
                    "investment_scale_corridor", "investment_scale_municipality",
                    "investment_scale_county"]
TYPES = ["blue", "gray", "green", "hybrid"]
PATHS = ["single_unit", "municipality", "county"]  # parcel/neighborhood/corridor collapse to single_unit

VOLUME_OUTCOMES_TRACT = ["investment_per_capita", "investment_total",
                         "investment_per_area", "investment_any_excl_county",
                         "investment_any_single_unit"]
VOLUME_OUTCOMES_BG = ["investment_any_excl_county", "investment_any_single_unit"]

BINARY_OUTCOMES = ["investment_any_excl_county", "investment_any_single_unit"]


def load_tract():
    df = pd.read_csv(BASE / "tract_analysis.csv", dtype={"GEOID": str})
    assert len(df) == 698
    return df


def load_bg():
    df = pd.read_csv(BASE / "blockgroup_analysis.csv", dtype={"GEOID": str})
    assert len(df) == 1843
    return df


def add_type_scale_measures(df, per_capita=True):
    """{type}_per_capita, {type}_share, {type}_any and the allocation-path
    equivalents. per_capita=False skips the dollar-per-resident measure
    (block-group spec, per the Part 4d restriction)."""
    df = df.copy()
    total = df["investment_total"]
    for t, col in zip(TYPES, TYPE_COLS_TRACT):
        if per_capita:
            df[f"type_{t}_per_capita"] = df[col] / df["population"].where(df["population"] > 0)
        df[f"type_{t}_share"] = (df[col] / total.where(total > 0))
        df[f"type_{t}_any"] = (df[col] > 0).astype(int)
    # path shares: single-unit = parcel+neighborhood+corridor; municipality; county
    single = df["investment_scale_parcel"] + df["investment_scale_neighborhood"] + df["investment_scale_corridor"]
    df["path_single_unit_amt"] = single
    df["path_municipality_amt"] = df["investment_scale_municipality"]
    df["path_county_amt"] = df["investment_scale_county"]
    for p in PATHS:
        amt = df[f"path_{p}_amt"]
        if per_capita:
            df[f"path_{p}_per_capita"] = amt / df["population"].where(df["population"] > 0)
        df[f"path_{p}_share"] = amt / total.where(total > 0)
        df[f"path_{p}_any"] = (amt > 0).astype(int)
    return df
