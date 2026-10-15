"""Part 1: build the tract- and block-group-level analysis tables by joining
the investment tables to the vulnerability/deprivation/exposure indicators.

tract_analysis.csv       = tract_investment.csv (9 zero-pop tracts excluded)
                            + SVI EP_* (24) + ACS CRE components (10)
blockgroup_analysis.csv  = blockgroup_investment.csv (all 1,843 rows, none
                            excluded - the exclusion decision was tract-only)
                            + EJScreen indicators (22) + ADI components (13)
                            + no_vehicle, no_broadband (added in the Part 6
                            follow-up: B25044/B28002 downloaded at BG grain
                            after RESULTS_FOR_REVIEW.md Sec 4e found EJScreen
                            carries neither)

Also adds the two investment_any replacements decided for this build:
  investment_any_excl_county   - 1 if any NON-county dollar reached the unit
  investment_any_single_unit   - 1 if a project was physically sited here
    (built from output/allocation_audit_{tract,bg}.csv, the ledger from the
    investment-table build - reused, not recomputed from scratch)

This script does not fit, model, or transform anything beyond the join and
the two derived binaries. GEOID stays string throughout.
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scaler_projects import BASE, OUTPUT_DIR  # noqa: E402
from vulnerability_loaders import (  # noqa: E402
    ADI_VARS, CRE_VARS, EJ_ENV, EJ_HEALTH, EJ_SOCIO, NEW_BG_VARS,
    load_acs_cre_tract, load_adi_bg, load_ejscreen_bg, load_new_bg_vars,
    load_svi_tract,
)

ZERO_POP_TRACTS = [  # from zero_population_investigation.md - excluded per
    "12086981000", "12086980400", "12086980600", "12086980800",  # decision, all population == 0
    "12086980100", "12086980200", "12086980900", "12086981200", "12086990000",
]


def add_allocation_binaries(table, grain):
    """investment_any_excl_county and investment_any_single_unit, built from
    the per-project allocation ledger (reused from the investment-table
    build, not recomputed)."""
    led = pd.read_csv(OUTPUT_DIR / f"allocation_audit_{grain}.csv",
                      dtype={"GEOID": str})
    pos = led[led["amount"] > 0]
    non_county = set(pos.loc[pos["scale"] != "County", "GEOID"])
    single = set(pos.loc[pos["path"] == "single-unit", "GEOID"])
    table["investment_any_excl_county"] = table["GEOID"].isin(non_county).astype(int)
    table["investment_any_single_unit"] = table["GEOID"].isin(single).astype(int)
    return table


def build_tract():
    inv = pd.read_csv(BASE / "tract_investment.csv", dtype={"GEOID": str})
    n_before = len(inv)
    inv = add_allocation_binaries(inv, "tract")

    excluded = inv[inv["GEOID"].isin(ZERO_POP_TRACTS)]
    assert (excluded["population"] == 0).all(), "exclusion list doesn't match population==0 rows"
    inv = inv[~inv["GEOID"].isin(ZERO_POP_TRACTS)].copy()

    svi = load_svi_tract()
    cre = load_acs_cre_tract()
    out = inv.merge(svi, on="GEOID", how="left").merge(
        cre[CRE_VARS + [f"{v}_num" for v in CRE_VARS] + [f"{v}_den" for v in CRE_VARS]],
        on="GEOID", how="left")

    print(f"TRACT: {n_before} investment rows -> excluded {len(excluded)} "
          f"zero-population tracts -> {len(out)} analysis rows")
    assert len(out) == 698, f"expected 698 tract rows, got {len(out)}"
    n_svi_missing = out[[c for c in svi.columns]].isna().all(axis=1).sum()
    n_cre_missing = out[CRE_VARS].isna().all(axis=1).sum()
    print(f"  units with ALL SVI EP_* missing after join: {n_svi_missing}")
    print(f"  units with ALL ACS CRE missing after join : {n_cre_missing}")
    assert n_svi_missing == 0 and n_cre_missing == 0, "join dropped indicator coverage unexpectedly"
    return out


def build_bg():
    inv = pd.read_csv(BASE / "blockgroup_investment.csv", dtype={"GEOID": str})
    n_before = len(inv)
    inv = add_allocation_binaries(inv, "bg")

    ej = load_ejscreen_bg()
    adi = load_adi_bg()
    new_vars = load_new_bg_vars()
    ej_cols = EJ_ENV + EJ_SOCIO + EJ_HEALTH + ["ACSTOTPOP"]
    adi_cols = ADI_VARS + [c for c in adi.columns if c not in ADI_VARS]
    new_cols = NEW_BG_VARS + [c for c in new_vars.columns if c not in NEW_BG_VARS]
    out = inv.merge(ej[ej_cols], on="GEOID", how="left").merge(
        adi[adi_cols], on="GEOID", how="left").merge(
        new_vars[new_cols], on="GEOID", how="left")

    print(f"BLOCK GROUP: {n_before} investment rows -> {len(out)} analysis rows "
          f"(no exclusion at this grain)")
    assert len(out) == 1843, f"expected 1843 bg rows, got {len(out)}"
    for v in NEW_BG_VARS:
        n_miss = out[v].isna().sum()
        print(f"  {v}: {n_miss} missing of 1843 ({n_miss/1843*100:.1f}%)")
    n_ej_missing = out[EJ_ENV].isna().all(axis=1).sum()
    print(f"  units with ALL EJScreen env indicators missing: {n_ej_missing}")
    return out


def write_dictionary():
    rows = []
    svi_desc = {
        "EP_POV150": "% below 150% poverty", "EP_UNEMP": "% unemployed",
        "EP_HBURD": "% housing cost burdened", "EP_NOHSDP": "% no HS diploma",
        "EP_UNINSUR": "% uninsured", "EP_AGE65": "% age 65+",
        "EP_AGE17": "% age 17-", "EP_DISABL": "% disability",
        "EP_SNGPNT": "% single parent HH", "EP_LIMENG": "% limited English HH",
        "EP_MINRTY": "% minority", "EP_MUNIT": "% multi-unit structures",
        "EP_MOBILE": "% mobile homes", "EP_CROWD": "% crowded housing",
        "EP_NOVEH": "% no vehicle", "EP_GROUPQ": "% group quarters",
        "EP_NOINT": "% no internet", "EP_AFAM": "% Black", "EP_HISP": "% Hispanic",
        "EP_ASIAN": "% Asian", "EP_AIAN": "% American Indian/Alaska Native",
        "EP_NHPI": "% Native Hawaiian/Pacific Islander",
        "EP_TWOMORE": "% two or more races", "EP_OTHERRACE": "% other race",
    }
    for code, desc in svi_desc.items():
        rows.append({"grain": "tract", "source": "SVI 2022 (CDC/ATSDR, Florida)",
                     "variable": code, "description": desc,
                     "unit": "percent, 0-100", "type": "individual indicator"})
    cre_desc = {
        "age65plus": "% population 65+ (B01001)",
        "poverty_under125": "% below 125% poverty (C17002)",
        "uninsured": "% uninsured (B27001)",
        "disability": "% with a disability (B18101)",
        "no_vehicle": "% households, no vehicle (B25044)",
        "crowding_over100": "% households, >1 occupant/room (B25014)",
        "limited_english_hh": "% limited-English-speaking households (C16002)",
        "no_broadband": "% households without broadband (B28002), PROXY",
        "no_fulltime_worker_hh": "% households with no workers (B08202), PROXY (loose)",
        "no_diploma_pop25": "% pop 25+ without HS diploma (B15003), PROXY (person-level)",
    }
    for code, desc in cre_desc.items():
        rows.append({"grain": "tract", "source": "ACS 2024 5yr CRE component",
                     "variable": code, "description": desc,
                     "unit": "fraction, 0-1", "type": "rate"})
    ej_desc = {
        "PM25": "Particulate matter 2.5", "OZONE": "Ozone", "DSLPM": "Diesel PM",
        "RSEI_AIR": "Toxic releases to air", "PTRAF": "Traffic proximity",
        "PRE1960PCT": "% pre-1960 housing (lead paint proxy)",
        "PNPL": "Superfund proximity", "PRMP": "RMP facility proximity",
        "PTSDF": "Hazardous waste proximity", "UST": "Underground storage tanks",
        "PWDIS": "Wastewater discharge", "NO2": "Nitrogen dioxide",
        "DWATER": "Drinking water non-compliance",
    }
    for code, desc in ej_desc.items():
        rows.append({"grain": "block group", "source": "EJScreen 2024 (v2.3 reconstruction)",
                     "variable": code, "description": desc,
                     "unit": "raw exposure units (see EJScreen tech doc)",
                     "type": "environmental indicator"})
    ej_socio_desc = {
        "PEOPCOLORPCT": "% people of color", "LOWINCPCT": "% low income",
        "UNEMPPCT": "% unemployed", "LINGISOPCT": "% limited English speaking HH",
        "LESSHSPCT": "% less than HS education", "UNDER5PCT": "% under age 5",
        "OVER64PCT": "% over age 64",
    }
    for code, desc in ej_socio_desc.items():
        rows.append({"grain": "block group", "source": "EJScreen 2024 (v2.3 reconstruction)",
                     "variable": code, "description": desc,
                     "unit": "fraction, 0-1 (despite PCT suffix)",
                     "type": "socioeconomic indicator (7 of 7)"})
    ej_health_desc = {"DISABILITYPCT": "% persons with disabilities",
                      "LIFEEXPPCT": "% low life expectancy"}
    for code, desc in ej_health_desc.items():
        rows.append({"grain": "block group", "source": "EJScreen 2024 (v2.3 reconstruction)",
                     "variable": code, "description": desc,
                     "unit": "fraction, 0-1",
                     "type": "health indicator (2 of 5 expected - see build notes)"})
    adi_desc = {
        "median_family_income": "Median family income (B19113)",
        "income_disparity": "log(low-income HH / high-income HH) (B19001, derived)",
        "poverty_pct_families": "% families below poverty (B17010)",
        "poverty_under150": "% below 150% poverty (C17002)",
        "no_diploma_under9yrs": "% pop 25+ with <9 years education (B15003)",
        "median_home_value": "Median home value (B25077)",
        "median_gross_rent": "Median gross rent (B25064)",
        "median_monthly_mortgage": "Median monthly mortgage, with-mortgage units (B25088)",
        "pct_owner_occupied": "% owner-occupied (B25003)",
        "pct_no_plumbing": "% lacking complete plumbing (B25049)",
        "pct_crowding_over100": "% households, >1 occupant/room (B25014)",
        "pct_single_parent_children": "% single-parent HH with children (B11003)",
        "pct_no_kitchen": "% lacking complete kitchen (B25053)",
    }
    for code, desc in adi_desc.items():
        unit = ("dollars" if "median" in code and code != "median" else
                "log ratio, unbounded" if code == "income_disparity" else
                "fraction, 0-1")
        rows.append({"grain": "block group", "source": "ADI components (ACS 2024 5yr)",
                     "variable": code, "description": desc,
                     "unit": unit, "type": "ADI component (13 of 13)"})
    dic = pd.DataFrame(rows)
    dic.to_csv(OUTPUT_DIR / "variable_dictionary.csv", index=False)
    print(f"wrote {OUTPUT_DIR / 'variable_dictionary.csv'} ({len(dic)} rows)")


def main():
    tract = build_tract()
    tract.to_csv(BASE / "tract_analysis.csv", index=False)
    print(f"wrote tract_analysis.csv ({len(tract)} rows, {len(tract.columns)} cols)")

    bg = build_bg()
    bg.to_csv(BASE / "blockgroup_analysis.csv", index=False)
    print(f"wrote blockgroup_analysis.csv ({len(bg)} rows, {len(bg.columns)} cols)")

    write_dictionary()


if __name__ == "__main__":
    main()
