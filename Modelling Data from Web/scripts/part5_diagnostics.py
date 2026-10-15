"""Part 5: diagnostics that decide the modeling approach downstream. Still no
fitting - these are robustness/structure checks on the correlations already
computed in Part 4, plus new spatial-autocorrelation and zero/skew profiling.

  - Pennsuco (12086981100) influence check
  - flag_large_project (3 units, 2 surviving SMART corridors) split
  - Moran's I via k-NN weights, on the outcome variants, main type shares,
    and key vulnerability variables
  - zero/skew profile per outcome variant, including per type

Usage: python scripts/part5_diagnostics.py
Outputs: output/part5_diagnostics/*.csv
"""
import sys
import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from libpysal.weights import KNN
from esda.moran import Moran
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
from allocation import PROJ_CRS, load_units  # noqa: E402
from analysis_variables import (  # noqa: E402
    BG_VULN_VARS, TRACT_VULN_VARS, add_type_scale_measures, load_bg, load_tract,
)
from scaler_projects import OUTPUT_DIR  # noqa: E402

OUT = OUTPUT_DIR / "part5_diagnostics"
OUT.mkdir(exist_ok=True)
warnings.filterwarnings("ignore", category=RuntimeWarning)

PENNSUCO = "12086981100"
K_NEIGHBORS = 6  # see report: matches the typical count of contiguous
                 # neighbors for an urban tract/BG grid; standard default in
                 # spatial-econometrics practice (Anselin) and avoids the
                 # island (zero-neighbor) problem that a fixed-distance band
                 # would create for the size-heterogeneous parcel/rural mix.


# --------------------------------------------------------------------------
# 5a - Pennsuco influence
# --------------------------------------------------------------------------

HEADLINE_TRACT_PAIRS = [
    ("investment_per_capita", "EP_NOVEH"), ("investment_per_capita", "EP_MUNIT"),
    ("investment_per_capita", "no_vehicle"), ("investment_per_capita", "EP_MINRTY"),
    ("investment_per_capita", "EP_POV150"), ("investment_per_capita", "poverty_under125"),
    ("investment_per_capita", "EP_AGE65"), ("investment_per_capita", "age65plus"),
    ("EP_NOVEH", "no_vehicle"), ("EP_NOHSDP", "no_diploma_pop25"),
]


def corr_with_without(df, xcol, ycol, drop_ids, drop_label):
    x, y = df[xcol], df[ycol]
    valid = x.notna() & y.notna()
    r_all, p_all = stats.spearmanr(x[valid], y[valid])
    keep = valid & ~df["GEOID"].isin(drop_ids)
    r_drop, p_drop = stats.spearmanr(x[keep], y[keep])
    return {"x": xcol, "y": ycol, "n_all": int(valid.sum()),
           "spearman_all": r_all, "n_excl": int(keep.sum()),
           f"spearman_excl_{drop_label}": r_drop,
           "abs_change": abs(r_drop - r_all),
           "pct_change": abs(r_drop - r_all) / abs(r_all) * 100 if r_all else np.nan}


def pennsuco_check(df):
    print("=" * 78 + "\n5a - PENNSUCO INFLUENCE CHECK (12086981100)\n" + "=" * 78)
    row = df[df.GEOID == PENNSUCO]
    if row.empty:
        print("Pennsuco tract not found in tract_analysis.csv - unexpected."); return None
    r = row.iloc[0]
    print(f"pop={int(r.population)}, investment_total=${r.investment_total:,.0f}, "
          f"investment_per_capita=${r.investment_per_capita:,.0f}")
    rows = [corr_with_without(df, x, y, [PENNSUCO], "pennsuco") for x, y in HEADLINE_TRACT_PAIRS]
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "5a_pennsuco_influence.csv", index=False)
    print(out.to_string(index=False, float_format=lambda v: f"{v:.4f}" if isinstance(v, float) else str(v)))
    big_move = out[out["pct_change"] > 10]
    print(f"\npairs whose Spearman rho moves >10% when Pennsuco is dropped: "
          f"{len(big_move)}")
    return out


# --------------------------------------------------------------------------
# 5b - flag_large_project split
# --------------------------------------------------------------------------

def flagged_check(df):
    print("\n" + "=" * 78 + "\n5b - FLAG_LARGE_PROJECT SPLIT (3 units)\n" + "=" * 78)
    flagged_ids = df.loc[df["flag_large_project"] == 1, "GEOID"].tolist()
    print(f"flagged tracts: {flagged_ids}")
    print(df[df.GEOID.isin(flagged_ids)][
        ["GEOID", "population", "investment_total", "investment_per_capita"]
    ].to_string(index=False, float_format=lambda v: f"{v:,.1f}"))
    rows = [corr_with_without(df, x, y, flagged_ids, "flagged")
            for x, y in HEADLINE_TRACT_PAIRS]
    out = pd.DataFrame(rows)
    out.to_csv(OUT / "5b_flag_large_project_influence.csv", index=False)
    print(out.to_string(index=False, float_format=lambda v: f"{v:.4f}" if isinstance(v, float) else str(v)))
    big_move = out[out["pct_change"] > 10]
    print(f"\npairs whose Spearman rho moves >10% when the 3 flagged units are "
          f"dropped: {len(big_move)}")
    return out


# --------------------------------------------------------------------------
# 5c - Moran's I
# --------------------------------------------------------------------------

def build_knn_weights(geoid_order, grain, k=K_NEIGHBORS):
    units = load_units(grain).to_crs(PROJ_CRS)
    units = units.set_index("GEOID").loc[geoid_order]
    cen = units.geometry.centroid
    coords = np.column_stack([cen.x.values, cen.y.values])
    w = KNN.from_array(coords, k=k)
    w.transform = "r"
    return w


def moran_batch(df, varnames, w, label):
    grain = "tract" if label.startswith("tract") else "bg"
    rows = []
    for v in varnames:
        s = df[v]
        valid = s.notna() & np.isfinite(s)
        if valid.sum() < 30:
            rows.append({"variable": v, "n": int(valid.sum()), "I": np.nan,
                        "p_sim": np.nan, "z_sim": np.nan,
                        "note": "too few non-missing units for Moran's I"})
            continue
        vals = s[valid].values
        # p_sim is Monte Carlo (999 permutations drawn via numpy.random) and
        # otherwise differs slightly run to run - np.random.seed below pins it.
        np.random.seed(12086)
        if valid.sum() == len(s):
            m = Moran(vals, w, permutations=999)
        else:
            # Moran needs one weight-matrix row per value supplied - rebuild
            # k-NN weights restricted to the non-missing subset (same k),
            # rather than imputing a value to keep the full matrix.
            sub_ids = df.loc[valid, "GEOID"].tolist()
            sub_w = build_knn_weights(sub_ids, grain)
            m = Moran(vals, sub_w, permutations=999)
        rows.append({"variable": v, "n": int(valid.sum()), "I": m.I,
                    "p_sim": m.p_sim, "z_sim": m.z_sim, "note": ""})
    return pd.DataFrame(rows)


def moran_section(df, grain):
    print("\n" + "=" * 78 + f"\n5c - MORAN'S I ({grain}, k={K_NEIGHBORS} nearest neighbors)\n"
          + "=" * 78)
    w = build_knn_weights(df["GEOID"].tolist(), grain)

    outcome_vars = (["investment_per_capita", "investment_any_excl_county",
                     "investment_any_single_unit"] if grain == "tract"
                    else ["investment_any_excl_county", "investment_any_single_unit"])
    type_share_vars = ["type_gray_share", "type_blue_share", "type_hybrid_share",
                       "type_green_share"]
    vuln_vars = (TRACT_VULN_VARS if grain == "tract" else BG_VULN_VARS)
    # "key" vulnerability variables = the ones that surfaced most in Part 4/3
    key_vuln = (["EP_NOVEH", "no_vehicle", "EP_MUNIT", "EP_MINRTY", "EP_POV150",
                "poverty_under125", "EP_AGE65", "age65plus", "EP_NOHSDP"]
                if grain == "tract" else
                ["LOWINCPCT", "LESSHSPCT", "PEOPCOLORPCT", "PM25", "OZONE",
                "UST", "median_family_income", "poverty_under150"])

    out_res = moran_batch(df, outcome_vars, w, f"{grain}_outcomes")
    type_res = moran_batch(df, type_share_vars, w, f"{grain}_types")
    vuln_res = moran_batch(df, key_vuln, w, f"{grain}_vuln")
    all_res = pd.concat([out_res.assign(family="outcome"),
                         type_res.assign(family="type_share"),
                         vuln_res.assign(family="key_vulnerability")])
    all_res.to_csv(OUT / f"5c_moran_{grain}.csv", index=False)
    print(all_res.to_string(index=False, float_format=lambda v: f"{v:.4f}" if isinstance(v, float) else str(v)))
    sig = all_res[(all_res["p_sim"] < 0.05) & all_res["I"].notna()]
    print(f"\nvariables with significant positive/negative spatial "
          f"autocorrelation (p_sim<0.05): {len(sig)} of {len(all_res)}")
    return all_res


# --------------------------------------------------------------------------
# 5d - zero/skew profile per outcome variant, incl. per type
# --------------------------------------------------------------------------

def zero_skew_profile(df, grain, type_cols, path_cols):
    print("\n" + "=" * 78 + f"\n5d - ZERO / SKEW PROFILE ({grain})\n" + "=" * 78)
    cols = (["investment_total", "investment_per_capita", "investment_per_area"]
            if grain == "tract" else ["investment_total"])
    cols += type_cols + path_cols
    rows = []
    for c in cols:
        s = df[c]
        v = s.dropna()
        n_zero = int((v == 0).sum())
        rows.append({"variable": c, "n": len(v), "n_zero": n_zero,
                    "pct_zero": round(n_zero / len(v) * 100, 1) if len(v) else np.nan,
                    "skew": v.skew() if len(v) > 2 else np.nan,
                    "skew_nonzero_only": v[v > 0].skew() if (v > 0).sum() > 2 else np.nan})
    out = pd.DataFrame(rows)
    out.to_csv(OUT / f"5d_zero_skew_{grain}.csv", index=False)
    print(out.to_string(index=False, float_format=lambda v: f"{v:.2f}" if isinstance(v, float) else str(v)))
    heavy_zero = out[out["pct_zero"] > 50]
    print(f"\nvariables with >50% exact zeros (hurdle/two-part candidates): "
          f"{heavy_zero['variable'].tolist()}")
    return out


def main():
    tract = add_type_scale_measures(load_tract(), per_capita=True)
    bg = add_type_scale_measures(load_bg(), per_capita=False)

    pennsuco_check(tract)
    flagged_check(tract)

    moran_section(tract, "tract")
    moran_section(bg, "bg")

    type_cols_t = [f"type_{t}_share" for t in ["blue", "gray", "green", "hybrid"]] \
        + [f"investment_type_{t}" for t in ["blue", "gray", "green", "hybrid"]]
    path_cols_t = [f"path_{p}_amt" for p in ["single_unit", "municipality", "county"]]
    zero_skew_profile(tract, "tract", type_cols_t, path_cols_t)
    zero_skew_profile(bg, "bg", type_cols_t, path_cols_t)


if __name__ == "__main__":
    main()
