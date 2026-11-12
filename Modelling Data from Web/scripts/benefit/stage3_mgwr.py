"""Stage 3 MGWR on a sample of single-family sales (prompt 27, D-153).

    ../.venv/bin/python -I scripts/benefit/stage3_mgwr.py <sample_seed>

How the sample is drawn: 2,000 single-family sales, stratified by tract
(each tract contributes in proportion to its share of sales, at least one
where it has any), with a fixed seed. The script is run twice with two
different seeds to check the results are stable.

The outcome is log sale price with month-of-sale effects removed first
(demeaned by month). All variables are standardised, as MGWR requires.
Writes outputs/benefit/stage3/mgwr_seed<seed>.csv (local estimates) and
mgwr_seed<seed>.json (bandwidths and fit).
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from mgwr.gwr import MGWR
from mgwr.sel_bw import Sel_BW

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import paths  # noqa: E402

OUT = paths.OUT_BENEFIT / "stage3"
N = 2000
MIN_BW = 500
X_COLS = ["log_living_area", "log_lot", "age", "log_dist_coast", "ground_elev_ft",
          "log_dist_gray", "log_dist_hybrid", "log_dist_green"]
# Project proximity enters as log distance to the nearest project of each type (50 m to 5 km).
# Left out (D-153):
# - yes/no "within 500 m" flags and the flood-zone flag: too few treated sales per local window,
#   so local fits were singular;
# - blue projects: too few in a 2,000-sale sample;
# - distance to downtown and block group income: locally they move with the intercept and the
#   distance to the coast. With them, the median local condition number at 200 neighbours was 48
#   (61% of locations above 30) and the MGWR standard errors broke down in two full runs. Without
#   them, and with at least 500 neighbours, the median is 6.4 (2% above 30). The local intercept
#   absorbs neighbourhood price levels instead.


def prepare(s):
    s = s[s.segment == "single_family"].copy()
    s["log_dist_coast"] = np.log(s.dist_coast_m.clip(lower=10))
    s["log_dist_downtown"] = np.log(s.dist_downtown_m.clip(lower=100))
    s["log_income"] = np.log(s.median_family_income.clip(lower=5000))
    for t in ["gray", "hybrid", "green"]:
        s[f"log_dist_{t}"] = np.log(s[f"dist_{t}_m"].clip(50, 5000))
    s["y_dm"] = s.log_price - s.groupby("ym").log_price.transform("mean")
    return s.dropna(subset=X_COLS + ["y_dm"])


def sample(s, seed):
    rng = np.random.default_rng(seed)
    share = s.GEOID_tract.value_counts(normalize=True)
    take = np.maximum(1, np.round(share * N)).astype(int)
    idx = []
    for tr, k in take.items():
        rows = s.index[s.GEOID_tract == tr]
        idx.extend(rng.choice(rows, size=min(k, len(rows)), replace=False))
    idx = np.array(idx)
    if len(idx) > N:
        idx = rng.choice(idx, size=N, replace=False)
    return s.loc[np.sort(idx)]


def main():
    seed = int(sys.argv[1])
    s = prepare(pd.read_parquet(paths.SALES_FEATURES_PARQUET))
    d = sample(s, seed)
    coords = d[["x", "y"]].to_numpy() + np.random.default_rng(seed).normal(0, 0.5, (len(d), 2))  # split exact ties
    mu, sd = d[X_COLS].mean(), d[X_COLS].std()
    X = ((d[X_COLS] - mu) / sd).to_numpy()
    y = ((d.y_dm - d.y_dm.mean()) / d.y_dm.std()).to_numpy().reshape(-1, 1)
    t0 = time.time()
    sel = Sel_BW(coords, y, X, multi=True, constant=True)
    # minimum bandwidth of 500 neighbours (a quarter of the sample) keeps local fits well conditioned (D-153)
    bws = sel.search(multi_bw_min=[MIN_BW], verbose=False)
    res = MGWR(coords, y, X, sel, constant=True).fit()
    names = ["intercept"] + X_COLS
    loc = pd.DataFrame(res.params, columns=names)
    se = pd.DataFrame(res.bse, columns=[f"se_{n}" for n in names])
    tv = res.filter_tvals()            # corrected for multiple testing
    sig = pd.DataFrame(tv != 0, columns=[f"sig_{n}" for n in names])
    out = pd.concat([d[["PARCEL_ID", "GEOID_tract", "x", "y", "lon", "lat", "sale_price"]].reset_index(drop=True),
                     loc, se, sig], axis=1)
    out.to_csv(OUT / f"mgwr_seed{seed}.csv", index=False)
    # back to log-price units: beta_raw = beta_std * sd(y) / sd(x)
    ysd = float(d.y_dm.std())
    summ = {"seed": seed, "n": len(d), "tracts": int(d.GEOID_tract.nunique()), "seconds": round(time.time() - t0),
            "min_bandwidth": MIN_BW, "bandwidths": dict(zip(names, [float(b) for b in bws])),
            "se_finite_share": float(np.isfinite(res.bse).mean()), "aicc": float(res.aicc), "r2": float(res.R2),
            "local_coef_log_price_units": {}}
    for n in X_COLS:
        b = loc[n] * ysd / sd[n]
        summ["local_coef_log_price_units"][n] = {
            "p10": float(b.quantile(.1)), "median": float(b.median()), "p90": float(b.quantile(.9)),
            "share_significant": float(sig[f"sig_{n}"].mean())}
    (OUT / f"mgwr_seed{seed}.json").write_text(json.dumps(summ, indent=2))
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
