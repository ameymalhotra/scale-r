"""Part 2: univariate description of every vulnerability indicator and every
outcome variant, at both grains, plus the project-type/scale-tag sparsity
baseline. Description only - no modeling.

Usage: python scripts/part2_univariate.py
Outputs: output/part2_univariate/*.csv
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analysis_variables import (  # noqa: E402
    BG_VULN_VARS, SCALE_COLS_TRACT, TRACT_VULN_VARS, TYPE_COLS_TRACT,
    VOLUME_OUTCOMES_BG, VOLUME_OUTCOMES_TRACT, add_type_scale_measures,
    load_bg, load_tract,
)
from scaler_projects import OUTPUT_DIR, load_typed  # noqa: E402

OUT = OUTPUT_DIR / "part2_univariate"
OUT.mkdir(exist_ok=True)

MISSING_FLAG_PCT = 20.0


def describe_var(s, name, is_rate):
    n = len(s)
    miss = int(s.isna().sum())
    v = s.dropna()
    row = {
        "variable": name, "n": n, "n_missing": miss,
        "pct_missing": round(miss / n * 100, 2) if n else np.nan,
        "n_distinct": int(v.nunique()),
        "min": v.min() if len(v) else np.nan, "max": v.max() if len(v) else np.nan,
        "mean": v.mean() if len(v) else np.nan, "median": v.median() if len(v) else np.nan,
        "sd": v.std() if len(v) else np.nan,
        "skew": v.skew() if len(v) > 2 else np.nan,
    }
    row["flag_high_missing_gt20pct"] = row["pct_missing"] > MISSING_FLAG_PCT
    row["flag_near_constant"] = bool(len(v) and (v.nunique() <= 1 or (v.std() == 0)))
    row["flag_rate_outside_0_1"] = bool(is_rate and len(v) and ((v.min() < -1e-9) or (v.max() > 1 + 1e-9)))
    row["flag_heavily_skewed_abs_gt2"] = bool(pd.notna(row["skew"]) and abs(row["skew"]) > 2)
    return row


def profile_set(df, varnames, rate_flags, label):
    rows = [describe_var(df[v], v, rate_flags.get(v, False)) for v in varnames]
    out = pd.DataFrame(rows)
    path = OUT / f"univariate_{label}.csv"
    out.to_csv(path, index=False)
    return out


def print_flags(out, label):
    print(f"\n--- {label}: flags ---")
    for flag, desc in [("flag_high_missing_gt20pct", ">20% missing"),
                       ("flag_near_constant", "near-constant"),
                       ("flag_rate_outside_0_1", "rate outside [0,1]"),
                       ("flag_heavily_skewed_abs_gt2", "|skew| > 2")]:
        hit = out[out[flag]]["variable"].tolist()
        print(f"  {desc}: {len(hit)} -> {hit}")


def tract_profile():
    print("=" * 78 + "\nTRACT UNIVARIATE PROFILE (698 rows)\n" + "=" * 78)
    df = load_tract()
    rate_flags = {v: True for v in TRACT_VULN_VARS}  # SVI EP_* are 0-100 "rates"; flag differently
    for v in TRACT_VULN_VARS:
        if v.startswith("EP_"):
            rate_flags[v] = "pct0_100"
    rows = []
    for v in TRACT_VULN_VARS:
        s = df[v]
        is_pct = v.startswith("EP_")
        r = describe_var(s, v, is_rate=not is_pct)
        if is_pct:
            v_ = s.dropna()
            r["flag_rate_outside_0_1"] = bool(len(v_) and ((v_.min() < -1e-9) or (v_.max() > 100 + 1e-9)))
            r["note"] = "SVI EP_* is 0-100 percent, not 0-1 fraction"
        rows.append(r)
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "univariate_tract_vulnerability.csv", index=False)
    print_flags(out, "tract vulnerability (SVI EP_* + ACS CRE)")

    df2 = add_type_scale_measures(df, per_capita=True)
    outcome_cols = (VOLUME_OUTCOMES_TRACT + ["investment_any", "population",
                    "project_count", "project_count_single_unit", "flag_large_project"]
                    + TYPE_COLS_TRACT + SCALE_COLS_TRACT)
    rate_like = {"investment_any_excl_county": True, "investment_any_single_unit": True,
                 "investment_any": True, "flag_large_project": True}
    out2 = pd.DataFrame([describe_var(df2[c], c, rate_like.get(c, False)) for c in outcome_cols])
    out2.to_csv(OUT / "univariate_tract_outcomes.csv", index=False)
    print_flags(out2, "tract outcomes")
    print("\ninvestment_any (as built) distinct values:",
          df["investment_any"].unique().tolist(), "-> zero variance, confirmed unusable")
    return df, df2


def bg_profile():
    print("\n" + "=" * 78 + "\nBLOCK GROUP UNIVARIATE PROFILE (1,843 rows)\n" + "=" * 78)
    df = load_bg()
    rows = []
    for v in BG_VULN_VARS:
        is_frac = not (v in ["PM25", "OZONE", "DSLPM", "RSEI_AIR", "PTRAF", "NO2"]
                       or "median_" in v or v == "income_disparity")
        rows.append(describe_var(df[v], v, is_rate=is_frac))
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "univariate_bg_vulnerability.csv", index=False)
    print_flags(out, "block group vulnerability (EJScreen + ADI)")

    df2 = add_type_scale_measures(df, per_capita=False)
    outcome_cols = (VOLUME_OUTCOMES_BG + ["investment_any", "investment_total",
                    "investment_per_capita", "investment_per_area", "population",
                    "project_count", "project_count_single_unit", "flag_large_project"]
                    + TYPE_COLS_TRACT + SCALE_COLS_TRACT)
    out2 = pd.DataFrame([describe_var(df2[c], c, False) for c in outcome_cols])
    out2.to_csv(OUT / "univariate_bg_outcomes.csv", index=False)
    print_flags(out2, "block group outcomes")
    pc = df["investment_per_capita"].dropna()
    print(f"\ninvestment_per_capita (descriptive ONLY, per Part 4d): "
          f"n={len(pc)}, min={pc.min():.2f}, max={pc.max():,.0f}, "
          f"median={pc.median():.2f}, p99={pc.quantile(.99):,.0f}")
    return df, df2


def sparsity_baseline():
    print("\n" + "=" * 78 + "\nPROJECT TYPE / SCALE-TAG SPARSITY BASELINE\n" + "=" * 78)
    proj = load_typed()
    proj = proj[proj["Project_Status"].isin(["Completed", "Funded", "Ongoing"])]
    print(f"filtered projects: {len(proj)}")

    keys_t = pd.read_csv(OUTPUT_DIR / "project_join_keys.csv", dtype=str)
    led_t = pd.read_csv(OUTPUT_DIR / "allocation_audit_tract.csv", dtype={"GEOID": str})
    led_b = pd.read_csv(OUTPUT_DIR / "allocation_audit_bg.csv", dtype={"GEOID": str})

    rows = []
    for grain, led in [("tract", led_t), ("bg", led_b)]:
        pos = led[led["amount"] > 0]
        by_type = proj.set_index("Project_ID")["Infrastructure_Type"]
        pos = pos.assign(type=pos["Project_ID"].map(by_type))
        for t in ["Blue", "Gray", "Green", "Hybrid"]:
            sub = pos[pos["type"] == t]
            n_proj = proj[proj["Infrastructure_Type"] == t]["Project_ID"].nunique()
            n_units = sub["GEOID"].nunique()
            n_units_organic = sub.loc[sub["path"] == "single-unit", "GEOID"].nunique()
            dollars = sub["amount"].sum()
            rows.append({"grain": grain, "dimension": "type", "category": t,
                        "n_projects": n_proj, "n_receiving_units": n_units,
                        "n_receiving_units_single_unit_only": n_units_organic,
                        "dollars": dollars,
                        "flag_sparse_lt20units": n_units_organic < 20})
        for sc in ["Parcel", "Neighborhood", "Corridor", "Municipality", "County"]:
            sub = pos[pos["scale"] == sc]
            n_proj = proj[proj["scale"] == sc]["Project_ID"].nunique()
            n_units = sub["GEOID"].nunique()
            n_units_organic = sub.loc[sub["path"] == "single-unit", "GEOID"].nunique()
            dollars = sub["amount"].sum()
            # Municipality/County ARE the distributed paths by definition, so
            # "single-unit-sited" is structurally 0 for them - not a sparsity
            # finding. Sparsity for those two is judged on n_projects instead.
            sparse_metric = n_units_organic if sc in ("Parcel", "Neighborhood", "Corridor") else n_proj
            rows.append({"grain": grain, "dimension": "scale", "category": sc,
                        "n_projects": n_proj, "n_receiving_units": n_units,
                        "n_receiving_units_single_unit_only": n_units_organic,
                        "dollars": dollars,
                        "flag_sparse_lt20units": sparse_metric < 20})
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "sparsity_baseline.csv", index=False)
    print(out.to_string(index=False, float_format=lambda v: f"{v:,.0f}"))
    print("\nNOTE: 'n_receiving_units' counts the county allocation path, which")
    print("reaches nearly every unit regardless of project type - it overstates")
    print("organic footprint. 'n_receiving_units_single_unit_only' (a project")
    print("physically sited there) is the sparsity number that matters for Part 4e.")
    sparse = out[out["flag_sparse_lt20units"]]
    print(f"\ncategories with <20 SINGLE-UNIT-SITED receiving units "
          f"(unstable for correlation): {len(sparse)}")
    for _, r in sparse.iterrows():
        print(f"  {r['grain']:5s} {r['dimension']:6s} {r['category']:14s} "
              f"{r['n_receiving_units_single_unit_only']} units (single-unit only)")
    return out


def main():
    tract_profile()
    bg_profile()
    sparsity_baseline()


if __name__ == "__main__":
    main()
