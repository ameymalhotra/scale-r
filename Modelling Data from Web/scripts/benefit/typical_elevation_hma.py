"""Typical building elevation project from FEMA HMA Subapplications, Florida (prompt 29 Part 2, D-197).

    /Users/.../Climate-Resilience---Miami-Dade/.venv/bin/python -I scripts/benefit/typical_elevation_hma.py

Rules (user, 16 Nov 2026):
- elevation projects only: primaryActivity == "Elevation" (FEMA's activity
  for structure elevation); Florida first, then South Florida (Miami-Dade,
  Broward, Palm Beach, Monroe) and Miami-Dade counts;
- funded only: status Closed, Approved, Obligated or Subaward Accepted.
  Withdrawn and Void are dropped as the user asked; denied, not selected,
  ineligible and still-in-review records are dropped too because they were
  never funded (user's choice, D-197). Every drop is counted;
- drop records with no building count or zero cost;
- cost = federal share + non-federal share (project cost without FEMA
  management costs), in 2025 dollars with CPI-U, fiscal year as cost year;
  homes = numberBuildingLocations;
- typical project = median homes and median cost per home; South Florida if
  it has at least 10 usable projects, otherwise all of Florida.
Writes outputs/benefit/typical_projects/hma_elevation.csv and hma_elevation_summary.json.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import paths  # noqa: E402

OUT = paths.OUT_BENEFIT / "typical_projects"
FUNDED = {"Closed", "Approved", "Obligated", "Subaward Accepted"}
SOUTH = {"MIAMI-DADE", "BROWARD", "PALM BEACH", "MONROE"}


def counties(s):
    s = str(s).upper().replace(" COUNTY", "").replace("DADE COUNTY", "MIAMI-DADE")
    return {c.strip() for c in s.replace(";", ",").split(",") if c.strip() and c.strip() != "NAN"}


def q(s):
    return {"median": float(s.median()), "p25": float(s.quantile(.25)), "p75": float(s.quantile(.75)),
            "mean": float(s.mean()), "n": int(s.notna().sum())}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    d = pd.read_csv(paths.HMA_SUBAPPS_FL_CSV, low_memory=False)
    e = d[d.primaryActivity.eq("Elevation")].copy()
    e["counties"] = e.benefitingCounties.map(counties)
    e["miami_dade"] = e.counties.map(lambda c: "MIAMI-DADE" in c or "DADE" in c)
    e["south_florida"] = e.counties.map(lambda c: bool(c & SOUTH) or "DADE" in c)
    cpi = pd.read_csv(paths.CPI_ANNUAL_CSV).set_index("year").factor_to_2025
    e["cost"] = e.federalShareAmount.fillna(0) + e.nonFederalShareAmount.fillna(0)
    e["cost_2025"] = e.cost * e.fiscalYear.clip(upper=2025).map(cpi)
    e["homes"] = e.numberBuildingLocations
    e["cost_per_home_2025"] = e.cost_2025 / e.homes.where(e.homes > 0)
    steps = {"elevation_records_florida": len(e), "by_status": e.status.value_counts().to_dict(),
             "miami_dade_records": int(e.miami_dade.sum()), "south_florida_records": int(e.south_florida.sum())}
    drops = {}
    keep = e.copy()
    NOT_FUNDED = {"Not Approved / Denied", "Not Selected", "Ineligible"}
    for name, rule in [("withdrawn_or_void", lambda k: k.status.isin(["Withdrawn", "Void"])),
                       ("not_funded_denied_not_selected_ineligible", lambda k: k.status.isin(NOT_FUNDED)),
                       ("not_funded_yet_pending_or_in_review", lambda k: ~k.status.isin(FUNDED)),
                       ("no_home_count", lambda k: ~(k.homes > 0)), ("zero_cost", lambda k: ~(k.cost > 0))]:
        bad = rule(keep)
        drops[name] = int(bad.sum()); keep = keep[~bad]
    steps["dropped"] = drops
    steps["usable_florida"] = len(keep)
    steps["usable_south_florida"] = int(keep.south_florida.sum())
    steps["usable_miami_dade"] = int(keep.miami_dade.sum())
    use_sf = steps["usable_south_florida"] >= 10
    base = keep[keep.south_florida] if use_sf else keep
    steps["typical_from"] = "South Florida" if use_sf else "all of Florida (South Florida has fewer than 10 usable projects)"
    S = {}
    for name, g in [("florida", keep), ("south_florida", keep[keep.south_florida]), ("miami_dade", keep[keep.miami_dade])]:
        S[name] = {"projects": len(g), "homes": q(g.homes) if len(g) else None,
                   "cost_per_home_2025": q(g.cost_per_home_2025) if len(g) else None,
                   "cost_per_project_2025": q(g.cost_2025) if len(g) else None,
                   "single_home_share": round(float((g.homes == 1).mean()), 3) if len(g) else None,
                   "fiscal_years": [int(g.fiscalYear.min()), int(g.fiscalYear.max())] if len(g) else None,
                   "by_program": g.program.value_counts().to_dict()}
    # recent projects only, as a check on the price trend (FY2018 onward)
    r = keep[keep.fiscalYear >= 2018]
    S["florida_fy2018_on"] = {"projects": len(r), "homes": q(r.homes), "cost_per_home_2025": q(r.cost_per_home_2025)}
    hb = keep.homes.where(keep.homes > 1)
    S["florida_multi_home"] = {"projects": int(hb.notna().sum()), "homes": q(hb.dropna()),
                               "cost_per_home_2025": q(keep.cost_per_home_2025[keep.homes > 1])}
    typ = {"homes": int(round(base.homes.median())), "cost_per_home_2025": float(base.cost_per_home_2025.median()),
           "cost_per_home_p25": float(base.cost_per_home_2025.quantile(.25)),
           "cost_per_home_p75": float(base.cost_per_home_2025.quantile(.75)), "from": steps["typical_from"]}
    R = {"steps": steps, "summary": S, "typical": typ,
         "elevate_florida_assumption": {"homes": 10, "cost_per_home_2025": 267000.0,
                                         "note": "assumption: Elevate Florida May 2025 snapshot, about 2,000 homes and more than $400M federal at 75% share, so about $267,000 total per home"}}
    keep[["subapplicationIdentifier", "fiscalYear", "program", "status", "subapplicantName", "benefitingCounties", "south_florida",
          "miami_dade", "homes", "cost", "cost_2025", "cost_per_home_2025"]].to_csv(OUT / "hma_elevation.csv", index=False)
    (OUT / "hma_elevation_summary.json").write_text(json.dumps(R, indent=2, default=str))
    print(json.dumps(R, indent=1, default=str))


if __name__ == "__main__":
    main()
