"""Audit of the FEMA National Risk Index extract at ../fema_miami_dade_dec_2025.csv.

Read-only inventory. This script does not join the file to anything, does not
build variables, does not correlate and does not model. It reads the file,
counts what is in it and prints the result. The NRI file itself is never
modified.

Usage: python scripts/audit_nri.py > output/nri_audit_raw.txt
"""
import pathlib
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent
NRI_PATH = BASE.parent / "fema_miami_dade_dec_2025.csv"
MD_PREFIX = "12086"

# the ten hazard prefixes the professor's list maps onto, plus the labels NRI
# uses for them
REQUESTED_HAZARDS = {
    "HWAV": "heat wave", "CFLD": "coastal flooding",
    "RFLD": "riverine flooding (pre-v1.20 name)", "HRCN": "hurricane",
    "SWND": "strong wind", "TRND": "tornado", "WFIR": "wildfire",
    "LTNG": "lightning", "DRGT": "drought", "HAIL": "hail",
}
# every NRI hazard code, so anything outside the requested ten is still named
ALL_NRI_HAZARDS = {
    "AVLN": "avalanche", "CFLD": "coastal flooding", "CWAV": "cold wave",
    "DRGT": "drought", "ERQK": "earthquake", "HAIL": "hail",
    "HWAV": "heat wave", "HRCN": "hurricane", "IFLD": "inland flooding",
    "ISTM": "ice storm", "LNDS": "landslide", "LTNG": "lightning",
    "RFLD": "riverine flooding", "SWND": "strong wind", "TRND": "tornado",
    "TSUN": "tsunami", "VLCN": "volcanic activity", "WFIR": "wildfire",
    "WNTW": "winter weather",
}
NON_HAZARD_PREFIXES = {"RISK", "SOVI", "RESL", "EAL", "ALR", "CRF"}

COMPONENT_TYPES = [
    ("_EALT", "expected annual loss, total"),
    ("_EALB", "expected annual loss, building (the property damage measure)"),
    ("_EALP", "expected annual loss, population"),
    ("_EALPE", "expected annual loss, population equivalence"),
    ("_EALA", "expected annual loss, agriculture"),
    ("_AFREQ", "annualized frequency"),
    ("_EXPB", "exposure, building"),
    ("_EXPP", "exposure, population"),
    ("_EXPA", "exposure, agriculture"),
    ("_RISKS", "hazard-specific risk score"),
    ("_RISKR", "hazard-specific risk rating"),
]

# composite columns that must NOT enter the model: each folds social
# vulnerability and community resilience into the number, and those derive
# from CDC SVI and the Census Community Resilience Estimates, which are
# already our independent variables
EXCLUDED_COMPOSITES = [
    "RISK_SCORE", "RISK_RATNG", "RISK_SPCTL", "RISK_VALUE",
    "SOVI_SCORE", "SOVI_RATNG", "SOVI_SPCTL",
    "RESL_SCORE", "RESL_RATNG", "RESL_SPCTL", "RESL_VALUE", "CRF_VALUE",
]

# EAL columns for the four hazards we would actually use
QUALITY_HAZARDS = ["HWAV", "CFLD", "IFLD", "RFLD", "HRCN"]
QUALITY_SUFFIXES = ["_EALT", "_EALB", "_EALP", "_EALPE", "_EALA"]

# values NRI and similar products use to mark "not applicable / not computed"
SENTINELS = [-999, -9999, -99999, 9999, -1]


def sec(title):
    print("\n" + "=" * 78 + f"\n{title}\n" + "=" * 78)


def load():
    """Everything as string on read so no identifier is silently renumbered."""
    return pd.read_csv(NRI_PATH, dtype=str, low_memory=False)


def task1_inventory(df):
    sec("TASK 1 - FILE INVENTORY")
    print(f"path            : {NRI_PATH}")
    print(f"rows (data)     : {len(df):,}")
    print(f"columns         : {len(df.columns):,}")

    id_candidates = [c for c in df.columns
                     if c.upper() in ("TRACTFIPS", "GEOID", "STCOFIPS", "NRI_ID", "TRACT")]
    print(f"\nidentifier-like columns present: {id_candidates}")
    for c in id_candidates:
        v = df[c].dropna()
        lens = sorted(v.str.len().unique().tolist())
        print(f"  {c:12s} example={v.iloc[0]!r:22s} lengths={lens} "
              f"unique={v.nunique():,}")

    geo = "TRACTFIPS" if "TRACTFIPS" in df.columns else None
    if geo is None:
        print("\nNo TRACTFIPS column found; cannot confirm the tract identifier.")
        return None
    s = df[geo]
    md = s.str.startswith(MD_PREFIX)
    print(f"\nGEOID column    : {geo} (string, {sorted(s.str.len().unique())} digits)")
    print(f"starts with {MD_PREFIX} : {int(md.sum()):,} of {len(df):,}")
    print(f"unique values   : {s.nunique():,}  duplicates: {int(s.duplicated().sum())}")

    lengths = set(s.str.len())
    if lengths == {11}:
        print("grain           : 11-digit identifiers = CENSUS TRACT level, confirmed")
    else:
        print(f"grain           : identifier lengths {lengths}, NOT a clean tract set")

    for col, label in [("STATEFIPS", "state"), ("COUNTYFIPS", "county")]:
        if col in df.columns:
            print(f"{label:15s} : {sorted(df[col].dropna().unique())}")
    if "COUNTY" in df.columns:
        print(f"county name     : {sorted(df['COUNTY'].dropna().unique())}")
    return geo


def task1_dictionary():
    print("\n--- data dictionary ---")
    hits = []
    for root in (BASE, BASE.parent):
        for p in root.glob("*"):
            n = p.name.lower()
            # "nri" as a bare substring also matches "enriched"; require it to
            # sit on a token boundary so ols_tract_data_enriched.csv is not
            # reported as NRI documentation
            tokens = set(re.split(r"[^a-z0-9]+", n))
            if p.is_file() and ("nri" in tokens or any(
                    k in n for k in ("dictionary", "datadict", "codebook", "metadata"))):
                if p.suffix.lower() in (".pdf", ".xlsx", ".csv", ".txt", ".md", ".docx"):
                    hits.append(str(p.relative_to(BASE.parent)))
    # exclude our own audit outputs, which carry "nri" in their names and
    # would otherwise be reported as documentation on any re-run
    real = [h for h in hits
            if "variable_dictionary" not in h
            and "NRI_Table" not in h
            and not pathlib.PurePath(h).name.startswith("nri_audit")]
    if real:
        print("candidate dictionary files found:")
        for h in real:
            print("  ", h)
    else:
        print("NO NRI data dictionary is present in this directory or the repo root.")
        print("The only NRI-named file is the national table NRI_Table_CensusTracts.csv,")
        print("which is data, not documentation. Column meanings below are read from")
        print("the NRI naming convention, not from a dictionary shipped with the file.")


def task2_hazards(df):
    sec("TASK 2 - HAZARDS PRESENT")
    prefixes = sorted({c.split("_")[0] for c in df.columns
                       if "_" in c and c.split("_")[0] not in NON_HAZARD_PREFIXES
                       and len(c.split("_")[0]) == 4})
    hazard_prefixes = [p for p in prefixes if p in ALL_NRI_HAZARDS]
    unknown = [p for p in prefixes if p not in ALL_NRI_HAZARDS]

    print("Requested list, and whether each prefix appears:\n")
    for code, label in REQUESTED_HAZARDS.items():
        cols = [c for c in df.columns if c.startswith(code + "_")]
        mark = "PRESENT" if cols else "ABSENT"
        print(f"  {code}  {label:38s} {mark:8s} ({len(cols)} columns)")

    extra = [p for p in hazard_prefixes if p not in REQUESTED_HAZARDS]
    print(f"\nOther NRI hazard prefixes also present ({len(extra)}):")
    for p in extra:
        n = len([c for c in df.columns if c.startswith(p + "_")])
        print(f"  {p}  {ALL_NRI_HAZARDS[p]:38s} ({n} columns)")
    if unknown:
        print(f"\nPrefixes not recognised as NRI hazards: {unknown}")

    print("\n--- component types per hazard present ---")
    print("(a dash means that component does not exist for that hazard)\n")
    header = f"{'hazard':6s} " + " ".join(f"{s[0][1:]:>6s}" for s in COMPONENT_TYPES)
    print(header)
    for p in hazard_prefixes:
        row = f"{p:6s} "
        for suffix, _ in COMPONENT_TYPES:
            row += f"{('yes' if (p + suffix) in df.columns else '-'):>6s} "
        print(row)

    print("\ncomponent type key:")
    for suffix, meaning in COMPONENT_TYPES:
        print(f"  {suffix:8s} {meaning}")

    print("\nfull column list for the hazards on the requested list that are present:")
    for code in REQUESTED_HAZARDS:
        cols = [c for c in df.columns if c.startswith(code + "_")]
        if cols:
            print(f"\n  {code} ({REQUESTED_HAZARDS[code]}), {len(cols)} columns:")
            print("    " + ", ".join(cols))
    return hazard_prefixes


def task3_composites(df):
    sec("TASK 3 - COMPOSITE COLUMNS, EXCLUDED FROM USE")
    print("These must NOT be used as the risk variable. NRI's composite risk")
    print("score is expected annual loss multiplied by a social vulnerability")
    print("factor and divided by a community resilience factor. Those two")
    print("factors derive from CDC SVI and the Census Community Resilience")
    print("Estimates, which are already our independent variables. Using the")
    print("composite would place our predictors on both sides of the model.")
    print("We use expected annual loss columns only.\n")
    for c in EXCLUDED_COMPOSITES:
        present = "PRESENT -> EXCLUDE" if c in df.columns else "not in file"
        print(f"  {c:14s} {present}")
    others = [c for c in df.columns
              if c.startswith(("SOVI", "RESL", "CRF")) and c not in EXCLUDED_COMPOSITES]
    if others:
        print(f"\nOther social-vulnerability / resilience columns, also excluded: {others}")


def task5_quality(df, geo):
    sec("TASK 5 - DATA QUALITY, EXPECTED ANNUAL LOSS COLUMNS")
    rows = []
    for hz in QUALITY_HAZARDS:
        for suffix in QUALITY_SUFFIXES:
            col = hz + suffix
            if col not in df.columns:
                continue
            raw = df[col]
            blank = raw.isna() | (raw.astype(str).str.strip() == "")
            v = pd.to_numeric(raw, errors="coerce")
            unparsed = (~blank) & v.isna()
            sent = {s: int((v == s).sum()) for s in SENTINELS if (v == s).any()}
            nz = v.dropna()
            rows.append({
                "column": col,
                "n_missing": int(blank.sum()),
                "pct_missing": round(blank.sum() / len(df) * 100, 2),
                "n_unparseable": int(unparsed.sum()),
                "n_zero": int((nz == 0).sum()),
                "pct_zero": round((nz == 0).sum() / len(nz) * 100, 1) if len(nz) else np.nan,
                "min": nz.min() if len(nz) else np.nan,
                "max": nz.max() if len(nz) else np.nan,
                "mean": nz.mean() if len(nz) else np.nan,
                "median": nz.median() if len(nz) else np.nan,
                "skew": nz.skew() if len(nz) > 2 else np.nan,
                "sentinels_found": sent if sent else "",
            })
    out = pd.DataFrame(rows)
    pd.set_option("display.width", 200)
    print(out.to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
    print("\nSentinel check: NRI marks a hazard that does not apply to a tract with")
    print("an empty cell, not a numeric code. Any value found in")
    print(f"{SENTINELS} is reported in the sentinels_found column above;")
    print("blank there means none were found.")
    heavy = out[out["skew"] > 2]["column"].tolist()
    print(f"\ncolumns with skew above 2: {heavy}")
    return out


def task6_version(df):
    sec("TASK 6 - VERSION CHECK")
    version_like = [c for c in df.columns
                    if any(k in c.upper() for k in ("VERS", "RELEASE", "VINTAGE", "UPDATE"))]
    print(f"explicit version field in the file: "
          f"{version_like if version_like else 'NONE'}")
    has_ifld = any(c.startswith("IFLD_") for c in df.columns)
    has_rfld = any(c.startswith("RFLD_") for c in df.columns)
    print(f"\ninland flooding columns   : IFLD present={has_ifld}, RFLD present={has_rfld}")
    print("\nInference from the column set:")
    if has_ifld and not has_rfld:
        print("  The inland flooding hazard is coded IFLD, not RFLD. NRI renamed this")
        print("  hazard from Riverine Flooding (RFLD) to Inland Flooding (IFLD) when it")
        print("  rebuilt the hazard to include pluvial as well as fluvial flooding.")
        print("  A file carrying IFLD therefore postdates that rebuild, which is the")
        print("  change the professor flagged as the v1.20 concern.")
    elif has_rfld and not has_ifld:
        print("  The file carries RFLD, the pre-rebuild riverine-only name. The inland")
        print("  flooding numbers come from the older fluvial-only method.")
    else:
        print("  Both or neither present; the column set does not settle the version.")


def task4_mapping(df):
    sec("TASK 4 - THE FIVE REQUESTS AGAINST THIS FILE")
    heat = [c for c in df.columns if c.startswith("HWAV_")]
    cfld = [c for c in df.columns if c.startswith("CFLD_")]
    ifld = [c for c in df.columns if c.startswith("IFLD_")]
    ealb = [c for c in df.columns if c.endswith("_EALB")]
    slr = [c for c in df.columns
           if any(k in c.upper() for k in ("SLR", "SEALEV", "SEA_LEV", "TIDE"))]
    surge = [c for c in df.columns
             if any(k in c.upper() for k in ("SURGE", "SRGE", "STORMSURGE"))]
    zones = [c for c in df.columns
             if any(k in c.upper() for k in ("ZONE", "FLD_ZONE", "SFHA", "FIRM"))]

    print("1. Extreme heat exposure")
    print(f"   IN FILE. {len(heat)} heat wave columns, loss columns "
          f"{[c for c in heat if '_EAL' in c]}")
    print("\n2. Property damage costs")
    print(f"   IN FILE. {len(ealb)} building expected-annual-loss columns, one per")
    print(f"   hazard: {ealb[:6]} ... plus the all-hazard total EAL_VALB")
    print("\n3. Flood hazard zones")
    print(f"   PARTLY. Flood LOSS is present as coastal ({len(cfld)} columns) and")
    print(f"   inland ({len(ifld)} columns) expected annual loss.")
    print(f"   Flood ZONE designations (AE, VE, X) are NOT here: "
          f"zone-like columns found = {zones if zones else 'none'}.")
    print("   Those are the National Flood Hazard Layer, a separate FEMA product.")
    print("\n4. Sea level rise exposure")
    print(f"   NOT SEPARABLE. Columns matching sea level rise / tide terms: "
          f"{slr if slr else 'none'}")
    print("   NRI folds four subtypes into the single coastal flooding number and")
    print("   publishes only the combined total, so it cannot be split out here.")
    print("\n5. Storm surge inundation")
    print(f"   NOT SEPARABLE. Columns matching surge terms: "
          f"{surge if surge else 'none'}")
    print("   Same reason: surge is one of the four subtypes folded into coastal")
    print("   flooding, and only the combined total is published.")


def main():
    if not NRI_PATH.exists():
        raise SystemExit(f"NRI file not found at {NRI_PATH}")
    df = load()
    geo = task1_inventory(df)
    task1_dictionary()
    task2_hazards(df)
    task3_composites(df)
    task4_mapping(df)
    task5_quality(df, geo)
    task6_version(df)


if __name__ == "__main__":
    main()
