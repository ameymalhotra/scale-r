"""Six quick checks of the flood effect with the fixed-effects hedonic model (D-195).

    /Users/.../Climate-Resilience---Miami-Dade/.venv/bin/python -I scripts/benefit/module_d_fe_tests.py

Same model as module_d_fe.py (D-191): all qualified 2025 to 2026 sales (sample "main"), separately for
single-family and condo, log price on the specification's house variables plus one dummy per area.
Each test replaces the flood rate with another flood measure, and is also run with the flood rate added
back, so both can be read side by side:
1. FEMA zone (maps effective 19 Feb 2027, sale point in the zone polygon): in or out of the 1% zone
   (A, AE, AH, AO, VE); and VE against the other 1% zones (in 1% zone + VE dummy).
2. Insurance cost: average NFIP premium per insured home in the block group, in $100 a year.
   Residential policies (occupancy 1, 2, 3, 11 to 16) that started in 2025; total premium of the
   policies divided by the number of insured units (policyCount). Block groups with fewer than 10
   policies are left out. Only block group totals are made; no single record is kept or written.
3. Flood experience: NFIP claims with loss year 2010 or later, residential occupancy, per 1,000
   occupied homes in the block group (ACS 2020 to 2024 table B25003 total), in units of 10 claims
   per 1,000 homes.
   Tests 2 and 3 are block group values, the same for every sale in a block group, so block group
   dummies would absorb them. They use one dummy per census tract instead (the user's choice,
   14 Nov), so they compare block groups within the same tract; standard errors clustered by tract.
4. Step effect: the flood rate in five groups: none (0) and the quartiles of the positive rates
   within the segment (low, medium, high, very high), each against none.
5. Away from water: the main model on sales not waterfront and more than 500 m from water (FEMA
   water areas: coast, bay, canal, lake).
6. Better floor heights: the main model on block groups whose floor height comes from their own
   elevation certificates (at least 10 insured buildings of that type with both elevations, D-185),
   not from the tract or county.
Tests 1, 4, 5, 6 use block group dummies, standard errors clustered by block group, as the main
fixed-effects result. The main flood-rate model with tract dummies is also reported, to compare with
tests 2 and 3.
Effects are % price change: exp(b) - 1 for a yes/no or group, per unit for the others.
Writes outputs/benefit/module_d/fe_tests.json and fe_tests.csv (one row per test and segment).
"""
import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyogrio
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
from module_d_fit import XV, load  # noqa: E402
from progress import Progress  # noqa: E402

RES_OCC = [1, 2, 3, 11, 12, 13, 14, 15, 16]
ZONE_1PCT = {"A", "AE", "AH", "AO", "VE"}
MIN_POLICIES = 10
FH_TYPE = {"single_family": "single_family", "condo": "multi_family"}
OUT = paths.OUT_BENEFIT / "module_d"
P = None


def premium_by_bg():
    d = ds.dataset(paths.NFIP_POLICIES_PARQUET_FULL)
    f = ((ds.field("propertyState") == "FL") & pc.starts_with(ds.field("censusGeoid"), "12086"))
    t = d.to_table(columns=["censusGeoid", "occupancyType", "policyEffectiveDate", "policyCount",
                            "totalInsurancePremiumOfThePolicy"], filter=f).to_pandas()
    t["year"] = pd.to_datetime(t.policyEffectiveDate, errors="coerce").dt.year
    t["occ"] = pd.to_numeric(t.occupancyType, errors="coerce")
    t = t[(t.year == 2025) & t.occ.isin(RES_OCC)]
    for c in ["policyCount", "totalInsurancePremiumOfThePolicy"]:
        t[c] = pd.to_numeric(t[c], errors="coerce")
    t = t.dropna(subset=["policyCount", "totalInsurancePremiumOfThePolicy"])
    t = t[t.policyCount > 0]
    g = t.groupby("censusGeoid").agg(prem=("totalInsurancePremiumOfThePolicy", "sum"), n=("policyCount", "sum"),
                                     records=("policyCount", "size"))
    g = g[g.records >= MIN_POLICIES]
    info = {"policies_2025_residential": int(len(t)), "block_groups_with_10_or_more": int(len(g))}
    return (g.prem / g.n / 100).rename("PREMIUM"), info


def claims_by_bg():
    c = pd.read_csv(paths.NFIP_CLAIMS_CSV, usecols=["censusGeoid", "yearOfLoss", "occupancyType"],
                    dtype={"censusGeoid": str})
    c = c[(c.yearOfLoss >= 2010) & pd.to_numeric(c.occupancyType, errors="coerce").isin(RES_OCC)]
    c["bg"] = c.censusGeoid.str.replace(r"\.0$", "", regex=True).str.zfill(12)
    n = c.groupby("bg").size()
    a = pd.read_csv(paths.ACS_BG_DIR / "B25003-Tenure" / "ACSDT5Y2024.B25003-Data.csv", skiprows=[1], dtype=str)
    a["bg"] = a.GEO_ID.str[-12:]
    homes = pd.to_numeric(a.set_index("bg").B25003_001E, errors="coerce")
    homes = homes[homes > 0]
    rate = (n.reindex(homes.index, fill_value=0) / homes * 1000 / 10).rename("CLAIMS")
    info = {"claims_2010_on_residential": int(len(c)), "claims_in_a_2024_block_group": int(n[n.index.isin(homes.index)].sum()),
            "block_groups": int(len(homes))}
    return rate, info


def eff(m, name):
    b, se = m.params[name], m.bse[name]
    p = float(m.pvalues[name])
    return {"pct": round(float((np.exp(b) - 1) * 100), 3),
            "ci95": [round(float((np.exp(b - 1.96 * se) - 1) * 100), 3), round(float((np.exp(b + 1.96 * se) - 1) * 100), 3)],
            "p": round(p, 4), "significant": bool(p < 0.05)}


def fit(d, xs, fe, cl):
    X = pd.concat([d[xs].astype(float), pd.get_dummies(d[fe], prefix="fe", drop_first=True, dtype=float)], axis=1)
    X = sm.add_constant(X)
    return sm.OLS(d.log_price.to_numpy(), X).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d[cl])[0]})


def run(seg, bg, zones, prem, claims, fh_bgs):
    s = load(seg)
    d = s[s.sample_name == "main"].copy()
    pts = gpd.GeoDataFrame(geometry=gpd.points_from_xy(d.x, d.y), crs=32617, index=d.index)
    j = gpd.sjoin(pts, bg, predicate="within", how="left")
    d["GEOID_bg"] = j[~j.index.duplicated()].GEOID
    z = gpd.sjoin(pts, zones, predicate="within", how="left")
    d["zone27"] = z[~z.index.duplicated()].FLD_ZONE.fillna("X")
    base = [x for x in XV[seg] if x != "FLOOD"]
    d = d.dropna(subset=base + ["log_price", "flood_rate", "GEOID_bg", "GEOID_tract"])
    d["FLOOD"] = d.flood_rate
    d["IN_1PCT"] = d.zone27.isin(ZONE_1PCT).astype(float)
    d["VE"] = (d.zone27 == "VE").astype(float)
    d["PREMIUM"] = d.GEOID_bg.map(prem)
    d["CLAIMS"] = d.GEOID_bg.map(claims)
    pos = d.flood_rate[d.flood_rate > 0]
    q = pos.quantile([0.25, 0.5, 0.75]).to_list()
    grp = np.select([d.flood_rate <= 0, d.flood_rate <= q[0], d.flood_rate <= q[1], d.flood_rate <= q[2]],
                    ["none", "low", "medium", "high"], "very_high")
    for g in ["low", "medium", "high", "very_high"]:
        d[f"G_{g}"] = (grp == g).astype(float)
    rows, info = [], {"sales": int(len(d)), "zone_counts": d.zone27.value_counts().to_dict(),
                      "flood_rate_group_cuts": [round(v, 3) for v in q]}

    def add(test, var, label, dd, extra, fe, cl, flood_too=False):
        m = fit(dd, base + extra, fe, cl)
        r = {"segment": seg, "test": test, "variable": label, "fixed_effects": fe.replace("GEOID_", ""),
             "sales": int(len(dd)), "with_flood_rate": False, **eff(m, var)}
        rows.append(r)
        if flood_too:
            m2 = fit(dd, base + extra + ["FLOOD"], fe, cl)
            rows.append({**r, "with_flood_rate": True, **eff(m2, var),
                         "flood_rate_alongside": eff(m2, "FLOOD")})

    P.start(f"{seg}: tests")
    add("0 main", "FLOOD", "flood rate (per $100 per $100,000)", d, ["FLOOD"], "GEOID_bg", "GEOID_bg")
    add("0 main, tract dummies", "FLOOD", "flood rate (per $100 per $100,000)", d, ["FLOOD"], "GEOID_tract", "GEOID_tract")
    add("1a FEMA 1% zone", "IN_1PCT", "in 1% zone (2027 maps)", d, ["IN_1PCT"], "GEOID_bg", "GEOID_bg", True)
    if d.VE.sum() >= 30:
        add("1b VE vs other 1% zones", "VE", "VE against A, AE, AH, AO", d, ["IN_1PCT", "VE"], "GEOID_bg", "GEOID_bg", True)
    info["ve_sales"] = int(d.VE.sum())
    dp = d.dropna(subset=["PREMIUM"])
    add("2 insurance cost", "PREMIUM", "average NFIP premium (per $100 a year)", dp, ["PREMIUM"], "GEOID_tract",
        "GEOID_tract", True)
    dc = d.dropna(subset=["CLAIMS"])
    add("3 flood experience", "CLAIMS", "NFIP claims since 2010 (per 10 per 1,000 homes)", dc, ["CLAIMS"],
        "GEOID_tract", "GEOID_tract", True)
    gs = [f"G_{g}" for g in ["low", "medium", "high", "very_high"]]
    m = fit(d, base + gs, "GEOID_bg", "GEOID_bg")
    for g, lab in zip(gs, ["low", "medium", "high", "very high"]):
        rows.append({"segment": seg, "test": "4 step effect", "variable": f"flood rate {lab} vs none",
                     "fixed_effects": "bg", "sales": int(len(d)), "with_flood_rate": False,
                     "group_sales": int(d[g].sum()), **eff(m, g)})
    da = d[(d.waterfront == 0) & (d.dist_water_m > 500)]
    add("5 away from water", "FLOOD", "flood rate, not waterfront and over 500 m from water", da, ["FLOOD"],
        "GEOID_bg", "GEOID_bg")
    df = d[d.GEOID_bg.isin(fh_bgs[FH_TYPE[seg]])]
    add("6 better floor heights", "FLOOD", "flood rate, block groups with own elevation certificates", df, ["FLOOD"],
        "GEOID_bg", "GEOID_bg")
    info["premium_sales"], info["claims_sales"] = int(len(dp)), int(len(dc))
    info["away_sales"], info["floor_height_sales"] = int(len(da)), int(len(df))
    P.end()
    return rows, info


def main():
    global P
    P = Progress("module D fixed-effects tests")
    P.start("inputs: block groups, 2027 zones, premiums, claims, floor heights")
    bg = gpd.read_file(f"zip://{paths.BOUNDARY_DIR / 'tl_2024_12_bg.zip'}")
    bg = bg[bg.COUNTYFP == "086"].to_crs(32617)[["GEOID", "geometry"]]
    zones = pyogrio.read_dataframe(paths.FIRM_2027_EXTRACT / "S_Fld_Haz_Ar.shp", columns=["FLD_ZONE"]).to_crs(32617)
    prem, ip = premium_by_bg()
    claims, ic = claims_by_bg()
    fh = pd.read_csv(OUT / "nfip_floor_height_summary.csv", dtype={"area": str})
    fh = fh[fh.level == "block_group"]
    fh_bgs = {t: set(fh[fh.type == t].area) for t in FH_TYPE.values()}
    P.end()
    R = {"premium": ip, "claims": ic, "floor_height_block_groups": {t: len(v) for t, v in fh_bgs.items()}}
    rows = []
    for seg in ["single_family", "condo"]:
        r, R[seg] = run(seg, bg, zones, prem, claims, fh_bgs)
        rows += r
    R["rows"] = rows
    (OUT / "fe_tests.json").write_text(json.dumps(R, indent=2))
    t = pd.DataFrame(rows)
    t["ci95_low"], t["ci95_high"] = t.ci95.str[0], t.ci95.str[1]
    t.drop(columns=["ci95"]).to_csv(OUT / "fe_tests.csv", index=False)
    print(t[["segment", "test", "with_flood_rate", "sales", "pct", "ci95", "p", "significant"]].to_string(), flush=True)
    P.finish()


if __name__ == "__main__":
    main()
