"""Investment by surface heat tercile, broken down by project Hazard_Focus.

Follow-up to Stage B (exposure_vs_investment.md, section 3.4). Descriptive
only: no model. Reads the analysis table, the exposure table, the allocation
ledger and the project file; modifies none of them.

Terciles: the 698-tract frame split into three equal-count groups by
`heat_lst_popwt_mean_f` (population-weighted mean surface temperature), ranked
with ties broken by order (pd.qcut on rank(method="first")), exactly as in
exposure_vs_investment.py. The 28-person Pennsuco tract (the only tract under
100 residents in the frame) is kept, as in Stage B; a row without it is shown.

Dollars come from the allocation ledger (data/processed/investment/
allocation_audit_tract.csv), so the allocation rules are the existing ones:
parcel, neighborhood and corridor projects whole to the containing tract;
municipality and county projects spread by population. "Sited" = the
single-unit path only (parcel, neighborhood, corridor).

Three summaries of dollars per resident, for every breakdown:
  pooled  total dollars in the tercile / total residents in the tercile
  mean    mean of tract dollars-per-resident
  median  median of tract dollars-per-resident

Hazard_Focus groups: each of the six values, plus "flood-related" =
Flooding + Coastal Hazards + Storms & Hurricanes.

Sensitivity: a few Extreme Heat projects dominate each tercile's heat money.
  S1  drop The Underline Phase 2 and 3 (SCALER-1093, SCALER-1094) and the
      Jose Martin Park Adaptive Re-Design (SCALER-0595). These are also the
      single largest sited heat project in each tercile.
  S2  drop the five largest Extreme Heat projects county-wide (by cost).
  Plus a count measure that no single large project can dominate: sited
  Extreme Heat projects per 100,000 residents.

Usage: ../.venv/bin/python scripts/04_exposure/heat_tercile_investment.py
Outputs: outputs/exposure/heat_terciles/*.csv and heat_terciles_log.txt (tee)
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import paths  # noqa: E402
from analysis_variables import load_tract  # noqa: E402

OUT = paths.OUTPUTS / "exposure" / "heat_terciles"
LABELS = ["T1 coolest", "T2 middle", "T3 hottest"]
FOCUS = ["Flooding", "Storms & Hurricanes", "Coastal Hazards", "Infrastructure Failure",
         "Multi-Hazard", "Extreme Heat"]
FLOOD = {"Flooding", "Coastal Hazards", "Storms & Hurricanes"}
DOMINANT = ["SCALER-1093", "SCALER-1094", "SCALER-0595"]
pd.set_option("display.width", 250)


def sec(t):
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78, flush=True)


def load():
    tr = load_tract()
    ex = pd.read_csv(paths.EXPOSURE_DIR / "exposure_tract.csv", dtype={"GEOID": str})
    tr = tr.merge(ex[["GEOID", "heat_lst_popwt_mean_f", "low_pop_flag"]], on="GEOID", validate="1:1")
    assert len(tr) == 698 and tr.heat_lst_popwt_mean_f.notna().all()
    tr["tercile"] = pd.qcut(tr.heat_lst_popwt_mean_f.rank(method="first"), 3, labels=LABELS)
    led = pd.read_csv(paths.INVESTMENT_DIR / "allocation_audit_tract.csv", dtype={"GEOID": str})
    proj = pd.read_csv(paths.PROJECT_CSV, dtype=str, encoding="utf-8-sig")
    proj["cost"] = pd.to_numeric(proj["Estimated_Cost"], errors="coerce")
    led = led.merge(proj[["Project_ID", "Project_Name", "Hazard_Focus", "cost"]], on="Project_ID",
                    how="left", validate="m:1")
    assert led.Hazard_Focus.notna().all()
    n_all = led.Project_ID.nunique()
    total_all = led.amount.sum()
    led = led[led.GEOID.isin(tr.GEOID)].merge(tr[["GEOID", "tercile"]], on="GEOID")
    print(f"ledger: {n_all:,} projects, ${total_all:,.0f}; inside the 698-tract frame ${led.amount.sum():,.0f} "
          f"(the rest went to the 9 zero-population tracts)")
    led["sited"] = led["path"] == "single-unit"
    return tr, led, proj


def per_resident(tr, led, label):
    """pooled, mean and median dollars per resident by tercile for one slice of the ledger."""
    by_tract = led.groupby("GEOID").amount.sum().reindex(tr.GEOID).fillna(0).to_numpy()
    d = tr.assign(dollars=by_tract, per_res=by_tract / tr.population.to_numpy())
    g = d.groupby("tercile", observed=True)
    out = pd.DataFrame({"pooled": g.dollars.sum() / g.population.sum(),
                        "mean": g.per_res.mean(), "median": g.per_res.median()})
    out.insert(0, "slice", label)
    return out.reset_index()


def tercile_profile(tr):
    g = tr.groupby("tercile", observed=True)
    return pd.DataFrame({"tracts": g.size(), "tracts_under_100": g.low_pop_flag.sum(),
                         "residents": g.population.sum(),
                         "min_f": g.heat_lst_popwt_mean_f.min(), "max_f": g.heat_lst_popwt_mean_f.max()})


def breakdown(tr, led, tag=""):
    rows = []
    for sited in (False, True):
        L = led[led.sited] if sited else led
        path = "sited" if sited else "all"
        rows.append(per_resident(tr, L, f"{path}: all projects"))
        for f in FOCUS:
            rows.append(per_resident(tr, L[L.Hazard_Focus == f], f"{path}: {f}"))
        rows.append(per_resident(tr, L[L.Hazard_Focus.isin(FLOOD)], f"{path}: flood-related"))
    t = pd.concat(rows)
    if tag:
        t.insert(0, "run", tag)
    return t


def heat_counts(tr, led):
    h = led[led.Hazard_Focus == "Extreme Heat"]
    res = tr.groupby("tercile", observed=True).population.sum()
    out = pd.DataFrame({
        "heat_projects_with_any_dollars": h.groupby("tercile", observed=True).Project_ID.nunique(),
        "heat_projects_sited": h[h.sited].groupby("tercile", observed=True).Project_ID.nunique(),
        "sited_heat_dollars": h[h.sited].groupby("tercile", observed=True).amount.sum(),
    }).reindex(res.index).fillna(0)
    out["sited_heat_projects_per_100k"] = out.heat_projects_sited / res * 1e5
    return out


def dominance(led):
    h = led[(led.Hazard_Focus == "Extreme Heat") & led.sited]
    t = h.groupby(["tercile", "Project_ID", "Project_Name", "scale"], observed=True).amount.sum().reset_index()
    tot = t.groupby("tercile", observed=True).amount.transform("sum")
    t["share_of_tercile_sited_heat"] = t.amount / tot
    return t.sort_values(["tercile", "amount"], ascending=[True, False]).groupby("tercile", observed=True).head(3)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tr, led, proj = load()

    sec("1. TERCILES (population-weighted mean surface temperature, 698 tracts)")
    prof = tercile_profile(tr)
    print(prof.to_string(float_format=lambda v: f"{v:,.1f}"))
    prof.to_csv(OUT / "tercile_profile.csv")

    sec("2. DOLLARS PER RESIDENT BY HAZARD_FOCUS: pooled, tract mean, tract median")
    base = breakdown(tr, led)
    piv = base.pivot_table(index="slice", columns="tercile", values=["pooled", "mean", "median"],
                           observed=True, sort=False)
    print(piv.to_string(float_format=lambda v: f"{v:,.0f}"))
    base.to_csv(OUT / "per_resident_by_focus.csv", index=False)
    k = tr.low_pop_flag == 0
    nolow = per_resident(tr[k], led[led.GEOID.isin(tr.GEOID[k])], "all: all projects, without the tract under 100")
    print("\nwithout the 28-person tract:")
    print(nolow.to_string(index=False, float_format=lambda v: f"{v:,.0f}"))
    nolow.to_csv(OUT / "per_resident_without_low_pop.csv", index=False)

    sec("3. EXTREME HEAT PROJECTS BY TERCILE")
    hc = heat_counts(tr, led)
    print(hc.to_string(float_format=lambda v: f"{v:,.1f}"))
    hc.to_csv(OUT / "heat_project_counts.csv")
    dom = dominance(led)
    print("\nlargest sited Extreme Heat projects in each tercile:")
    print(dom.to_string(index=False, float_format=lambda v: f"{v:,.2f}"))
    dom.to_csv(OUT / "dominant_heat_projects.csv", index=False)

    sec("4. SENSITIVITY: dropping the dominant Extreme Heat projects")
    top5 = (proj[(proj.Hazard_Focus == "Extreme Heat") & proj.Project_ID.isin(led.Project_ID)]
            .nlargest(5, "cost")[["Project_ID", "Project_Name", "cost"]])
    print("S2 drops the five largest Extreme Heat projects county-wide:")
    print(top5.to_string(index=False))
    runs = {"S0 baseline": led,
            "S1 drop Underline 2 and 3 and SCALER-0595": led[~led.Project_ID.isin(DOMINANT)],
            "S2 drop the five largest heat projects": led[~led.Project_ID.isin(top5.Project_ID)]}
    rows, counts = [], []
    for name, L in runs.items():
        b = breakdown(tr, L, name)
        rows.append(b[b.slice.isin(["all: all projects", "all: Extreme Heat", "sited: all projects",
                                    "sited: Extreme Heat"])])
        c = heat_counts(tr, L)
        c.insert(0, "run", name)
        counts.append(c.reset_index())
    sens = pd.concat(rows)
    sp = sens.pivot_table(index=["run", "slice"], columns="tercile", values="pooled", observed=True, sort=False)
    sp["coolest_to_hottest_ratio"] = sp["T1 coolest"] / sp["T3 hottest"]
    print("\npooled dollars per resident:")
    print(sp.to_string(float_format=lambda v: f"{v:,.2f}"))
    sens.to_csv(OUT / "sensitivity_per_resident.csv", index=False)
    cc = pd.concat(counts)
    print("\nsited Extreme Heat projects per 100,000 residents:")
    print(cc.pivot_table(index="run", columns="tercile", values="sited_heat_projects_per_100k", observed=True,
                         sort=False).to_string(float_format=lambda v: f"{v:,.2f}"))
    cc.to_csv(OUT / "sensitivity_heat_counts.csv", index=False)


if __name__ == "__main__":
    main()
