"""Compare the two MGWR samples (prompt 27 Stage 3, D-153).

    ../.venv/bin/python -I scripts/benefit/stage3_mgwr_compare.py

Each sample is rebuilt exactly from its seed (stage3_mgwr.prepare and
sample), so local coefficients can be put back into price units and
the fitted values and residuals recomputed.

Stability checks between seeds 101 and 202:
- bandwidths per covariate;
- percent change in price per halving of distance to each project type
  (10th, 50th and 90th percentiles across locations). MGWR's own standard
  errors were not usable on these data (D-153), so no local significance
  is reported; stability across the two samples is the test;
- tract-by-tract agreement: Spearman correlation of the tract mean local
  coefficient, for tracts present in both samples;
- residual Moran's I (8 nearest neighbours).
Also how the project coefficients vary across the county, by Census place.
Writes outputs/benefit/stage3/mgwr_compare.json and mgwr_by_place.csv.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from esda.moran import Moran
from libpysal.weights import KNN
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
from stage3_mgwr import X_COLS, prepare, sample  # noqa: E402

OUT = paths.OUT_BENEFIT / "stage3"
SEEDS = [101, 202]
PROJ = ["log_dist_gray", "log_dist_hybrid", "log_dist_green"]


def main():
    s_all = prepare(pd.read_parquet(paths.SALES_FEATURES_PARQUET))
    pl = pd.read_csv(paths.OUT_BENEFIT / "stage2" / "tract_places.csv", dtype={"GEOID_tract": str}).set_index("GEOID_tract").place
    names = ["intercept"] + X_COLS
    R = {"bandwidths": {}, "fit": {}, "pct_per_halving": {}, "moran_residual": {}}
    pooled = []
    for seed in SEEDS:
        d = sample(s_all, seed)
        L = pd.read_csv(OUT / f"mgwr_seed{seed}.csv", dtype={"GEOID_tract": str, "PARCEL_ID": str})
        J = json.loads((OUT / f"mgwr_seed{seed}.json").read_text())
        assert (L.PARCEL_ID.to_numpy() == d.PARCEL_ID.to_numpy()).all(), "sample does not match the saved run"
        sd, mu = d[X_COLS].std(), d[X_COLS].mean()
        ysd, ymu = d.y_dm.std(), d.y_dm.mean()
        Xs = np.c_[np.ones(len(d)), ((d[X_COLS] - mu) / sd).to_numpy()]
        fitted = (L[names].to_numpy() * Xs).sum(1)
        ystd = ((d.y_dm - ymu) / ysd).to_numpy()
        resid = (ystd - fitted) * ysd                      # in log-price units
        g = pd.DataFrame({"x": d.x.round(0).to_numpy(), "y": d.y.round(0).to_numpy(), "r": resid}).groupby(["x", "y"]).r.mean().reset_index()
        w = KNN.from_array(g[["x", "y"]].to_numpy(), k=8)
        w.transform = "r"
        np.random.seed(20261111)
        m = Moran(g.r.to_numpy(), w, permutations=199)
        R["moran_residual"][seed] = {"I": round(float(m.I), 3), "p_sim": float(m.p_sim)}
        R["bandwidths"][seed] = J["bandwidths"]
        R["fit"][seed] = {"aicc": round(J["aicc"], 1), "r2": round(J["r2"], 3), "seconds": J["seconds"],
                          "sales": J["n"], "tracts": J["tracts"], "se_finite_share": J.get("se_finite_share"),
                          "min_bandwidth": J.get("min_bandwidth")}
        assert J.get("se_finite_share", 0) == 1.0, f"seed {seed}: standard errors not finite"
        L["seed"] = seed
        for n in PROJ:
            raw = L[n] * ysd / sd[n]                       # log-price change per unit of log distance
            L[f"pct_halving_{n}"] = (np.exp(-np.log(2) * raw) - 1) * 100
            R["pct_per_halving"].setdefault(n, {})[seed] = {
                "p10": round(float(L[f"pct_halving_{n}"].quantile(.1)), 2),
                "median": round(float(L[f"pct_halving_{n}"].median()), 2),
                "p90": round(float(L[f"pct_halving_{n}"].quantile(.9)), 2),
                "bandwidth": J["bandwidths"][n]}
        pooled.append(L)
    P = pd.concat(pooled)
    both = sorted(set(P[P.seed == 101].GEOID_tract) & set(P[P.seed == 202].GEOID_tract))
    R["tracts_in_both"] = len(both)
    agree = {}
    for n in names:
        a = P[P.seed == 101].groupby("GEOID_tract")[n].mean().reindex(both)
        b = P[P.seed == 202].groupby("GEOID_tract")[n].mean().reindex(both)
        agree[n] = round(float(spearmanr(a, b).statistic), 3) if a.std() > 1e-9 and b.std() > 1e-9 else "constant (global bandwidth)"
    R["tract_spearman_local_coef"] = agree
    P["place"] = P.GEOID_tract.map(pl).fillna("unincorporated")
    rows = []
    for n in PROJ:
        g = P.groupby("place").agg(sales=(f"pct_halving_{n}", "size"), median_pct_per_halving=(f"pct_halving_{n}", "median"))
        g = g[g.sales >= 40].sort_values("median_pct_per_halving")
        rows.append(g.assign(variable=n).reset_index())
    pd.concat(rows).round(3).to_csv(OUT / "mgwr_by_place.csv", index=False)
    (OUT / "mgwr_compare.json").write_text(json.dumps(R, indent=2, default=str))
    print(json.dumps(R, indent=1, default=str))


if __name__ == "__main__":
    main()
