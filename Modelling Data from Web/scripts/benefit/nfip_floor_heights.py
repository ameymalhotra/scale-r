"""First-floor height above ground from NFIP policy elevation fields, summarised by block group and building type (D-185).

    /Users/.../Climate-Resilience---Miami-Dade/.venv/bin/python -I scripts/benefit/nfip_floor_heights.py

Source: OpenFEMA NfipPoliciesV3 (already redacted by FEMA), Miami-Dade
records (censusGeoid 12086), fields lowestFloorElevation and
lowestAdjacentGrade (from elevation certificates used in rating).
1. Floor height = lowest floor elevation minus lowest adjacent grade, kept
   between -5 and 20 ft (outside that range: keying errors, 9999 codes).
2. The same building appears once per policy year. Records are collapsed
   to one per building with a proxy key (census block, occupancy, the two
   elevations, construction date). The key is used in memory only.
3. Building type from occupancy: single-family (1, 11), multi-family and
   condo (2, 3, 12, 13, 15, 16), mobile home (14), non-residential (4, 6,
   17, 18, 19). The same four groups are made from the NSI occupancy type.
4. Median floor height by block group and type where at least 10 buildings;
   by tract and type where the block group has fewer; county by type
   otherwise. Only these summaries are written, never single records.
Coverage note: almost all records with these fields are in zones AE and AH
(rated with an elevation certificate), so X-zone buildings get the summary
of their block group, tract or county.
Writes outputs/benefit/module_d/nfip_floor_height_summary.csv (level, area,
type, buildings, median) and nfip_floor_height_summary.json.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.compute as pc
import pyarrow.dataset as ds

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import paths  # noqa: E402

MIN_N = 10
OCC = {1: "single_family", 11: "single_family", 2: "multi_family", 3: "multi_family", 12: "multi_family",
       13: "multi_family", 15: "multi_family", 16: "multi_family", 14: "mobile_home", 4: "non_residential",
       6: "non_residential", 17: "non_residential", 18: "non_residential", 19: "non_residential"}


def nsi_type(occtype):
    o = pd.Series(occtype).astype(str)
    return np.select([o.str.startswith("RES1"), o.str.startswith("RES2"), o.str.match(r"RES[3-6]")],
                     ["single_family", "mobile_home", "multi_family"], "non_residential")


def main():
    cols = ["censusGeoid", "occupancyType", "lowestFloorElevation", "lowestAdjacentGrade", "originalConstructionDate"]
    d = ds.dataset(paths.NFIP_POLICIES_PARQUET_FULL)
    p = d.to_table(columns=cols, filter=(ds.field("propertyState") == "FL") &
                   pc.starts_with(ds.field("censusGeoid"), "12086")).to_pandas()
    n_records = len(p)
    for c in ["lowestFloorElevation", "lowestAdjacentGrade"]:
        p[c] = pd.to_numeric(p[c], errors="coerce")
    p = p[p.lowestFloorElevation.notna() & p.lowestAdjacentGrade.notna()]
    p["fh"] = p.lowestFloorElevation - p.lowestAdjacentGrade
    p = p[p.fh.between(-5, 20)]
    p["type"] = p.occupancyType.map(OCC)
    p = p[p.type.notna()]
    n_with = len(p)
    p = p.drop_duplicates(["censusGeoid", "occupancyType", "lowestFloorElevation", "lowestAdjacentGrade",
                           "originalConstructionDate"])
    p["bg"], p["tract"] = p.censusGeoid.str[:12], p.censusGeoid.str[:11]
    rows = []
    for level, key in [("block_group", "bg"), ("tract", "tract")]:
        g = p.groupby([key, "type"]).fh.agg(["size", "median"]).reset_index()
        g = g[g["size"] >= MIN_N]
        rows.append(pd.DataFrame({"level": level, "area": g[key], "type": g.type, "buildings": g["size"],
                                  "median_ft": g["median"].round(2)}))
    c = p.groupby("type").fh.agg(["size", "median"]).reset_index()
    rows.append(pd.DataFrame({"level": "county", "area": "12086", "type": c.type, "buildings": c["size"],
                              "median_ft": c["median"].round(2)}))
    S = pd.concat(rows, ignore_index=True)
    out = paths.OUT_BENEFIT / "module_d"
    out.mkdir(parents=True, exist_ok=True)
    S.to_csv(out / "nfip_floor_height_summary.csv", index=False)
    R = {"policy_records": n_records, "records_with_fields_in_range": n_with, "buildings_after_collapse": int(len(p)),
         "county_by_type": c.set_index("type").round(2).to_dict("index"),
         "quartiles_ft": [round(float(p.fh.quantile(q)), 2) for q in (.25, .5, .75)],
         "summaries": S.groupby(["level", "type"]).size().rename("areas").reset_index().to_dict("records")}
    (out / "nfip_floor_height_summary.json").write_text(json.dumps(R, indent=2, default=str))
    print(json.dumps(R, indent=1, default=str))


def lookup(fd):
    """Floor height for each building (fd: DataFrame with GEOID_bg, GEOID_tract, occtype). Returns (ft, level)."""
    S = pd.read_csv(paths.OUT_BENEFIT / "module_d" / "nfip_floor_height_summary.csv", dtype={"area": str})
    t = nsi_type(fd.occtype.to_numpy())
    fh = np.full(len(fd), np.nan)
    lev = np.full(len(fd), "none", dtype=object)
    for level, col in [("block_group", "GEOID_bg"), ("tract", "GEOID_tract")]:
        m = S[S.level == level].set_index(["area", "type"]).median_ft
        v = pd.MultiIndex.from_arrays([fd[col].astype(str).to_numpy(), t]).map(lambda k: m.get(k, np.nan)).to_numpy(float)
        new = np.isnan(fh) & ~np.isnan(v)
        fh[new], lev[new] = v[new], level
    cm = S[S.level == "county"].set_index("type").median_ft
    v = pd.Series(t).map(cm).to_numpy(float)
    new = np.isnan(fh) & ~np.isnan(v)
    fh[new], lev[new] = v[new], "county"
    return fh, lev


if __name__ == "__main__":
    main()
