"""Diagnostics on the built investment tables. Reporting only - reads the
CSVs and the allocation ledgers, computes nothing new into them.

Usage: python scripts/report_investment_tables.py
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_investment_tables import KEEP_STATUS, large_project_ids  # noqa: E402
from scaler_projects import BASE, OUTPUT_DIR, load_typed  # noqa: E402

GRAINS = [("tract", "tract_investment.csv", 707, 38.0),
          ("bg", "blockgroup_investment.csv", 1843, 63.6)]


def sec(t):
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)


def status_filter_impact(df, proj):
    sec("1. STATUS FILTER IMPACT")
    tot_all, tot_keep = df["cost_num"].sum(), proj["cost_num"].sum()
    print(f"projects : {len(proj):,} of {len(df):,} survive "
          f"({len(proj)/len(df)*100:.1f}%)")
    print(f"dollars  : ${tot_keep:,.0f} of ${tot_all:,.0f} "
          f"({tot_keep/tot_all*100:.1f}% retained; "
          f"${tot_all-tot_keep:,.0f} removed)")
    print("\nby status:")
    t = df.groupby("Project_Status").agg(n=("Project_ID", "size"),
                                         dollars=("cost_num", "sum"))
    t["pct_dollars"] = t["dollars"] / tot_all * 100
    t["kept"] = [s in KEEP_STATUS for s in t.index]
    print(t.to_string(float_format=lambda v: f"{v:,.1f}"))
    print("\npost-filter project-level concentration:")
    c = proj["cost_num"]
    print(f"  skew             : {c.skew():.2f}   (unfiltered 25.78)")
    print(f"  top 50 share     : {c.nlargest(50).sum()/tot_keep*100:.1f}%"
          f"   (unfiltered 77.0%)")
    print(f"  top 10 share     : {c.nlargest(10).sum()/tot_keep*100:.1f}%"
          f"   (unfiltered 51.1%)")
    print(f"  largest record   : {c.max():,.0f} "
          f"({c.max()/tot_keep*100:.1f}% of filtered dollars)")
    print(f"  median / mean    : ${c.median():,.0f} / ${c.mean():,.0f}")


def problem_projects(df, proj):
    sec("2. THE TWO PROBLEM GROUPS UNDER THE STATUS FILTER")
    smart, sfwmd = large_project_ids(df)
    tot_all, tot_keep = df["cost_num"].sum(), proj["cost_num"].sum()
    for label, ids in [("5 SMART Program transit corridors", smart),
                       ("19 SFWMD basin-resiliency projects", sfwmd)]:
        g = df[df["Project_ID"].isin(ids)]
        kept = g[g["Project_Status"].isin(KEEP_STATUS)]
        print(f"\n--- {label} ({len(g)} records) ---")
        print(f"unfiltered dollars : ${g['cost_num'].sum():,.0f} "
              f"({g['cost_num'].sum()/tot_all*100:.1f}% of the $22.48B)")
        print("status values:")
        print(g.groupby("Project_Status").agg(
            n=("Project_ID", "size"), dollars=("cost_num", "sum")).to_string(
            float_format=lambda v: f"{v:,.0f}"))
        print(f"SURVIVING          : {len(kept)} of {len(g)} records, "
              f"${kept['cost_num'].sum():,.0f}")
        print(f"share of FILTERED dollars : "
              f"{kept['cost_num'].sum()/tot_keep*100:.1f}%")
        with pd.option_context("display.max_colwidth", 52):
            print(g[["Project_ID", "Project_Name", "Project_Status", "cost_num"]]
                  .sort_values("cost_num", ascending=False)
                  .to_string(index=False, float_format=lambda v: f"{v:,.0f}"))
    both = df[df["Project_ID"].isin(smart | sfwmd)]
    bk = both[both["Project_Status"].isin(KEEP_STATUS)]
    print(f"\nCOMBINED: {len(bk)} of {len(both)} records survive, "
          f"${bk['cost_num'].sum():,.0f} = "
          f"{bk['cost_num'].sum()/tot_keep*100:.1f}% of filtered dollars "
          f"(was {both['cost_num'].sum()/tot_all*100:.1f}% of unfiltered)")


def zero_shares(tables, ledgers):
    sec("3. ZERO-INVESTMENT SHARE AFTER FILTERING")
    print("Two readings. The county path spreads a little money into EVERY unit,")
    print("so the raw zero count understates true absence of local investment.\n")
    for grain, _, n_units, unfiltered_zero in GRAINS:
        t, led = tables[grain], ledgers[grain]
        raw_zero = int((t["investment_total"] == 0).sum())
        no_county = led[led["scale"] != "County"]
        hit = set(no_county.loc[no_county["amount"] > 0, "GEOID"])
        ex_county_zero = n_units - len(hit)
        single = led[led["path"] == "single-unit"]
        hit_single = set(single.loc[single["amount"] > 0, "GEOID"])
        print(f"--- {grain} ({n_units} units) ---")
        print(f"  unfiltered point-presence zeros (prior profile): "
              f"{unfiltered_zero:.1f}%")
        print(f"  zeros, all allocation paths      : {raw_zero} "
              f"({raw_zero/n_units*100:.1f}%)")
        print(f"  zeros, EXCLUDING county path     : {ex_county_zero} "
              f"({ex_county_zero/n_units*100:.1f}%)")
        print(f"  zeros, single-unit path only     : "
              f"{n_units - len(hit_single)} "
              f"({(n_units - len(hit_single))/n_units*100:.1f}%)")


def reconciliation(tables, proj):
    sec("4. RECONCILIATION")
    exp = proj["cost_num"].sum()
    for grain, fname, n_units, _ in GRAINS:
        t = tables[grain]
        got = t["investment_total"].sum()
        print(f"{grain:6s}: allocated ${got:,.2f} vs filtered ${exp:,.2f} "
              f"| diff ${got-exp:,.6f} | rows {len(t)} (expected {n_units}) "
              f"| {'OK' if abs(got-exp) < .01 else 'MISMATCH'}")
        scale_cols = [c for c in t.columns if c.startswith("investment_scale_")]
        type_cols = [c for c in t.columns if c.startswith("investment_type_")]
        print(f"        scale columns sum ${t[scale_cols].sum().sum():,.2f}"
              f" | type columns sum ${t[type_cols].sum().sum():,.2f}")


def population_issues(tables):
    sec("5. ZERO-POPULATION UNITS")
    for grain, _, _, _ in GRAINS:
        t = tables[grain]
        zp = t[t["population"] == 0]
        zpi = zp[zp["investment_total"] > 0]
        print(f"\n--- {grain} ---")
        print(f"units with population 0              : {len(zp)}")
        print(f"  of those, with NON-ZERO investment : {len(zpi)}  "
              f"(investment_per_capita is UNDEFINED - left empty, not zeroed)")
        if len(zpi):
            print(zpi[["GEOID", "population", "investment_total",
                       "project_count", "flag_large_project"]].to_string(
                index=False, float_format=lambda v: f"{v:,.0f}"))
        print(f"units with per_capita empty          : "
              f"{int(t['investment_per_capita'].isna().sum())}")
        print(f"units with per_area empty (ALAND=0)  : "
              f"{int(t['investment_per_area'].isna().sum())}")


def per_capita_dist(tables, ledgers, proj):
    sec("6. INVESTMENT PER CAPITA")
    names = proj.set_index("Project_ID")["Project_Name"]
    for grain, _, _, _ in GRAINS:
        t, led = tables[grain], ledgers[grain]
        pc = t["investment_per_capita"].dropna()
        print(f"\n--- {grain} ---")
        print(pc.describe(percentiles=[.05, .25, .5, .75, .95, .99]).to_string(
            float_format=lambda v: f"{v:,.2f}"))
        print(f"  units at exactly 0 : {int((pc == 0).sum())}")
        print("\ntop 10 by investment_per_capita:")
        top = t.nlargest(10, "investment_per_capita")
        for _, r in top.iterrows():
            contrib = led[(led["GEOID"] == r["GEOID"]) & (led["amount"] > 0)]
            contrib = contrib.nlargest(3, "amount")
            who = "; ".join(
                f"{names.get(p, p)[:44]} (${a:,.0f}, {s})"
                for p, a, s in zip(contrib["Project_ID"], contrib["amount"],
                                   contrib["scale"]))
            print(f"  {r['GEOID']}  pop={int(r['population']):>6,}  "
                  f"total=${r['investment_total']:>14,.0f}  "
                  f"per_cap=${r['investment_per_capita']:>12,.0f}  "
                  f"flag={int(r['flag_large_project'])}")
            print(f"      top contributors: {who}")


def coverage(tables, ledgers):
    sec("7. COVERAGE BY ALLOCATION PATH")
    for grain, _, n_units, _ in GRAINS:
        t, led = tables[grain], ledgers[grain]
        pos = led[led["amount"] > 0]
        print(f"\n--- {grain} ({n_units} units) ---")
        rows = []
        for path in ["single-unit", "municipality (centroid)",
                     "municipality (intersect-fallback)", "county"]:
            sub = pos[pos["path"] == path]
            if len(sub) == 0:
                continue
            rows.append({"path": path, "n_projects": sub["Project_ID"].nunique(),
                         "units_receiving": sub["GEOID"].nunique(),
                         "dollars": f"{sub['amount'].sum():,.0f}"})
        print(pd.DataFrame(rows).to_string(index=False))
        county_units = set(pos.loc[pos["scale"] == "County", "GEOID"])
        other_units = set(pos.loc[pos["scale"] != "County", "GEOID"])
        only_county = county_units - other_units
        print(f"\nunits receiving ANY investment      : "
              f"{int(t['investment_any'].sum())}")
        print(f"units receiving via county path     : {len(county_units)}")
        print(f"units receiving via non-county path : {len(other_units)}")
        print(f"** units receiving ONLY via county  : {len(only_county)} "
              f"({len(only_county)/n_units*100:.1f}% of all units) **")
        if only_county:
            oc = t[t["GEOID"].isin(only_county)]
            print(f"   their total investment: ${oc['investment_total'].sum():,.0f} "
                  f"({oc['investment_total'].sum()/t['investment_total'].sum()*100:.2f}% "
                  f"of allocated dollars)")
            print(f"   median amount per such unit: "
                  f"${oc['investment_total'].median():,.0f}")
        print(f"\nunits flagged flag_large_project    : "
              f"{int(t['flag_large_project'].sum())} "
              f"({t['flag_large_project'].mean()*100:.1f}%)")
        print("project_count distribution (all paths, county inflates this):")
        print(t["project_count"].describe().to_string(
            float_format=lambda v: f"{v:,.1f}"))
        print("project_count_single_unit distribution:")
        print(t["project_count_single_unit"].describe().to_string(
            float_format=lambda v: f"{v:,.1f}"))


def breakdowns(tables, proj):
    sec("8. COLUMN BREAKDOWNS (what the category columns actually are)")
    print("Infrastructure_Type categories present after filtering: "
          f"{sorted(proj['Infrastructure_Type'].unique())}")
    for grain, _, _, _ in GRAINS:
        t = tables[grain]
        print(f"\n--- {grain} ---")
        cols = [c for c in t.columns if c.startswith(("investment_type_",
                                                      "investment_scale_"))]
        s = pd.DataFrame({
            "dollars": t[cols].sum(),
            "pct": t[cols].sum() / t["investment_total"].sum() * 100,
            "units_nonzero": (t[cols] > 0).sum(),
        })
        print(s.to_string(float_format=lambda v: f"{v:,.1f}"))


def main():
    df = load_typed()
    proj = df[df["Project_Status"].isin(KEEP_STATUS)].copy()
    tables, ledgers = {}, {}
    for grain, fname, _, _ in GRAINS:
        tables[grain] = pd.read_csv(BASE / fname, dtype={"GEOID": str})
        ledgers[grain] = pd.read_csv(OUTPUT_DIR / f"allocation_audit_{grain}.csv",
                                     dtype={"GEOID": str})
    status_filter_impact(df, proj)
    problem_projects(df, proj)
    zero_shares(tables, ledgers)
    reconciliation(tables, proj)
    population_issues(tables)
    per_capita_dist(tables, ledgers, proj)
    coverage(tables, ledgers)
    breakdowns(tables, proj)


if __name__ == "__main__":
    main()
