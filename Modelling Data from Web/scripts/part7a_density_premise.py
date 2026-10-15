"""Part 7, Task 1: the density premise check. Before crediting the Part 6
partial-correlation result as evidence that density does NOT explain the
composition pattern, check that density predicted the outcome variables at
all - if pop_density itself has no relationship with these outcomes, the
partial-correlation test was uninformative regardless of how little it
moved the vulnerability-variable correlations.

Direct zero-order correlation of pop_density (and housing_density at BG)
against the outcome side: the four type shares, investment_per_capita (raw
and rank-transformed, given its skew), and the two volume-proxy binaries.

Descriptive only.

Usage: python scripts/part7a_density_premise.py
Outputs: output/part7_gray/1_density_premise_check.csv
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats


sys.path.insert(0, str(Path(__file__).resolve().parent))
from analysis_variables import add_type_scale_measures, load_bg, load_tract  # noqa: E402
from part6c_density_control import build_density  # noqa: E402
from scaler_projects import OUTPUT_DIR  # noqa: E402

OUT = OUTPUT_DIR / "part7_gray"
OUT.mkdir(exist_ok=True)
warnings.filterwarnings("ignore", category=RuntimeWarning)

TYPE_SHARES = ["type_gray_share", "type_green_share", "type_blue_share", "type_hybrid_share"]
BINARIES = ["investment_any_excl_county", "investment_any_single_unit"]


def corr_row(x, y, xname, yname):
    valid = x.notna() & y.notna() & np.isfinite(x) & np.isfinite(y)
    n = int(valid.sum())
    if n < 5:
        return {"density_var": xname, "outcome": yname, "n": n,
               "pearson_r": np.nan, "pearson_p": np.nan,
               "spearman_rho": np.nan, "spearman_p": np.nan}
    rp, pp = stats.pearsonr(x[valid], y[valid])
    rs, ps = stats.spearmanr(x[valid], y[valid])
    return {"density_var": xname, "outcome": yname, "n": n,
           "pearson_r": rp, "pearson_p": pp, "spearman_rho": rs, "spearman_p": ps}


def binary_row(dens, binary, xname, yname):
    valid = dens.notna() & binary.notna()
    a = dens[valid & (binary == 1)]
    b = dens[valid & (binary == 0)]
    if len(a) < 3 or len(b) < 3:
        return {"density_var": xname, "outcome": yname, "n_receiving": len(a),
               "n_not": len(b), "mean_receiving": np.nan, "mean_not": np.nan, "mw_p": np.nan}
    stat, p = stats.mannwhitneyu(a, b, alternative="two-sided")
    return {"density_var": xname, "outcome": yname, "n_receiving": len(a),
           "n_not": len(b), "mean_receiving": a.mean(), "mean_not": b.mean(), "mw_p": p}


def run_grain(df, grain, density_vars):
    rows = []
    for dvar in density_vars:
        for outcome in TYPE_SHARES:
            rows.append(corr_row(df[dvar], df[outcome], dvar, outcome))
        rows.append(corr_row(df[dvar], df["investment_per_capita"], dvar, "investment_per_capita_raw"))
        # pandas .rank() keeps NaN as NaN (unlike scipy.stats.rankdata, which
        # has no missing-value handling by default) - needed at BG grain,
        # where investment_per_capita is undefined for zero-population units.
        ranked = df["investment_per_capita"].rank()
        rows.append(corr_row(df[dvar], ranked, dvar, "investment_per_capita_rank"))
    out = pd.DataFrame(rows)

    bin_rows = []
    for dvar in density_vars:
        for outcome in BINARIES:
            bin_rows.append(binary_row(df[dvar], df[outcome], dvar, outcome))
    binr = pd.DataFrame(bin_rows)
    return out, binr


def housing_density_control_bg(bg):
    """Supplementary: Part 6 controlled for pop_density, but at block group
    housing_density turns out to be the stronger correlate of composition
    (see the main table). Re-run the same partial correlation controlling for
    housing_density instead, so the Part 6 conclusion is tested against the
    stronger of the two available density measures rather than the weaker."""
    from part6c_density_control import spearman_partial
    from statsmodels.stats.multitest import multipletests
    rows = []
    for t in ["gray", "green"]:
        share = f"type_{t}_share"
        for v in ["no_vehicle", "no_broadband", "PEOPCOLORPCT"]:
            n_p, r_xy, _, _, r_pop, _, p_pop = spearman_partial(
                bg[v], bg[share], bg["pop_density"])
            n_h, _, _, _, r_hou, _, p_hou = spearman_partial(
                bg[v], bg[share], bg["housing_density"])
            rows.append({"type": t, "variable": v, "n": n_h,
                        "zero_order_rho": r_xy,
                        "partial_rho_pop_density": r_pop, "p_pop": p_pop,
                        "partial_rho_housing_density": r_hou, "p_housing": p_hou})
    out = pd.DataFrame(rows)
    for col, pcol in [("p_pop", "p_pop_fdr"), ("p_housing", "p_housing_fdr")]:
        valid = out[col].notna()
        out[pcol] = np.nan
        if valid.sum():
            _, adj, _, _ = multipletests(out.loc[valid, col], method="fdr_bh")
            out.loc[valid, pcol] = adj
    out.to_csv(OUT / "1_housing_density_control_bg.csv", index=False)
    print("\n--- SUPPLEMENTARY: same partial correlation controlling for "
          "housing_density instead of pop_density (block group) ---")
    print(out.to_string(index=False, float_format=lambda v: f"{v:.4f}" if isinstance(v, float) else str(v)))
    return out


def main():
    tract = add_type_scale_measures(load_tract(), per_capita=True)
    bg = add_type_scale_measures(load_bg(), per_capita=False)
    tract = build_density(tract, "tract")
    bg = build_density(bg, "bg")

    ct, bt = run_grain(tract, "tract", ["pop_density"])
    cb, bb = run_grain(bg, "bg", ["pop_density", "housing_density"])

    ct.to_csv(OUT / "1_density_premise_continuous_tract.csv", index=False)
    bt.to_csv(OUT / "1_density_premise_binary_tract.csv", index=False)
    cb.to_csv(OUT / "1_density_premise_continuous_bg.csv", index=False)
    bb.to_csv(OUT / "1_density_premise_binary_bg.csv", index=False)

    print("=" * 78 + "\nTASK 1 - DENSITY PREMISE CHECK\n" + "=" * 78)
    print("\n--- tract, continuous ---")
    print(ct.to_string(index=False, float_format=lambda v: f"{v:.4f}" if isinstance(v, float) else str(v)))
    print("\n--- tract, binary ---")
    print(bt.to_string(index=False, float_format=lambda v: f"{v:.4f}" if isinstance(v, float) else str(v)))
    print("\n--- bg, continuous ---")
    print(cb.to_string(index=False, float_format=lambda v: f"{v:.4f}" if isinstance(v, float) else str(v)))
    print("\n--- bg, binary ---")
    print(bb.to_string(index=False, float_format=lambda v: f"{v:.4f}" if isinstance(v, float) else str(v)))

    print("\nmax |Spearman rho| tract:", ct["spearman_rho"].abs().max())
    print("max |Spearman rho| bg   :", cb["spearman_rho"].abs().max())

    housing_density_control_bg(bg)


if __name__ == "__main__":
    main()
