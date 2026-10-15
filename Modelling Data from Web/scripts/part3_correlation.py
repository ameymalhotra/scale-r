"""Part 3: correlation among the vulnerability/exposure indicators, within
each grain separately (never across grains). Pearson + Spearman matrices,
VIF, |r|>0.8 duplicate pairs, and the three named overlap questions.

Usage: python scripts/part3_correlation.py
Outputs: output/part3_correlation/*.csv, *.png
"""
import sys
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from statsmodels.stats.outliers_influence import variance_inflation_factor

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analysis_variables import (  # noqa: E402
    BG_DUPLICATE_CANDIDATES, BG_VULN_VARS, TRACT_OVERLAP_PAIRS,
    TRACT_VULN_VARS, load_bg, load_tract,
)
from scaler_projects import OUTPUT_DIR  # noqa: E402
from vulnerability_loaders import ADI_VARS, EJ_ENV, EJ_HEALTH, EJ_SOCIO  # noqa: E402

OUT = OUTPUT_DIR / "part3_correlation"
OUT.mkdir(exist_ok=True)
warnings.filterwarnings("ignore", category=RuntimeWarning)


def corr_matrices(df, varnames, label):
    x = df[varnames]
    pear = x.corr(method="pearson")
    spear = x.corr(method="spearman")
    pear.to_csv(OUT / f"{label}_pearson.csv")
    spear.to_csv(OUT / f"{label}_spearman.csv")

    for name, mat in [("pearson", pear), ("spearman", spear)]:
        fig, ax = plt.subplots(figsize=(max(10, len(varnames) * 0.42),
                                        max(8, len(varnames) * 0.38)))
        sns.heatmap(mat, cmap="RdBu_r", center=0, vmin=-1, vmax=1,
                   square=True, linewidths=0.3, ax=ax,
                   cbar_kws={"label": f"{name} r"})
        ax.set_title(f"{label}: {name} correlation ({len(varnames)} indicators)")
        plt.tight_layout()
        fig.savefig(OUT / f"{label}_{name}_heatmap.png", dpi=130)
        plt.close(fig)
    return pear, spear


def high_corr_pairs(pear, spear, label, thresh=0.8):
    rows = []
    cols = pear.columns
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            a, b = cols[i], cols[j]
            rp, rs = pear.iloc[i, j], spear.iloc[i, j]
            if pd.notna(rp) and abs(rp) > thresh:
                rows.append({"var_a": a, "var_b": b, "pearson_r": rp,
                            "spearman_rho": rs, "abs_pearson": abs(rp)})
    out = pd.DataFrame(rows).sort_values("abs_pearson", ascending=False)
    out.to_csv(OUT / f"{label}_high_corr_pairs.csv", index=False)
    print(f"\n{label}: {len(out)} pairs with |Pearson r| > {thresh}")
    if len(out):
        print(out.drop(columns="abs_pearson").to_string(index=False,
              float_format=lambda v: f"{v:.3f}"))
    return out


def compute_vif(df, varnames, label):
    x = df[varnames].dropna()
    print(f"\n{label}: VIF computed on {len(x)} complete-case rows "
          f"(of {len(df)} total; listwise deletion for this step only)")
    x = x.loc[:, x.std() > 0]  # VIF undefined for zero-variance columns
    dropped = set(varnames) - set(x.columns)
    if dropped:
        print(f"  dropped from VIF (zero variance in complete cases): {dropped}")
    vifs = []
    arr = x.values.astype(float)
    for i, col in enumerate(x.columns):
        try:
            v = variance_inflation_factor(arr, i)
        except Exception as e:  # singular matrix etc - report, don't hide
            v = np.nan
            print(f"  VIF failed for {col}: {e}")
        vifs.append({"variable": col, "VIF": v})
    out = pd.DataFrame(vifs).sort_values("VIF", ascending=False)
    out.to_csv(OUT / f"{label}_vif.csv", index=False)
    print(out.to_string(index=False, float_format=lambda v: f"{v:.2f}"))
    print(f"  variables with VIF > 10 (severe multicollinearity in combination): "
          f"{out[out.VIF > 10]['variable'].tolist()}")
    return out


def tract_overlap_report(df):
    print("\n" + "=" * 78 + "\nTRACT: SVI EP_* vs ACS CRE overlap (named pairs)\n" + "=" * 78)
    rows = []
    for a, b, note in TRACT_OVERLAP_PAIRS:
        x, y = df[a], df[b]
        valid = x.notna() & y.notna()
        rp = x[valid].corr(y[valid], method="pearson")
        rs = x[valid].corr(y[valid], method="spearman")
        rows.append({"svi_var": a, "cre_var": b, "n": int(valid.sum()),
                    "pearson_r": rp, "spearman_rho": rs, "note": note})
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "tract_svi_vs_cre_overlap.csv", index=False)
    print(out.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    return out


def bg_socio_adi_overlap(df):
    print("\n" + "=" * 78
          + "\nBLOCK GROUP: EJScreen socioeconomic (7) vs ADI (13) - full cross\n"
          + "=" * 78)
    rows = []
    for s in EJ_SOCIO:
        for a in ADI_VARS:
            x, y = df[s], df[a]
            valid = x.notna() & y.notna()
            if valid.sum() < 10:
                continue
            rp = x[valid].corr(y[valid], method="pearson")
            rs = x[valid].corr(y[valid], method="spearman")
            rows.append({"ejscreen_socio": s, "adi_component": a,
                        "n": int(valid.sum()), "pearson_r": rp, "spearman_rho": rs})
    out = pd.DataFrame(rows).sort_values("pearson_r", key=abs, ascending=False)
    out.to_csv(OUT / "bg_ejscreen_socio_vs_adi_full_cross.csv", index=False)
    print("\ntop 15 by |Pearson r| (full cross, all socio x ADI pairs):")
    print(out.head(15).to_string(index=False, float_format=lambda v: f"{v:.3f}"))

    print("\n--- the 4 flagged TRUE-DUPLICATE candidates ---")
    checks = [
        ("no vehicle", "EJScreen has NO raw 'no vehicle' column in this extract "
                       "(not PTRAF/traffic - that's a hazard proximity measure, "
                       "not a household-vehicle-access measure). Cannot check this pair; "
                       "flagged as a genuine gap, not computed."),
        ("no internet", "EJScreen has NO raw 'no household internet' column in "
                        "this extract. Cannot check this pair; flagged as a gap."),
        ("unemployment", "EJScreen UNEMPPCT exists; DATA_PROCESSING.md says ADI "
                         "dropped unemployment as a duplicate (never pulled) - "
                         "so there is no ADI-side unemployment column to correlate "
                         "against. The redundancy claim can't be VERIFIED numerically "
                         "because one side was never collected."),
    ]
    for name, note in checks:
        print(f"  {name}: {note}")
    x, y = df["LESSHSPCT"], df["no_diploma_under9yrs"]
    valid = x.notna() & y.notna()
    rp = x[valid].corr(y[valid], method="pearson")
    rs = x[valid].corr(y[valid], method="spearman")
    print(f"  less-than-HS vs <9yrs-education: n={int(valid.sum())}, "
          f"Pearson r={rp:.3f}, Spearman rho={rs:.3f} "
          f"(different thresholds by construction - HS-diploma cut vs 8th-grade "
          f"cut - so a high but non-~1.0 correlation is the EXPECTED result of "
          f"'related, not identical')")
    dup_rows = [{"pair": "no vehicle", "pearson_r": np.nan, "spearman_rho": np.nan,
                "verdict": "cannot compute - EJScreen column absent"},
               {"pair": "no internet", "pearson_r": np.nan, "spearman_rho": np.nan,
                "verdict": "cannot compute - EJScreen column absent"},
               {"pair": "unemployment", "pearson_r": np.nan, "spearman_rho": np.nan,
                "verdict": "cannot compute - ADI-side column was never pulled (dropped as duplicate)"},
               {"pair": "less-than-HS vs <9yrs", "pearson_r": rp, "spearman_rho": rs,
                "verdict": "high correlation expected, not ~1.0 (different thresholds)"}]
    pd.DataFrame(dup_rows).to_csv(OUT / "bg_flagged_duplicate_candidates.csv", index=False)
    return out


def bg_env_vs_adi_ej_question(df):
    print("\n" + "=" * 78
          + "\nBLOCK GROUP: EJScreen environmental (13) vs ADI (13) - EJ co-location finding\n"
          + "=" * 78)
    rows = []
    for e in EJ_ENV:
        for a in ADI_VARS:
            x, y = df[e], df[a]
            valid = x.notna() & y.notna()
            if valid.sum() < 10:
                continue
            rp = x[valid].corr(y[valid], method="pearson")
            rs = x[valid].corr(y[valid], method="spearman")
            rows.append({"env_indicator": e, "adi_component": a,
                        "n": int(valid.sum()), "pearson_r": rp, "spearman_rho": rs})
    out = pd.DataFrame(rows).sort_values("pearson_r", key=abs, ascending=False)
    out.to_csv(OUT / "bg_environmental_vs_adi_ej_question.csv", index=False)
    print("top 20 by |Pearson r| (environmental exposure x deprivation, "
          "the EJ co-location question):")
    print(out.head(20).to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print(f"\nmedian |r| across all {len(out)} env x ADI pairs: "
          f"{out['pearson_r'].abs().median():.3f}")
    return out


def main():
    tract = load_tract()
    print("=" * 78 + "\nTRACT (698 rows, 34 vulnerability indicators)\n" + "=" * 78)
    pear_t, spear_t = corr_matrices(tract, TRACT_VULN_VARS, "tract")
    high_corr_pairs(pear_t, spear_t, "tract")
    compute_vif(tract, TRACT_VULN_VARS, "tract")
    tract_overlap_report(tract)

    bg = load_bg()
    print("\n" + "=" * 78 + "\nBLOCK GROUP (1,843 rows, 35 vulnerability indicators)\n" + "=" * 78)
    pear_b, spear_b = corr_matrices(bg, BG_VULN_VARS, "bg")
    high_corr_pairs(pear_b, spear_b, "bg")
    compute_vif(bg, BG_VULN_VARS, "bg")
    # income_disparity / median_gross_rent / median_monthly_mortgage are each
    # >20% missing (Part 2), so the all-35-variable VIF above listwise-drops
    # to n=495 of 1843 - too much dropout to trust for "multicollinearity
    # hiding in combination". Re-run VIF without those 3 to see the bulk of
    # the block-group sample.
    bg_vars_dense = [v for v in BG_VULN_VARS
                     if v not in ("income_disparity", "median_gross_rent",
                                 "median_monthly_mortgage")]
    compute_vif(bg, bg_vars_dense, "bg_excl_high_missing")
    bg_socio_adi_overlap(bg)
    bg_env_vs_adi_ej_question(bg)


if __name__ == "__main__":
    main()
