"""Part 6, Task 3: the density control (highest priority).

Tests whether the gray-up/green-down composition finding, and the opposite-
signed minority-composition finding, are actually urban-density effects
rather than deprivation/equity effects.

3a. Build pop_density (both grains) and housing_density (BG only - see note
    below on why tract housing_density is "not available").
3b. Spearman PARTIAL correlation of every vulnerability variable against
    type_gray_share and type_green_share, controlling for pop_density.
3c. Density-tercile stratification: recompute the headline zero-order
    correlations within low/medium/high density strata.
3d. The minority-composition variables run through the same 3b/3c machinery
    as everything else - flagged separately in the report, not computed
    differently here.

Partial correlation method: Spearman partial correlation via the standard
rank-based formula
    r_xy.z = (r_xy - r_xz*r_yz) / sqrt((1 - r_xz^2)(1 - r_yz^2))
computed on Spearman correlations (equivalently, Pearson partial correlation
computed on the rank-transformed variables) - the standard nonparametric
partial-correlation approach. Significance of the partial via the standard
t-approximation with df = n-3. All three pairwise correlations (x-y, x-z,
y-z) and the partial's n are computed on the SAME listwise-complete rows for
that specific (variable, type) pair, so partial and zero-order are directly
comparable for that row.

Still descriptive/correlational - no fitting, no prediction.

Usage: python scripts/part6c_density_control.py
Outputs: output/part6_followup/6c_*.csv
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from allocation import load_units  # noqa: E402
from analysis_variables import (  # noqa: E402
    BG_VULN_VARS, TRACT_VULN_VARS, add_type_scale_measures, load_bg, load_tract,
)
from scaler_projects import BASE, OUTPUT_DIR  # noqa: E402
from vulnerability_loaders import EJSCREEN_PATH, MD_PREFIX  # noqa: E402

OUT = OUTPUT_DIR / "part6_followup"
OUT.mkdir(exist_ok=True)
warnings.filterwarnings("ignore", category=RuntimeWarning)

# access/connectivity vs. direct-hardship variable sets, per grain
TRACT_ACCESS = ["EP_NOVEH", "no_vehicle", "EP_MUNIT", "EP_NOINT", "no_broadband"]
TRACT_HARDSHIP = ["EP_POV150", "poverty_under125", "EP_UNEMP", "EP_NOHSDP",
                  "no_diploma_pop25", "EP_AGE65", "age65plus"]
TRACT_MINORITY = ["EP_MINRTY", "EP_HISP", "EP_AFAM"]

BG_ACCESS = ["no_vehicle", "no_broadband"]  # no BG equivalent of EP_MUNIT/EP_NOINT exists
BG_HARDSHIP = ["poverty_under150", "poverty_pct_families", "LOWINCPCT", "UNEMPPCT",
              "LESSHSPCT", "no_diploma_under9yrs", "OVER64PCT"]
BG_MINORITY = ["PEOPCOLORPCT"]  # EJScreen carries no separate Hispanic/Black split

SPARSE_TYPES = {"Blue"}  # 19 single-unit-sited units at both grains


# --------------------------------------------------------------------------
# 3a - density measures
# --------------------------------------------------------------------------

def build_density(df, grain):
    units = load_units(grain)[["GEOID", "ALAND"]]
    out = df.merge(units, on="GEOID", how="left")
    out["area_km2"] = out["ALAND"] / 1e6
    out["pop_density"] = out["population"] / out["area_km2"].where(out["area_km2"] > 0)
    if grain == "bg":
        # ACSTOTHU (total housing units) isn't in the standard EJScreen
        # loader's column set (that loader keeps only the env/socio/health
        # indicators) - read it directly from the same source file.
        ej = pd.read_csv(EJSCREEN_PATH, dtype=str, low_memory=False)
        ej["GEOID"] = ej["ID"].astype(str).str.zfill(12)
        ej = ej[ej["GEOID"].str.startswith(MD_PREFIX)]
        ej["ACSTOTHU"] = pd.to_numeric(ej["ACSTOTHU"], errors="coerce")
        out = out.merge(ej[["GEOID", "ACSTOTHU"]], on="GEOID", how="left")
        out["housing_density"] = out["ACSTOTHU"] / out["area_km2"].where(out["area_km2"] > 0)
    else:
        out["housing_density"] = np.nan  # see report: not available at tract
    return out


def report_density(df, grain, access_vars, hardship_vars):
    print(f"\n--- {grain}: pop_density distribution ---")
    d = df["pop_density"].dropna()
    print(d.describe(percentiles=[.05, .25, .5, .75, .95]).to_string(
        float_format=lambda v: f"{v:,.1f}"))
    if grain == "bg":
        h = df["housing_density"].dropna()
        print(f"\nhousing_density (n={len(h)}, from EJScreen ACSTOTHU):")
        print(h.describe(percentiles=[.05, .25, .5, .75, .95]).to_string(
            float_format=lambda v: f"{v:,.1f}"))
    else:
        print("\nhousing_density: NOT AVAILABLE at tract grain. The 10 pulled "
              "ACS CRE tables (B25044, B25014, etc.) carry OCCUPIED housing "
              "units as their denominator, not total housing units - using "
              "that would misrepresent density in coastal/seasonal tracts "
              "with high vacancy, and no total-housing-unit table was pulled "
              "at tract grain. Not approximated; reported as unavailable "
              "rather than substituted.")

    rows = []
    for v in access_vars + hardship_vars:
        x, y = df["pop_density"], df[v]
        valid = x.notna() & y.notna()
        if valid.sum() < 5:
            rows.append({"variable": v, "block": "access" if v in access_vars else "hardship",
                        "n": int(valid.sum()), "pearson_r": np.nan, "spearman_rho": np.nan})
            continue
        rp, _ = stats.pearsonr(x[valid], y[valid])
        rs, _ = stats.spearmanr(x[valid], y[valid])
        rows.append({"variable": v, "block": "access" if v in access_vars else "hardship",
                    "n": int(valid.sum()), "pearson_r": rp, "spearman_rho": rs})
    out = pd.DataFrame(rows)
    out.to_csv(OUT / f"6a_density_vs_access_hardship_{grain}.csv", index=False)
    print(f"\ndensity vs. access/hardship blocks ({grain}):")
    print(out.to_string(index=False, float_format=lambda v: f"{v:.3f}" if isinstance(v, float) else str(v)))
    return out


# --------------------------------------------------------------------------
# 3b - partial correlation
# --------------------------------------------------------------------------

def spearman_partial(x, y, z):
    """Returns (n, r_xy, r_xz, r_yz, r_partial, t, p) on listwise-complete
    rows across all three series."""
    valid = x.notna() & y.notna() & z.notna()
    n = int(valid.sum())
    if n < 10:
        return n, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan
    xs, ys, zs = x[valid], y[valid], z[valid]
    r_xy, _ = stats.spearmanr(xs, ys)
    r_xz, _ = stats.spearmanr(xs, zs)
    r_yz, _ = stats.spearmanr(ys, zs)
    denom = np.sqrt((1 - r_xz ** 2) * (1 - r_yz ** 2))
    if denom == 0 or np.isnan(denom):
        return n, r_xy, r_xz, r_yz, np.nan, np.nan, np.nan
    r_partial = (r_xy - r_xz * r_yz) / denom
    if abs(r_partial) >= 1 or n <= 3:
        t, p = np.nan, np.nan
    else:
        t = r_partial * np.sqrt((n - 3) / (1 - r_partial ** 2))
        p = 2 * (1 - stats.t.cdf(abs(t), df=n - 3))
    return n, r_xy, r_xz, r_yz, r_partial, t, p


def partial_table(df, vuln_vars, sparse_set, grain):
    rows = []
    for t in ["gray", "green"]:
        share_col = f"type_{t}_share"
        for v in vuln_vars:
            n, r_xy, r_xz, r_yz, r_partial, tstat, p = spearman_partial(
                df[v], df[share_col], df["pop_density"])
            rows.append({
                "variable": v, "type": t, "n": n,
                "zero_order_rho": r_xy, "partial_rho": r_partial,
                "abs_change": abs(r_partial - r_xy) if pd.notna(r_partial) else np.nan,
                "pct_change": (abs(r_partial - r_xy) / abs(r_xy) * 100
                              if pd.notna(r_partial) and r_xy else np.nan),
                "t_stat": tstat, "p_partial": p,
                "flag_sparse": t.capitalize() in sparse_set,
            })
    out = pd.DataFrame(rows)
    # FDR within each (type) family, matching Part 4's convention
    out["p_partial_fdr"] = np.nan
    out["zero_order_p_fdr_ref"] = np.nan  # cross-referenced from Part 4, not recomputed
    for t in ["gray", "green"]:
        m = out["type"] == t
        valid = out.loc[m, "p_partial"].notna()
        if valid.sum():
            _, adj, _, _ = multipletests(out.loc[m & (out["type"] == t), "p_partial"][valid],
                                         method="fdr_bh")
            out.loc[out[m].index[valid.values], "p_partial_fdr"] = adj
    out["sig_after_control"] = out["p_partial_fdr"] < 0.05
    out.to_csv(OUT / f"6b_partial_correlation_{grain}.csv", index=False)
    return out


def summarize_partial(out, grain, access_vars, minority_vars):
    print(f"\n--- {grain}: partial correlation summary ---")
    for label, varlist in [("access/connectivity", access_vars), ("minority-composition", minority_vars)]:
        sub = out[out["variable"].isin(varlist)]
        print(f"\n{label} variables ({len(varlist)} vars x 2 types):")
        print(sub[["variable", "type", "n", "zero_order_rho", "partial_rho",
                   "pct_change", "p_partial_fdr", "sig_after_control", "flag_sparse"]]
              .to_string(index=False, float_format=lambda v: f"{v:.3f}" if isinstance(v, float) else str(v)))


# --------------------------------------------------------------------------
# 3c - density-tercile stratification
# --------------------------------------------------------------------------

def stratify(df, grain, access_vars, minority_vars):
    d = df.dropna(subset=["pop_density"]).copy()
    d["density_tercile"], bins = pd.qcut(d["pop_density"], 3, labels=["low", "medium", "high"],
                                         retbins=True)
    print(f"\n--- {grain}: density tercile boundaries (pop_density, per km^2) ---")
    print(f"low < {bins[1]:,.1f} <= medium < {bins[2]:,.1f} <= high")
    print(d["density_tercile"].value_counts().to_string())

    rows = []
    for tercile in ["low", "medium", "high"]:
        sub = d[d["density_tercile"] == tercile]
        n_stratum = len(sub)
        for t in ["gray", "green"]:
            share_col = f"type_{t}_share"
            for v in access_vars + minority_vars:
                x, y = sub[v], sub[share_col]
                valid = x.notna() & y.notna()
                if valid.sum() < 10:
                    rows.append({"tercile": tercile, "n_stratum": n_stratum, "type": t,
                                "variable": v, "n": int(valid.sum()), "spearman_rho": np.nan,
                                "p": np.nan})
                    continue
                rho, p = stats.spearmanr(x[valid], y[valid])
                rows.append({"tercile": tercile, "n_stratum": n_stratum, "type": t,
                            "variable": v, "n": int(valid.sum()), "spearman_rho": rho, "p": p})
    out = pd.DataFrame(rows)
    out["p_fdr"] = np.nan
    valid = out["p"].notna()
    if valid.sum():
        _, adj, _, _ = multipletests(out.loc[valid, "p"], method="fdr_bh")
        out.loc[valid, "p_fdr"] = adj
    out.to_csv(OUT / f"6c_density_stratified_{grain}.csv", index=False)
    print(f"\nstratified correlations ({grain}):")
    print(out.to_string(index=False, float_format=lambda v: f"{v:.3f}" if isinstance(v, float) else str(v)))
    return out, bins


# --------------------------------------------------------------------------

def main():
    tract = add_type_scale_measures(load_tract(), per_capita=True)
    bg = add_type_scale_measures(load_bg(), per_capita=False)

    tract = build_density(tract, "tract")
    bg = build_density(bg, "bg")

    report_density(tract, "tract", TRACT_ACCESS, TRACT_HARDSHIP)
    report_density(bg, "bg", BG_ACCESS, BG_HARDSHIP)

    tract.to_csv(OUT / "6a_tract_with_density.csv", index=False)
    bg.to_csv(OUT / "6a_bg_with_density.csv", index=False)

    print("\n" + "=" * 78 + "\n3b - PARTIAL CORRELATION\n" + "=" * 78)
    pt = partial_table(tract, TRACT_VULN_VARS, SPARSE_TYPES, "tract")
    pb = partial_table(bg, BG_VULN_VARS, SPARSE_TYPES, "bg")
    summarize_partial(pt, "tract", TRACT_ACCESS, TRACT_MINORITY)
    summarize_partial(pb, "bg", BG_ACCESS, BG_MINORITY)

    print("\n" + "=" * 78 + "\n3c - DENSITY-TERCILE STRATIFICATION\n" + "=" * 78)
    stratify(tract, "tract", TRACT_ACCESS, TRACT_MINORITY)
    stratify(bg, "bg", BG_ACCESS, BG_MINORITY)


if __name__ == "__main__":
    main()
