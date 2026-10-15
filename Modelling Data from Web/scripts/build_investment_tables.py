"""Build the tract- and block-group-level investment outcome tables.

Aggregation only - nothing is modeled, no unit is dropped, no scale tag is
reclassified. Zero-investment units are kept.

Outputs:
  tract_investment.csv        707 rows
  blockgroup_investment.csv  1843 rows
  output/allocation_audit_<grain>.csv   per-project x unit allocation ledger

Usage: python scripts/build_investment_tables.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from allocation import (  # noqa: E402
    UNINCORPORATED, assign_municipality, load_population, load_units,
    municipality_members, normalize_municipality,
)
from scaler_projects import BASE, ensure_output_dir, load_typed  # noqa: E402

KEEP_STATUS = ["Completed", "Funded", "Ongoing"]
SINGLE_UNIT_SCALES = ["Parcel", "Neighborhood", "Corridor"]
JOIN_KEYS = BASE / "output" / "project_join_keys.csv"
GEOID_COL = {"tract": "tract_GEOID", "bg": "bg_GEOID"}


def large_project_ids(df):
    """The two known footprint-misrepresentation groups, identified by name.

    5 SMART Program transit corridors + 19 SFWMD basin-resiliency projects.
    These are flagged, NOT excluded and NOT reclassified.
    """
    smart = df[df["Project_Name"].str.contains("SMART Program", na=False)]
    sfwmd = df[
        df["Jurisdiction"].str.strip().eq("SFWMD")
        & df["scale"].eq("Parcel")
        & df["Project_Name"].str.contains("Basin|Coastal Structure", case=False, na=False)
    ]
    return set(smart["Project_ID"]), set(sfwmd["Project_ID"])


def build_ledger(proj, units, pop, grain):
    """One row per (project, receiving unit) with the allocated dollar amount.

    Every project's rows sum to exactly its Estimated_Cost.
    """
    geo_col = GEOID_COL[grain]
    keys = pd.read_csv(JOIN_KEYS, dtype=str).set_index("Project_ID")[geo_col]
    muni_assign = assign_municipality(units)
    pop_map = pop.set_index("GEOID")["population"]
    all_geoids = units["GEOID"].tolist()

    rows = []
    fallbacks = {}
    for _, p in proj.iterrows():
        pid, cost, scale = p["Project_ID"], p["cost_num"], p["scale"]
        if scale in SINGLE_UNIT_SCALES:
            rows.append((pid, keys.loc[pid], cost, scale, "single-unit"))
            continue
        if scale == "Municipality":
            name = normalize_municipality(p["Jurisdiction"])
            members, path = municipality_members(units, muni_assign, name)
            if path != "centroid":
                fallbacks[name] = path
            if not members:
                raise SystemExit(
                    f"{pid}: municipality '{name}' has no recipient unit at "
                    f"{grain} grain - dollars would leak. Stop and resolve.")
            path_label = f"municipality ({path})"
        elif scale == "County":
            members, path_label = all_geoids, "county"
        else:
            raise SystemExit(f"{pid}: unhandled scale tag '{scale}'")

        w = pop_map.reindex(members).fillna(0.0)
        if w.sum() <= 0:
            raise SystemExit(
                f"{pid}: recipient set for '{scale}' has zero total population "
                f"at {grain} grain - population weighting is undefined.")
        share = cost * (w / w.sum())
        for geoid, amt in share.items():
            rows.append((pid, geoid, amt, scale, path_label))

    led = pd.DataFrame(rows, columns=["Project_ID", "GEOID", "amount",
                                      "scale", "path"])
    if fallbacks:
        print(f"  [{grain}] intersect fallback used for: "
              f"{', '.join(sorted(fallbacks))}")
    return led


def build_table(grain, proj, smart_ids, sfwmd_ids):
    units = load_units(grain)
    pop = load_population(grain)
    units = units.merge(pop, on="GEOID", how="left")
    n_expected = {"tract": 707, "bg": 1843}[grain]
    assert len(units) == n_expected, f"{grain}: {len(units)} units, expected {n_expected}"
    assert units["population"].notna().all(), f"{grain}: missing population"

    led = build_ledger(proj, units, pop, grain)

    out = units[["GEOID", "ALAND", "population"]].copy()
    tot = led.groupby("GEOID")["amount"].sum()
    out["investment_total"] = out["GEOID"].map(tot).fillna(0.0)

    # per-capita / per-area: undefined where the denominator is zero. Left as
    # NaN (empty in the CSV) and reported - not silently set to 0.
    out["investment_per_capita"] = np.where(
        out["population"] > 0, out["investment_total"] / out["population"], np.nan)
    out["investment_per_area"] = np.where(
        out["ALAND"] > 0, out["investment_total"] / out["ALAND"], np.nan)
    out["investment_any"] = (out["investment_total"] > 0).astype(int)

    types = sorted(proj["Infrastructure_Type"].unique())
    tmap = proj.set_index("Project_ID")["Infrastructure_Type"]
    led["type"] = led["Project_ID"].map(tmap)
    for t in types:
        s = led[led["type"] == t].groupby("GEOID")["amount"].sum()
        out[f"investment_type_{t.lower()}"] = out["GEOID"].map(s).fillna(0.0)

    for s_name in ["Parcel", "Neighborhood", "Corridor", "Municipality", "County"]:
        s = led[led["scale"] == s_name].groupby("GEOID")["amount"].sum()
        out[f"investment_scale_{s_name.lower()}"] = out["GEOID"].map(s).fillna(0.0)

    contrib = led[led["amount"] > 0]
    out["project_count"] = out["GEOID"].map(
        contrib.groupby("GEOID")["Project_ID"].nunique()).fillna(0).astype(int)
    # ADDITION beyond the requested columns: the single-unit-only count, so the
    # county-distributed projects (which touch every unit) can be netted out.
    single = contrib[contrib["path"] == "single-unit"]
    out["project_count_single_unit"] = out["GEOID"].map(
        single.groupby("GEOID")["Project_ID"].nunique()).fillna(0).astype(int)

    big = smart_ids | sfwmd_ids
    flagged = contrib[contrib["Project_ID"].isin(big)]["GEOID"].unique()
    out["flag_large_project"] = out["GEOID"].isin(flagged).astype(int)

    out = out.drop(columns=["ALAND"]).sort_values("GEOID").reset_index(drop=True)
    return out, led


def main():
    df = load_typed()
    smart_ids, sfwmd_ids = large_project_ids(df)
    proj = df[df["Project_Status"].isin(KEEP_STATUS)].copy()
    print(f"projects: {len(df)} total -> {len(proj)} after status filter "
          f"(kept {KEEP_STATUS}, dropped Planned)")
    print(f"dollars : ${df['cost_num'].sum():,.0f} -> ${proj['cost_num'].sum():,.0f}")

    outdir = ensure_output_dir()
    for grain, fname in [("tract", "tract_investment.csv"),
                         ("bg", "blockgroup_investment.csv")]:
        print(f"\nbuilding {grain} table ...")
        table, led = build_table(grain, proj, smart_ids, sfwmd_ids)
        allocated = table["investment_total"].sum()
        expected = proj["cost_num"].sum()
        print(f"  units            : {len(table)}")
        print(f"  allocated dollars: ${allocated:,.2f}")
        print(f"  filtered dollars : ${expected:,.2f}")
        print(f"  difference       : ${allocated - expected:,.6f}")
        assert abs(allocated - expected) < 0.01, "RECONCILIATION FAILED"
        table.to_csv(BASE / fname, index=False)
        led.to_csv(outdir / f"allocation_audit_{grain}.csv", index=False)
        print(f"  wrote {fname} and output/allocation_audit_{grain}.csv")


if __name__ == "__main__":
    main()
