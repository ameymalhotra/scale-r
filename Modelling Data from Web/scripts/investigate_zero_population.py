"""Investigation: zero- and low-population units in the investment tables.

Read-only. It does not modify tract_investment.csv or blockgroup_investment.csv,
does not drop or filter any unit, and never substitutes a placeholder
population. Units whose identity cannot be established from the data are
labelled "unidentified" rather than inferred.

Identification evidence, in order of preference:
  1. TIGER area landmarks (AREALM) intersecting the unit
  2. TIGER point landmarks (POINTLM) inside the unit
  3. The census place (incorporated OR CDP) containing the unit centroid
  4. The names/descriptions of the projects allocated to the unit
All evidence is printed, so a label can always be checked against its source.

Usage: python scripts/investigate_zero_population.py > output/zero_population_report.txt
"""
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from allocation import PROJ_CRS, load_units  # noqa: E402
from scaler_projects import BASE, BOUNDARY_DIR, OUTPUT_DIR, load_typed  # noqa: E402

GRAINS = {"tract": ("tract_investment.csv", 707),
          "bg": ("blockgroup_investment.csv", 1843)}
FLOORS = [0, 50, 100, 250, 500]
BOTTOM_N = 30

MTFCC = {
    "C3081": "locality", "K1231": "hospital", "K1235": "juvenile institution",
    "K1236": "local jail", "K1237": "prison/correctional",
    "K2180": "park", "K2181": "National Park Service land",
    "K2182": "national forest/federal land", "K2184": "military",
    "K2190": "conservation area", "K2451": "airport/airfield",
    "K2457": "airport (statistical)", "K2540": "university/college",
    "K2543": "museum", "K2561": "golf course", "K2582": "cemetery",
    "K2586": "zoo", "K3544": "place of worship",
}


def sec(t):
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)


def mt(code):
    return MTFCC.get(code, code)


# ---------------------------------------------------------------- loading

def load_table(grain):
    fname, n = GRAINS[grain]
    t = pd.read_csv(BASE / fname, dtype={"GEOID": str})
    assert len(t) == n, f"{grain}: expected {n} rows, got {len(t)}"
    return t


def load_ledger(grain):
    return pd.read_csv(OUTPUT_DIR / f"allocation_audit_{grain}.csv",
                       dtype={"GEOID": str})


def load_landmarks():
    al = gpd.read_file(f"zip://{BOUNDARY_DIR / 'tl_2024_12_arealm.zip'}")
    pl = gpd.read_file(f"zip://{BOUNDARY_DIR / 'tl_2024_12_pointlm.zip'}")
    pl = pl[pl["MTFCC"] != "C3061"]          # cul-de-sacs carry no information
    return al.to_crs(PROJ_CRS), pl.to_crs(PROJ_CRS)


def load_places_all():
    """Incorporated places AND CDPs - here they are descriptive labels, not
    jurisdictions, so CDP names are useful ('Fisher Island', 'Homestead Base')."""
    pl = gpd.read_file(f"zip://{BOUNDARY_DIR / 'tl_2024_12_place.zip'}")
    tr = load_units("tract")
    return pl[pl.intersects(tr.union_all())][["NAME", "CLASSFP", "geometry"]].to_crs(PROJ_CRS)


def unit_geoms(grain):
    g = load_units(grain).to_crs(PROJ_CRS)
    return g.set_index("GEOID")


# ---------------------------------------------------------- identification

def describe_units(geoids, grain, led, projects):
    """Evidence bundle per unit. No inference beyond what the sources say."""
    geoms = unit_geoms(grain)
    al, pl = load_landmarks()
    places = load_places_all()
    names = projects.set_index("Project_ID")["Project_Name"]
    rows = []
    for g in geoids:
        if g not in geoms.index:
            rows.append({"GEOID": g, "area_landmarks": "", "point_landmarks": "",
                         "place": "", "top_projects": "", "label": "unidentified"})
            continue
        geom = geoms.loc[g, "geometry"]
        a = al[al.intersects(geom)]
        p = pl[pl.within(geom)]
        pc = places[places.contains(geom.centroid)]
        contrib = led[(led["GEOID"] == g) & (led["amount"] > 0)]
        contrib = contrib[contrib["path"] == "single-unit"].nlargest(3, "amount")
        a_txt = "; ".join(f"{n} ({mt(m)})" for n, m in
                          zip(a["FULLNAME"].fillna("?"), a["MTFCC"]))
        p_txt = "; ".join(f"{n} ({mt(m)})" for n, m in
                          zip(p["FULLNAME"].fillna("?"), p["MTFCC"]))
        pc_txt = "; ".join(f"{n} [{'incorporated' if c.startswith('C') else 'CDP'}]"
                           for n, c in zip(pc["NAME"], pc["CLASSFP"]))
        pr_txt = "; ".join(str(names.get(i, i))[:46] for i in contrib["Project_ID"])
        def first_named(frame):
            """First landmark that actually carries a name; unnamed TIGER
            features identify nothing and must not become a label."""
            named = frame[frame["FULLNAME"].notna()
                          & (frame["FULLNAME"].astype(str).str.strip() != "")]
            return None if named.empty else str(named.iloc[0]["FULLNAME"])

        label = (first_named(a) or first_named(p)
                 or (str(pc.iloc[0]["NAME"]) if len(pc) else None)
                 or "unidentified")
        rows.append({"GEOID": g, "area_landmarks": a_txt, "point_landmarks": p_txt,
                     "place": pc_txt, "top_projects": pr_txt, "label": label})
    return pd.DataFrame(rows).set_index("GEOID")


# -------------------------------------------------------------- step 1

def step1(grain, table, led, projects):
    sec(f"STEP 1 - ZERO-POPULATION UNITS: {grain.upper()}")
    geoms = load_units(grain).set_index("GEOID")
    zp = table[table["population"] == 0].copy()
    zp["ALAND"] = zp["GEOID"].map(geoms["ALAND"])
    zp["AWATER"] = zp["GEOID"].map(geoms["AWATER"])
    print(f"{len(zp)} units with population == 0 "
          f"({len(zp[zp.investment_total > 0])} of them carry investment)\n")
    ev = describe_units(zp["GEOID"].tolist(), grain, led, projects)
    show = zp[["GEOID", "ALAND", "AWATER", "investment_total", "project_count",
               "project_count_single_unit", "flag_large_project"]].copy()
    show["ALAND_km2"] = show["ALAND"] / 1e6
    show["AWATER_km2"] = show["AWATER"] / 1e6
    print(show[["GEOID", "ALAND", "AWATER", "ALAND_km2", "AWATER_km2",
                "investment_total", "project_count", "project_count_single_unit"]]
          .sort_values("investment_total", ascending=False)
          .to_string(index=False, float_format=lambda v: f"{v:,.2f}"))

    names = projects.set_index("Project_ID")
    for g in zp.sort_values("investment_total", ascending=False)["GEOID"]:
        e = ev.loc[g]
        print(f"\n--- {g} ---")
        print(f"  TIGER area landmarks : {e['area_landmarks'] or '(none)'}")
        print(f"  TIGER point landmarks: {e['point_landmarks'] or '(none)'}")
        print(f"  census place at centroid: {e['place'] or '(none - unincorporated, no CDP)'}")
        sub = led[(led["GEOID"] == g) & (led["amount"] > 0)].sort_values(
            "amount", ascending=False)
        if sub.empty:
            print("  contributing projects: NONE (zero investment)")
            continue
        print(f"  contributing projects ({len(sub)}):")
        for _, r in sub.iterrows():
            p = names.loc[r["Project_ID"]]
            print(f"    ${r['amount']:>14,.0f}  {r['path']:<26} "
                  f"{p['Infrastructure_Type']:<7} {p['Project_Status']:<10} "
                  f"{r['scale']:<13} {p['Project_Name'][:58]}")
    return ev


# -------------------------------------------------------------- step 2

def step2(grain, table, led, projects):
    sec(f"STEP 2 - BOTTOM {BOTTOM_N} UNITS BY POPULATION: {grain.upper()}")
    bot = table.nsmallest(BOTTOM_N, "population").copy()
    ev = describe_units(bot["GEOID"].tolist(), grain, led, projects)
    bot = bot.join(ev[["label", "area_landmarks", "point_landmarks", "place",
                       "top_projects"]], on="GEOID")
    print(f"{'GEOID':<13} {'pop':>6} {'investment_total':>18} "
          f"{'per_capita':>14}  what the place appears to be")
    for _, r in bot.sort_values("population").iterrows():
        pc = ("undefined" if r["population"] == 0
              else f"{r['investment_per_capita']:,.0f}")
        ident = r["label"]
        detail = r["point_landmarks"] or r["place"] or r["top_projects"]
        print(f"{r['GEOID']:<13} {int(r['population']):>6,} "
              f"{r['investment_total']:>18,.0f} {pc:>14}  {ident}")
        if detail:
            print(f"{'':>54}  evidence: {detail[:110]}")
    print(f"\npopulation percentiles ({grain}):")
    print(table["population"].describe(
        percentiles=[.005, .01, .02, .05, .1, .25, .5]).to_string(
        float_format=lambda v: f"{v:,.1f}"))
    for f in FLOORS:
        n = int((table["population"] < f).sum()) if f else int((table["population"] == 0).sum())
        print(f"  units with population {'== 0' if f == 0 else f'< {f}':<7}: {n}")
    return bot


# -------------------------------------------------------------- step 3

def step3(grain, table):
    sec(f"STEP 3 - CANDIDATE POPULATION FLOORS: {grain.upper()}")
    total = table["investment_total"].sum()
    rows = []
    base_pc = table["investment_per_capita"].dropna()
    rows.append({
        "floor": "none (keep all)", "units_excluded": 0, "pct_units": "0.0%",
        "dollars_excluded": 0.0, "pct_dollars": "0.00%",
        "remaining_units": len(table),
        "max_per_capita": base_pc.max(), "p99_per_capita": base_pc.quantile(.99),
        "p95_per_capita": base_pc.quantile(.95),
    })
    for f in FLOORS:
        drop = table["population"] == 0 if f == 0 else table["population"] < f
        keep = table[~drop]
        pc = keep["investment_per_capita"].dropna()
        rows.append({
            "floor": "pop == 0" if f == 0 else f"pop < {f}",
            "units_excluded": int(drop.sum()),
            "pct_units": f"{drop.sum()/len(table)*100:.1f}%",
            "dollars_excluded": table.loc[drop, "investment_total"].sum(),
            "pct_dollars": f"{table.loc[drop, 'investment_total'].sum()/total*100:.2f}%",
            "remaining_units": len(keep),
            "max_per_capita": pc.max(), "p99_per_capita": pc.quantile(.99),
            "p95_per_capita": pc.quantile(.95),
        })
    d = pd.DataFrame(rows)
    for c in ["dollars_excluded", "max_per_capita", "p99_per_capita", "p95_per_capita"]:
        d[c] = d[c].map(lambda v: f"{v:,.0f}")
    print(d.to_string(index=False))
    print(f"\ntotal allocated ({grain}): ${total:,.0f}")
    print("note: 'max_per_capita' is computed only over units that remain, and")
    print("units with population 0 are already absent from it (undefined).")


# -------------------------------------------------------------- step 4

def _num(s):
    return pd.to_numeric(s, errors="coerce")


def vulnerability_tract(geoids):
    """SVI EP_* indicators (-999 = missing) and the 10 ACS CRE denominators."""
    svi = pd.read_csv(BASE / "tract-level/SVI Data/FLORIDA.csv",
                      dtype=str, low_memory=False)
    svi = svi[svi["FIPS"].str.startswith("12086")].set_index("FIPS")
    ep = [c for c in svi.columns if c.startswith("EP_")]
    v = svi[ep].apply(_num)
    v = v.mask(v == -999)
    out = pd.DataFrame(index=pd.Index(geoids, name="GEOID"))
    out["svi_in_file"] = [g in svi.index for g in geoids]
    out["svi_ep_na"] = [int(v.loc[g].isna().sum()) if g in v.index else np.nan
                        for g in geoids]
    out["svi_ep_total"] = len(ep)

    acs_dir = BASE / "tract-level/ACS Data"
    tables = {p.name.split("-")[0]: p for p in sorted(acs_dir.iterdir()) if p.is_dir()}
    zero_den, na_den = [], []
    for g in geoids:
        z = n = 0
        for code, path in tables.items():
            f = next(path.glob("*Data.csv"))
            d = pd.read_csv(f, dtype=str, skiprows=[1])
            d["GEOID"] = d["GEO_ID"].str.replace("1400000US", "", regex=False)
            d = d.set_index("GEOID")
            col = f"{code}_001E"
            if g not in d.index or col not in d.columns:
                n += 1
                continue
            val = _num(pd.Series([d.loc[g, col]])).iloc[0]
            if pd.isna(val):
                n += 1
            elif val == 0:
                z += 1
        zero_den.append(z)
        na_den.append(n)
    out["acs_tables"] = len(tables)
    out["acs_zero_denominator"] = zero_den
    out["acs_na_denominator"] = na_den
    return out


def vulnerability_bg(geoids):
    """EJScreen 13 environmental indicators + ADI component denominators."""
    ej_path = (BASE / "block-group-level/EJScreen-Data"
               / "EJSCREEN_2024_BG_with_AS_CNMI_GU_VI.csv")
    ej = pd.read_csv(ej_path, dtype=str, low_memory=False)
    ej["GEOID"] = ej["ID"].astype(str).str.zfill(12)
    ej = ej[ej["GEOID"].str.startswith("12086")].set_index("GEOID")
    env = ["PM25", "OZONE", "DSLPM", "RSEI_AIR", "PTRAF", "PRE1960PCT", "PNPL",
           "PRMP", "PTSDF", "UST", "PWDIS", "NO2", "DWATER"]
    env = [c for c in env if c in ej.columns]
    e = ej[env].apply(_num)
    out = pd.DataFrame(index=pd.Index(geoids, name="GEOID"))
    out["ej_in_file"] = [g in ej.index for g in geoids]
    out["ej_env_na"] = [int(e.loc[g].isna().sum()) if g in e.index else np.nan
                        for g in geoids]
    out["ej_env_total"] = len(env)
    out["ej_acstotpop"] = [_num(pd.Series([ej.loc[g, "ACSTOTPOP"]])).iloc[0]
                           if g in ej.index else np.nan for g in geoids]

    adi_dir = BASE / "block-group-level/ADI Data"
    tables = {p.name.split("-")[0].strip(): p for p in sorted(adi_dir.iterdir())
              if p.is_dir()}
    zero_den, na_den, supp = [], [], []
    for g in geoids:
        z = n = s = 0
        for code, path in tables.items():
            f = next(path.glob("*Data.csv"))
            d = pd.read_csv(f, dtype=str, skiprows=[1])
            d["GEOID"] = d["GEO_ID"].str.replace("1500000US", "", regex=False)
            d = d.set_index("GEOID")
            col = f"{code}_001E"
            if g not in d.index or col not in d.columns:
                n += 1
                continue
            raw = str(d.loc[g, col])
            if raw.strip() in ("-", "**", "N", "(X)", "null", "nan"):
                s += 1
                continue
            val = _num(pd.Series([raw])).iloc[0]
            if pd.isna(val) or val <= -666666:
                n += 1
            elif val == 0:
                z += 1
        zero_den.append(z)
        na_den.append(n)
        supp.append(s)
    out["adi_tables"] = len(tables)
    out["adi_zero_denominator"] = zero_den
    out["adi_na_denominator"] = na_den
    out["adi_suppressed"] = supp
    return out


def step4(grain, table, zp_ids, bottom_ids):
    sec(f"STEP 4 - VULNERABILITY-SIDE USABILITY: {grain.upper()}")
    ids = list(dict.fromkeys(list(zp_ids) + list(bottom_ids)))
    v = (vulnerability_tract(ids) if grain == "tract" else vulnerability_bg(ids))
    v = v.join(table.set_index("GEOID")[["population", "investment_total"]])
    v["zero_pop"] = v["population"] == 0
    print(f"units examined: {len(v)} "
          f"({int(v['zero_pop'].sum())} zero-population, rest = bottom-{BOTTOM_N})\n")
    print(v.sort_values("population").to_string(float_format=lambda x: f"{x:,.0f}"))
    print("\nsummary:")
    if grain == "tract":
        zp = v[v["zero_pop"]]
        print(f"  zero-pop tracts missing from the SVI file entirely : "
              f"{int((~zp['svi_in_file']).sum())} of {len(zp)}")
        print(f"  zero-pop tracts with ALL 24 SVI EP_* indicators NA : "
              f"{int((zp['svi_ep_na'] == zp['svi_ep_total']).sum())} of {len(zp)}")
        print(f"  zero-pop tracts with >=1 ACS table having a zero denominator: "
              f"{int((zp['acs_zero_denominator'] > 0).sum())} of {len(zp)}")
        print(f"  mean ACS tables with zero denominator, zero-pop tracts: "
              f"{zp['acs_zero_denominator'].mean():.1f} of {int(zp['acs_tables'].iloc[0])}")
        low = v[(~v["zero_pop"])]
        print(f"  bottom-{BOTTOM_N} non-zero-pop tracts with any SVI EP_* NA: "
              f"{int((low['svi_ep_na'] > 0).sum())} of {len(low)}")
        print(f"  bottom-{BOTTOM_N} non-zero-pop tracts with any zero ACS denominator: "
              f"{int((low['acs_zero_denominator'] > 0).sum())} of {len(low)}")
    else:
        zp = v[v["zero_pop"]]
        print(f"  zero-pop BGs missing from EJScreen entirely : "
              f"{int((~zp['ej_in_file']).sum())} of {len(zp)}")
        print(f"  zero-pop BGs with ALL environmental indicators NA: "
              f"{int((zp['ej_env_na'] == zp['ej_env_total']).sum())} of {len(zp)}")
        print(f"  zero-pop BGs with >=1 ADI table zero denominator: "
              f"{int((zp['adi_zero_denominator'] > 0).sum())} of {len(zp)}")
        print(f"  mean ADI tables with zero denominator, zero-pop BGs: "
              f"{zp['adi_zero_denominator'].mean():.1f} of {int(zp['adi_tables'].iloc[0])}")
        low = v[(~v["zero_pop"])]
        print(f"  bottom-{BOTTOM_N} non-zero-pop BGs with any suppressed ADI value: "
              f"{int((low['adi_suppressed'] > 0).sum())} of {len(low)}")
    return v


def main():
    projects = load_typed()
    for grain in ["tract", "bg"]:
        table = load_table(grain)
        led = load_ledger(grain)
        step1(grain, table, led, projects)
        bot = step2(grain, table, led, projects)
        step3(grain, table)
        zp_ids = table.loc[table["population"] == 0, "GEOID"].tolist()
        step4(grain, table, zp_ids, bot["GEOID"].tolist())


if __name__ == "__main__":
    main()
