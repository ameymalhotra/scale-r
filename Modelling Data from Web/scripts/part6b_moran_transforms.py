"""Part 6, Task 2: retest Moran's I on transformed dollar outcomes.

The original investment_per_capita Moran's I (I=0.006, p=0.070, "not
significant") was computed on a variable with skew 18.718 - Moran's I is a
variance-based statistic and a handful of extreme values can dominate it,
so the "no clustering" conclusion needs checking on less skew-dominated
transforms before it's trusted. Same k=6 KNN weights, same 698-tract sample,
as the original Part 5c run - this is a retest, not a new spatial analysis.

Transforms, per outcome:
  raw   - reproduces the original Part 5c number as the baseline
  log   - natural log. Zero/undefined handling: checked per outcome below;
          if no zeros/negatives exist, plain log(x) is used and that is
          stated explicitly (never silently defaulted to log1p or +epsilon).
  rank  - scipy.stats.rankdata, ranks 1..n. Moran's I is invariant to any
          positive affine transform of its input (it is computed from
          deviations-from-mean divided by variance), so an ordinary rank
          (not normalized to [0,1]) gives an identical I to a normalized
          rank - this is the most robust of the three per the request, since
          it depends only on order, not on the magnitude of the extremes.

Also retests type_green_share and type_hybrid_share (tract skew 4.319 and
3.688, both > 3) under the same three transforms.

Usage: python scripts/part6b_moran_transforms.py
Outputs: output/part6_followup/6b_moran_transforms.csv
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from esda.moran import Moran
from scipy.stats import rankdata

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analysis_variables import add_type_scale_measures, load_tract  # noqa: E402
from part5_diagnostics import K_NEIGHBORS, build_knn_weights  # noqa: E402
from scaler_projects import OUTPUT_DIR  # noqa: E402

OUT = OUTPUT_DIR / "part6_followup"
OUT.mkdir(exist_ok=True)
warnings.filterwarnings("ignore", category=RuntimeWarning)

OUTCOMES = ["investment_per_capita", "investment_total", "investment_per_area"]
TYPE_SHARES_TO_CHECK = ["type_green_share", "type_hybrid_share"]  # skew > 3


def transform(s, kind):
    if kind == "raw":
        return s, "none"
    if kind == "log":
        n_zero = int((s <= 0).sum())
        n_missing = int(s.isna().sum())
        if n_zero > 0:
            note = (f"{n_zero} values <=0 exist - log undefined for them, "
                    f"left as NaN (not log1p'd, not shifted by epsilon)")
            out = s.where(s > 0).apply(np.log)
        else:
            note = "no zeros/negatives present - plain log(x), n unchanged"
            out = np.log(s)
        return out, note
    if kind == "rank":
        valid = s.notna()
        out = pd.Series(np.nan, index=s.index)
        out[valid] = rankdata(s[valid])
        return out, "scipy.stats.rankdata, ranks 1..n (affine-equivalent to any [0,1] rank)"
    raise ValueError(kind)


def run_moran(df, geoid_col, varname, kind, w):
    s = df[varname]
    t, note = transform(s, kind)
    valid = t.notna() & np.isfinite(t)
    n = int(valid.sum())
    skew_after = t[valid].skew() if n > 2 else np.nan
    if n < 30:
        return {"variable": varname, "transform": kind, "n": n, "I": np.nan,
               "p_sim": np.nan, "z_sim": np.nan, "skew_after": skew_after,
               "note": note + " | too few valid values for Moran's I"}
    if n == len(df):
        m = Moran(t.values, w, permutations=999)
    else:
        sub_ids = df.loc[valid, geoid_col].tolist()
        sub_w = build_knn_weights(sub_ids, "tract")
        m = Moran(t[valid].values, sub_w, permutations=999)
    return {"variable": varname, "transform": kind, "n": n, "I": m.I,
           "p_sim": m.p_sim, "z_sim": m.z_sim, "skew_after": skew_after, "note": note}


def main():
    df = add_type_scale_measures(load_tract(), per_capita=True)
    np.random.seed(12086)  # pin the 999-permutation Monte Carlo draw
    w = build_knn_weights(df["GEOID"].tolist(), "tract")

    rows = []
    for outcome in OUTCOMES + TYPE_SHARES_TO_CHECK:
        for kind in ["raw", "log", "rank"]:
            np.random.seed(12086)
            rows.append(run_moran(df, "GEOID", outcome, kind, w))

    out = pd.DataFrame(rows)
    out.to_csv(OUT / "6b_moran_transforms.csv", index=False)
    print(out.to_string(index=False, float_format=lambda v: f"{v:.4f}" if isinstance(v, float) else str(v)))

    print("\n--- baseline reproduction check ---")
    base = out[(out["variable"] == "investment_per_capita") & (out["transform"] == "raw")].iloc[0]
    print(f"investment_per_capita raw: I={base.I:.4f}, p_sim={base.p_sim:.4f} "
          f"(original Part 5c run: I=0.0059, p_sim=0.0700)")

    print("\n--- does clustering appear after transform? ---")
    for outcome in OUTCOMES:
        sub = out[out["variable"] == outcome]
        sig = sub[sub.p_sim < 0.05]
        print(f"{outcome}: {len(sig)} of {len(sub)} transforms significant "
              f"(p_sim<0.05) -> {sig[['transform', 'I', 'p_sim']].to_dict('records')}")


if __name__ == "__main__":
    main()
