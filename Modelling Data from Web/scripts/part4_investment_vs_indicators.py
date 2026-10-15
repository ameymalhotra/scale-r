"""Part 4 (the core): investment distribution vs the vulnerability indicators.
Two questions kept distinct throughout: HOW MUCH (volume, 4a/4d-any) and WHAT
KIND (composition, 4b/4c/4d-share). Description/correlation only - no fitting.

4a  tract volume:      5 outcomes  x 34 vuln vars
4b  tract type comp.:  4 types x {per_capita, share, any} x 34 vuln vars
4c  tract path comp.:  3 paths x {per_capita, share, any} x 34 vuln vars
4d  bg composition only (no per-capita-by-type; see restriction note)
4e  sparsity carried through from Part 2 as a flag column on every row

Every test row carries n, the raw p-value, and a BH-FDR-adjusted p-value
computed within its family (see FAMILIES below). With this many pairs, some
will clear p<0.05 by chance - the report must not present every significant
cell as a finding; sparse cells (Part 2/4e) must not be read as findings at
all regardless of p-value.

Usage: python scripts/part4_investment_vs_indicators.py
Outputs: output/part4_investment_vs_indicators/*.csv, *.png
"""
import sys
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.nonparametric.smoothers_lowess import lowess
from statsmodels.stats.multitest import multipletests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analysis_variables import (  # noqa: E402
    BG_VULN_VARS, PATHS, TRACT_VULN_VARS, TYPES, add_type_scale_measures,
    load_bg, load_tract,
)
from scaler_projects import OUTPUT_DIR  # noqa: E402

OUT = OUTPUT_DIR / "part4_investment_vs_indicators"
OUT.mkdir(exist_ok=True)
warnings.filterwarnings("ignore", category=RuntimeWarning)

SPARSE_TYPES = {"tract": set(), "bg": set()}  # filled from Part 2 sparsity table


def load_sparsity_flags():
    sp = pd.read_csv(OUTPUT_DIR / "part2_univariate" / "sparsity_baseline.csv")
    flags = {}
    for _, r in sp.iterrows():
        key = (r["grain"], r["dimension"], r["category"])
        flags[key] = bool(r["flag_sparse_lt20units"])
    return flags


SPARSITY = load_sparsity_flags()


def is_sparse(grain, dimension, category):
    return SPARSITY.get((grain, dimension, category), False)


# --------------------------------------------------------------------------
# generic pairwise correlation testing with FDR, applied per "family"
# --------------------------------------------------------------------------

def corr_pair(x, y):
    valid = x.notna() & y.notna() & np.isfinite(x) & np.isfinite(y)
    n = int(valid.sum())
    if n < 5 or x[valid].std() == 0 or y[valid].std() == 0:
        return n, np.nan, np.nan, np.nan, np.nan
    rp, pp = stats.pearsonr(x[valid], y[valid])
    rs, ps = stats.spearmanr(x[valid], y[valid])
    return n, rp, pp, rs, ps


def add_fdr(df, pcol="pearson_p", group_cols=()):
    """BH-FDR within each group (family) of pcol; NaN p-values pass through."""
    out = df.copy()
    out[f"{pcol}_fdr"] = np.nan
    if group_cols:
        groups = out.groupby(list(group_cols), group_keys=True).groups
    else:
        groups = {"_all": out.index}
    for _, idx in groups.items():
        sub = out.loc[idx, pcol]
        valid = sub.notna()
        if valid.sum() == 0:
            continue
        _, adj, _, _ = multipletests(sub[valid], method="fdr_bh")
        out.loc[sub[valid].index, f"{pcol}_fdr"] = adj
    return out


def mann_whitney_pair(vuln, binary):
    valid = vuln.notna() & binary.notna()
    a = vuln[valid & (binary == 1)]
    b = vuln[valid & (binary == 0)]
    if len(a) < 3 or len(b) < 3:
        return dict(n_receiving=len(a), n_not=len(b), mean_receiving=np.nan,
                    mean_not=np.nan, median_receiving=np.nan, median_not=np.nan,
                    mw_p=np.nan)
    stat, p = stats.mannwhitneyu(a, b, alternative="two-sided")
    return dict(n_receiving=len(a), n_not=len(b),
               mean_receiving=a.mean(), mean_not=b.mean(),
               median_receiving=a.median(), median_not=b.median(),
               mw_p=p)


# --------------------------------------------------------------------------
# 4a - tract volume
# --------------------------------------------------------------------------

VOLUME_OUTCOMES = ["investment_per_capita", "investment_total",
                   "investment_per_area", "investment_any_excl_county",
                   "investment_any_single_unit"]
CONTINUOUS_OUTCOMES = ["investment_per_capita", "investment_total", "investment_per_area"]
BINARY_OUTCOMES = ["investment_any_excl_county", "investment_any_single_unit"]


def part4a(df):
    print("=" * 78 + "\nPART 4a - TRACT VOLUME vs VULNERABILITY\n" + "=" * 78)
    rows = []
    for outcome in CONTINUOUS_OUTCOMES:
        for v in TRACT_VULN_VARS:
            n, rp, pp, rs, ps = corr_pair(df[outcome], df[v])
            rows.append({"outcome": outcome, "vuln_var": v, "n": n,
                        "pearson_r": rp, "pearson_p": pp,
                        "spearman_rho": rs, "spearman_p": ps})
    cont = pd.DataFrame(rows)
    cont = add_fdr(cont, "pearson_p", group_cols=["outcome"])
    cont = add_fdr(cont, "spearman_p", group_cols=["outcome"])
    cont.to_csv(OUT / "4a_tract_volume_continuous.csv", index=False)

    rows = []
    for outcome in BINARY_OUTCOMES:
        for v in TRACT_VULN_VARS:
            r = mann_whitney_pair(df[v], df[outcome])
            r.update({"outcome": outcome, "vuln_var": v})
            rows.append(r)
    binr = pd.DataFrame(rows)
    binr = add_fdr(binr, "mw_p", group_cols=["outcome"])
    binr.to_csv(OUT / "4a_tract_volume_binary.csv", index=False)

    # sign/strength consistency check across outcome definitions
    pivot = cont.pivot(index="vuln_var", columns="outcome", values="spearman_rho")
    pivot["sign_flip_or_large_swing"] = False
    for i in pivot.index:
        vals = pivot.loc[i, CONTINUOUS_OUTCOMES]
        if vals.notna().sum() >= 2:
            signs = np.sign(vals.dropna())
            spread = vals.max() - vals.min()
            pivot.loc[i, "sign_flip_or_large_swing"] = bool(
                (signs.nunique() > 1) or (spread > 0.3))
    pivot.to_csv(OUT / "4a_outcome_definition_consistency.csv")
    flips = pivot[pivot["sign_flip_or_large_swing"]]
    print(f"variables whose Spearman rho changes sign or swings >0.3 across "
          f"{{per_capita, total, per_area}}: {len(flips)}")
    print(flips.to_string(float_format=lambda v: f"{v:.3f}" if isinstance(v, float) else str(v)))

    # LOESS scatterplots for the strongest per-capita relationships
    top = cont[cont.outcome == "investment_per_capita"].dropna(
        subset=["spearman_rho"]).nlargest(6, "spearman_rho", keep="all")
    bottom = cont[cont.outcome == "investment_per_capita"].dropna(
        subset=["spearman_rho"]).nsmallest(6, "spearman_rho", keep="all")
    strongest = pd.concat([top, bottom]).sort_values("spearman_rho", key=abs, ascending=False).head(8)
    for _, r in strongest.iterrows():
        make_loess_plot(df, r["vuln_var"], "investment_per_capita",
                        OUT / f"4a_loess_{r['vuln_var']}.png")
    print(f"\nLOESS scatterplots written for: {strongest['vuln_var'].tolist()}")
    return cont, binr


def make_loess_plot(df, xvar, yvar, path, logy=True):
    x = df[xvar]
    y = df[yvar]
    valid = x.notna() & y.notna() & (y > 0 if logy else y.notna())
    x, y = x[valid], y[valid]
    fig, ax = plt.subplots(figsize=(6, 5))
    yy = np.log10(y) if logy else y
    ax.scatter(x, yy, s=14, alpha=0.45, color="#2b6cb0", edgecolor="none")
    sm = lowess(yy, x, frac=0.5, return_sorted=True)
    ax.plot(sm[:, 0], sm[:, 1], color="#c0392b", lw=2.2)
    ax.set_xlabel(xvar)
    ax.set_ylabel(f"log10({yvar})" if logy else yvar)
    ax.set_title(f"{yvar} vs {xvar} (n={len(x)}, LOESS)")
    plt.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


# --------------------------------------------------------------------------
# 4b - tract composition by project type ; 4c - by allocation path
# --------------------------------------------------------------------------

def composition_block(df, vuln_vars, groups, prefix, per_capita, grain):
    """Shared engine for 4b (type) and 4c (path) at tract, and the
    composition-only slice reused by 4d at bg (per_capita=False there)."""
    cont_rows, bin_rows = [], []
    for g in groups:
        sparse = is_sparse(grain, "type" if prefix == "type" else "scale",
                           _category_label(prefix, g))
        measures = (["per_capita", "share"] if per_capita else ["share"])
        for measure in measures:
            col = f"{prefix}_{g}_{measure}"
            for v in vuln_vars:
                n, rp, pp, rs, ps = corr_pair(df[col], df[v])
                cont_rows.append({"group": g, "measure": measure, "vuln_var": v,
                                  "n": n, "pearson_r": rp, "pearson_p": pp,
                                  "spearman_rho": rs, "spearman_p": ps,
                                  "flag_sparse": sparse})
        any_col = f"{prefix}_{g}_any"
        for v in vuln_vars:
            r = mann_whitney_pair(df[v], df[any_col])
            r.update({"group": g, "vuln_var": v, "flag_sparse": sparse})
            bin_rows.append(r)
    cont = pd.DataFrame(cont_rows)
    binr = pd.DataFrame(bin_rows)
    cont = add_fdr(cont, "pearson_p", group_cols=["group", "measure"])
    cont = add_fdr(cont, "spearman_p", group_cols=["group", "measure"])
    binr = add_fdr(binr, "mw_p", group_cols=["group"])
    return cont, binr


def _category_label(prefix, g):
    if prefix == "type":
        return g.capitalize()
    return {"single_unit": "Parcel", "municipality": "Municipality", "county": "County"}[g]


def part4b(df):
    print("\n" + "=" * 78 + "\nPART 4b - TRACT COMPOSITION BY PROJECT TYPE\n" + "=" * 78)
    cont, binr = composition_block(df, TRACT_VULN_VARS, TYPES, "type",
                                   per_capita=True, grain="tract")
    cont.to_csv(OUT / "4b_tract_type_composition_continuous.csv", index=False)
    binr.to_csv(OUT / "4b_tract_type_composition_binary.csv", index=False)
    share = cont[cont.measure == "share"]
    print("strongest SHARE relationships (|Spearman rho|, top 15, sparse flagged):")
    print(share.dropna(subset=["spearman_rho"]).reindex(
        share["spearman_rho"].abs().sort_values(ascending=False).index
    ).head(15)[["group", "vuln_var", "n", "spearman_rho", "spearman_p_fdr", "flag_sparse"]]
        .to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    return cont, binr


def part4c(df):
    print("\n" + "=" * 78 + "\nPART 4c - TRACT COMPOSITION BY ALLOCATION PATH\n" + "=" * 78)
    cont, binr = composition_block(df, TRACT_VULN_VARS, PATHS, "path",
                                   per_capita=True, grain="tract")
    cont.to_csv(OUT / "4c_tract_path_composition_continuous.csv", index=False)
    binr.to_csv(OUT / "4c_tract_path_composition_binary.csv", index=False)
    share = cont[cont.measure == "share"]
    print("strongest SHARE relationships (|Spearman rho|, top 15, sparse flagged):")
    print(share.dropna(subset=["spearman_rho"]).reindex(
        share["spearman_rho"].abs().sort_values(ascending=False).index
    ).head(15)[["group", "vuln_var", "n", "spearman_rho", "spearman_p_fdr", "flag_sparse"]]
        .to_string(index=False, float_format=lambda v: f"{v:.3f}"))

    print("\n'targeted vs untargeted' check: county-only-share vs vulnerability")
    cs = cont[(cont.group == "county") & (cont.measure == "share")]
    top_county = cs.dropna(subset=["spearman_rho"]).reindex(
        cs["spearman_rho"].abs().sort_values(ascending=False).index).head(10)
    print(top_county[["vuln_var", "n", "spearman_rho", "spearman_p_fdr"]]
          .to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    return cont, binr


# --------------------------------------------------------------------------
# 4d - block group, composition only
# --------------------------------------------------------------------------

def part4d(df):
    print("\n" + "=" * 78 + "\nPART 4d - BLOCK GROUP: COMPOSITION ONLY\n" + "=" * 78)
    print("EXCLUDED at this grain (stated per the prompt's restriction):")
    print("  - {type}_per_capita, {path}_per_capita: per-capita is unstable at BG")
    print("    (max $1.7M/person; a 6-resident BG holds $6.6M) - see")
    print("    zero_population_investigation.md Part 3. Not computed here.")
    print("  - investment_total / investment_per_area as correlation targets:")
    print("    not requested for BG composition; investment_per_capita is")
    print("    reported DESCRIPTIVELY only, no correlations built on it.")
    pc = df["investment_per_capita"].dropna()
    print(f"\ninvestment_per_capita, descriptive only: n={len(pc)}, "
          f"min={pc.min():.2f}, p50={pc.median():.2f}, p95={pc.quantile(.95):,.0f}, "
          f"p99={pc.quantile(.99):,.0f}, max={pc.max():,.0f}")

    cont_t, binr_t = composition_block(df, BG_VULN_VARS, TYPES, "type",
                                       per_capita=False, grain="bg")
    cont_p, binr_p = composition_block(df, BG_VULN_VARS, PATHS, "path",
                                       per_capita=False, grain="bg")
    cont_t.to_csv(OUT / "4d_bg_type_composition_continuous.csv", index=False)
    binr_t.to_csv(OUT / "4d_bg_type_composition_binary.csv", index=False)
    cont_p.to_csv(OUT / "4d_bg_path_composition_continuous.csv", index=False)
    binr_p.to_csv(OUT / "4d_bg_path_composition_binary.csv", index=False)

    # volume proxies at BG: investment_any_excl_county / investment_any_single_unit
    rows = []
    for outcome in BINARY_OUTCOMES:
        for v in BG_VULN_VARS:
            r = mann_whitney_pair(df[v], df[outcome])
            r.update({"outcome": outcome, "vuln_var": v})
            rows.append(r)
    vol = pd.DataFrame(rows)
    vol = add_fdr(vol, "mw_p", group_cols=["outcome"])
    vol.to_csv(OUT / "4d_bg_volume_proxy_binary.csv", index=False)

    share = cont_t[cont_t.measure == "share"]
    print("\nstrongest TYPE SHARE relationships at BG (|Spearman rho|, top 15):")
    print(share.dropna(subset=["spearman_rho"]).reindex(
        share["spearman_rho"].abs().sort_values(ascending=False).index
    ).head(15)[["group", "vuln_var", "n", "spearman_rho", "spearman_p_fdr", "flag_sparse"]]
        .to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    return cont_t, binr_t, cont_p, binr_p, vol


def main():
    tract = add_type_scale_measures(load_tract(), per_capita=True)
    bg = add_type_scale_measures(load_bg(), per_capita=False)

    part4a(tract)
    part4b(tract)
    part4c(tract)
    part4d(bg)

    print("\n" + "=" * 78 + "\nPART 4e - SPARSITY (carried from Part 2)\n" + "=" * 78)
    sp = pd.read_csv(OUTPUT_DIR / "part2_univariate" / "sparsity_baseline.csv")
    print(sp[sp.flag_sparse_lt20units].to_string(index=False))
    print("\nAll Part 4b/4c/4d output rows for these categories carry "
          "flag_sparse=True and must not be read as findings.")


if __name__ == "__main__":
    main()
