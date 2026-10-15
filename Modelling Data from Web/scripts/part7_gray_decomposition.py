"""Part 7: decompose Gray infrastructure and re-run the composition
correlations per sub-category, with the density control, to check whether
the gray/access finding is carried by transit alone (tautological - transit
goes where transit riders are) or holds for non-transit gray on its own.
Also re-runs the block-group environmental-proximity result against
road/non-road gray, for the same reason (traffic proximity vs road
investment has the same tautology risk).

Descriptive/correlational only - no fitting, no prediction.

Usage: python scripts/part7_gray_decomposition.py
Outputs: output/part7_gray/*.csv
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analysis_variables import add_type_scale_measures, load_bg, load_tract  # noqa: E402
from gray_classification import FALSE_POSITIVE_EXAMPLES, add_classifications  # noqa: E402
from part6c_density_control import build_density  # noqa: E402
from part6c_density_control import spearman_partial  # noqa: E402
from scaler_projects import BASE, OUTPUT_DIR, load_typed  # noqa: E402

OUT = OUTPUT_DIR / "part7_gray"
OUT.mkdir(exist_ok=True)
warnings.filterwarnings("ignore", category=RuntimeWarning)

SPARSE_MIN_UNITS = 20
SUBCATS = ["transit", "coastal_seawall", "drainage_stormwater", "road",
          "water_sewer", "power_comm_facility", "other_unclassified"]

TRACT_ACCESS = ["EP_NOVEH", "no_vehicle", "EP_MUNIT", "EP_NOINT", "no_broadband"]
TRACT_MINORITY = ["EP_MINRTY", "EP_HISP", "EP_AFAM"]
BG_ACCESS = ["no_vehicle", "no_broadband"]
BG_MINORITY = ["PEOPCOLORPCT"]
BG_ENV = ["PTRAF", "NO2", "UST", "RSEI_AIR"]


# --------------------------------------------------------------------------
# 2a - profile what's inside gray
# --------------------------------------------------------------------------

def profile_gray():
    print("=" * 78 + "\n2a - GRAY SUB-CATEGORY PROFILE\n" + "=" * 78)
    df = load_typed()
    gray = df[(df["Infrastructure_Type"] == "Gray")
             & (df["Project_Status"].isin(["Completed", "Funded", "Ongoing"]))].copy()
    gray = add_classifications(gray)
    print(f"filtered Gray projects: {len(gray)}, ${gray['cost_num'].sum():,.0f}")

    print("\n--- transit detection: false positives from a loose first-pass "
          "pattern, and why the pattern was tightened ---")
    for pid, (term, why) in FALSE_POSITIVE_EXAMPLES.items():
        row = df[df["Project_ID"] == pid]
        name = row["Project_Name"].iloc[0] if len(row) else "?"
        print(f"  {pid} ('{name}'): loose match on '{term}' - {why}")

    transit_ids = gray.loc[gray["gray_finer_subcat"] == "transit", "Project_ID"].tolist()
    print(f"\ntightened transit pattern matches: {len(transit_ids)} of {len(gray)} "
          f"Gray projects -> {transit_ids}")

    led_t = pd.read_csv(OUTPUT_DIR / "allocation_audit_tract.csv", dtype={"GEOID": str})
    led_b = pd.read_csv(OUTPUT_DIR / "allocation_audit_bg.csv", dtype={"GEOID": str})
    subcat_map = gray.set_index("Project_ID")["gray_finer_subcat"]

    rows = []
    for grain, led in [("tract", led_t), ("bg", led_b)]:
        pos = led[led["amount"] > 0].copy()
        pos["subcat"] = pos["Project_ID"].map(subcat_map)
        pos = pos[pos["subcat"].notna()]  # restrict to Gray-classified rows
        for cat in SUBCATS:
            sub = pos[pos["subcat"] == cat]
            n_proj = gray.loc[gray["gray_finer_subcat"] == cat, "Project_ID"].nunique()
            dollars = gray.loc[gray["gray_finer_subcat"] == cat, "cost_num"].sum()
            n_units = sub["GEOID"].nunique()
            n_units_organic = sub.loc[sub["path"] == "single-unit", "GEOID"].nunique()
            rows.append({"grain": grain, "subcategory": cat, "n_projects": n_proj,
                        "dollars": dollars, "n_receiving_units": n_units,
                        "n_receiving_units_single_unit_only": n_units_organic})
    prof = pd.DataFrame(rows)
    prof["pct_of_gray_dollars"] = prof.groupby("grain")["dollars"].transform(
        lambda s: s / s.sum() * 100)
    prof["flag_sparse_lt20"] = prof["n_receiving_units_single_unit_only"] < SPARSE_MIN_UNITS
    prof.to_csv(OUT / "2a_gray_subcategory_profile.csv", index=False)
    print(f"\n{prof[prof.grain == 'tract'].drop(columns='grain').to_string(index=False, float_format=lambda v: f'{v:,.1f}' if isinstance(v, float) else str(v))}")

    print("\n--- example matches per sub-category (first 3, name only) ---")
    for cat in SUBCATS:
        ex = gray.loc[gray["gray_finer_subcat"] == cat, "Project_Name"].head(3).tolist()
        print(f"  {cat}: {ex}")

    bundling = gray["Project_Name"].fillna("") + " || " + gray["Project_Description"].fillna("")
    from gray_classification import FINER_PATTERNS
    has_drain = bundling.str.contains(FINER_PATTERNS["drainage_stormwater"], regex=True)
    has_road = bundling.str.contains(FINER_PATTERNS["road"], regex=True)
    both = (has_drain & has_road).sum()
    print(f"\nbundling disclosure: {both} of {has_drain.sum()} drainage-pattern "
          f"matches ({both / has_drain.sum() * 100:.0f}%) ALSO match the road "
          f"pattern - filed under drainage by priority order (see "
          f"gray_classification.PRIORITY). The finer 6-way split is "
          f"lower-confidence for this reason; transit vs. non-transit is not "
          f"affected by this bundling issue.")
    return gray, prof


# --------------------------------------------------------------------------
# 2b/3 - per-subcategory share measures and correlations
# --------------------------------------------------------------------------

def build_subcat_shares(df, led, subcat_map, grain_label):
    """{subcat}_share and two aggregates (non_transit, non_road), all as a
    fraction of the unit's total investment - same 'share' definition used
    throughout this project."""
    pos = led[led["amount"] > 0].copy()
    pos["subcat"] = pos["Project_ID"].map(subcat_map)
    pos_gray = pos[pos["subcat"].notna()]
    out = df.copy()
    total = out["investment_total"]
    for cat in SUBCATS:
        amt = pos_gray[pos_gray["subcat"] == cat].groupby("GEOID")["amount"].sum()
        out[f"gray_{cat}_amt"] = out["GEOID"].map(amt).fillna(0.0)
        out[f"gray_{cat}_share"] = out[f"gray_{cat}_amt"] / total.where(total > 0)
    out["gray_non_transit_amt"] = sum(out[f"gray_{c}_amt"] for c in SUBCATS if c != "transit")
    out["gray_non_transit_share"] = out["gray_non_transit_amt"] / total.where(total > 0)
    out["gray_non_road_amt"] = sum(out[f"gray_{c}_amt"] for c in SUBCATS if c != "road")
    out["gray_non_road_share"] = out["gray_non_road_amt"] / total.where(total > 0)
    return out


def sparsity_from_profile(prof, grain):
    p = prof[prof.grain == grain].set_index("subcategory")
    return set(p[p["flag_sparse_lt20"]].index)


def correlate_subcats(df, subcats, vuln_vars, sparse_set, grain, tag):
    rows = []
    for cat in subcats:
        share_col = f"gray_{cat}_share" if not cat.startswith("gray_") else cat
        for v in vuln_vars:
            n, r_xy, r_xz, r_yz, r_partial, tstat, p = spearman_partial(
                df[v], df[share_col], df["pop_density"])
            rows.append({
                "subcategory": cat, "variable": v, "n": n,
                "zero_order_rho": r_xy, "partial_rho": r_partial,
                "abs_change": abs(r_partial - r_xy) if pd.notna(r_partial) else np.nan,
                "pct_change": (abs(r_partial - r_xy) / abs(r_xy) * 100
                              if pd.notna(r_partial) and r_xy else np.nan),
                "p_partial": p, "flag_sparse": cat in sparse_set,
            })
    out = pd.DataFrame(rows)
    out["p_partial_fdr"] = np.nan
    valid = out["p_partial"].notna()
    if valid.sum():
        _, adj, _, _ = multipletests(out.loc[valid, "p_partial"], method="fdr_bh")
        out.loc[valid, "p_partial_fdr"] = adj
    out["sig_after_control"] = out["p_partial_fdr"] < 0.05
    out.to_csv(OUT / f"{tag}_{grain}.csv", index=False)
    return out


def main():
    gray_proj, prof = profile_gray()
    subcat_map = gray_proj.set_index("Project_ID")["gray_finer_subcat"]

    tract = add_type_scale_measures(load_tract(), per_capita=True)
    bg = add_type_scale_measures(load_bg(), per_capita=False)
    tract = build_density(tract, "tract")
    bg = build_density(bg, "bg")

    led_t = pd.read_csv(OUTPUT_DIR / "allocation_audit_tract.csv", dtype={"GEOID": str})
    led_b = pd.read_csv(OUTPUT_DIR / "allocation_audit_bg.csv", dtype={"GEOID": str})
    tract = build_subcat_shares(tract, led_t, subcat_map, "tract")
    bg = build_subcat_shares(bg, led_b, subcat_map, "bg")
    tract.to_csv(OUT / "2b_tract_with_subcat_shares.csv", index=False)
    bg.to_csv(OUT / "2b_bg_with_subcat_shares.csv", index=False)

    sparse_t = sparsity_from_profile(prof, "tract")
    sparse_b = sparsity_from_profile(prof, "bg")
    print(f"\nsparse sub-categories (<{SPARSE_MIN_UNITS} single-unit-sited "
          f"receiving units): tract={sparse_t}, bg={sparse_b}")

    print("\n" + "=" * 78 + "\n2b - PER-SUBCATEGORY CORRELATIONS: TRACT\n" + "=" * 78)
    ct_access = correlate_subcats(tract, SUBCATS, TRACT_ACCESS, sparse_t, "tract",
                                  "2b_subcat_vs_access")
    ct_minority = correlate_subcats(tract, SUBCATS, TRACT_MINORITY, sparse_t, "tract",
                                    "2b_subcat_vs_minority")
    print(ct_access.to_string(index=False, float_format=lambda v: f"{v:.3f}" if isinstance(v, float) else str(v)))
    print()
    print(ct_minority.to_string(index=False, float_format=lambda v: f"{v:.3f}" if isinstance(v, float) else str(v)))

    # non_transit and non_road aggregates, tract
    print("\n--- non_transit / non_road aggregate shares, tract ---")
    agg_rows = []
    for agg in ["gray_non_transit_share", "gray_non_road_share"]:
        for v in TRACT_ACCESS + TRACT_MINORITY:
            n, r_xy, r_xz, r_yz, r_partial, tstat, p = spearman_partial(
                tract[v], tract[agg], tract["pop_density"])
            agg_rows.append({"aggregate": agg, "variable": v, "n": n,
                            "zero_order_rho": r_xy, "partial_rho": r_partial, "p_partial": p})
    agg_t = pd.DataFrame(agg_rows)
    valid = agg_t["p_partial"].notna()
    _, adj, _, _ = multipletests(agg_t.loc[valid, "p_partial"], method="fdr_bh")
    agg_t.loc[valid, "p_partial_fdr"] = adj
    agg_t.to_csv(OUT / "2b_nontransit_nonroad_aggregates_tract.csv", index=False)
    print(agg_t.to_string(index=False, float_format=lambda v: f"{v:.3f}" if isinstance(v, float) else str(v)))

    print("\n" + "=" * 78 + "\n2b - PER-SUBCATEGORY CORRELATIONS: BLOCK GROUP\n" + "=" * 78)
    cb_access = correlate_subcats(bg, SUBCATS, BG_ACCESS, sparse_b, "bg", "2b_subcat_vs_access")
    cb_minority = correlate_subcats(bg, SUBCATS, BG_MINORITY, sparse_b, "bg", "2b_subcat_vs_minority")
    print(cb_access.to_string(index=False, float_format=lambda v: f"{v:.3f}" if isinstance(v, float) else str(v)))
    print()
    print(cb_minority.to_string(index=False, float_format=lambda v: f"{v:.3f}" if isinstance(v, float) else str(v)))

    print("\n" + "=" * 78
          + "\nTASK 3 - BLOCK-GROUP ENVIRONMENTAL PROXIMITY vs GRAY SUB-CATEGORIES\n"
          + "=" * 78)
    ct_env = correlate_subcats(bg, SUBCATS, BG_ENV, sparse_b, "bg", "3_subcat_vs_environmental")
    print(ct_env.to_string(index=False, float_format=lambda v: f"{v:.3f}" if isinstance(v, float) else str(v)))

    print("\n--- non_road aggregate vs environmental proximity, block group ---")
    agg_rows2 = []
    for v in BG_ENV:
        n, r_xy, r_xz, r_yz, r_partial, tstat, p = spearman_partial(
            bg[v], bg["gray_non_road_share"], bg["pop_density"])
        agg_rows2.append({"aggregate": "gray_non_road_share", "variable": v, "n": n,
                         "zero_order_rho": r_xy, "partial_rho": r_partial, "p_partial": p})
    agg_b = pd.DataFrame(agg_rows2)
    valid = agg_b["p_partial"].notna()
    if valid.sum():
        _, adj, _, _ = multipletests(agg_b.loc[valid, "p_partial"], method="fdr_bh")
        agg_b.loc[valid, "p_partial_fdr"] = adj
    agg_b.to_csv(OUT / "3_nonroad_aggregate_vs_environmental_bg.csv", index=False)
    print(agg_b.to_string(index=False, float_format=lambda v: f"{v:.3f}" if isinstance(v, float) else str(v)))


if __name__ == "__main__":
    main()
