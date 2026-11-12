"""Stage 3: XGBoost comparison for the property value model (prompt 27, D-154).

    bash scripts/ml/run_ml.sh scripts/benefit/stage3_xgb.py   (run_ml.sh and .venv-ml are in the main checkout)

Same features and the same 10 spatial folds as the OLS model
(stage3_models.py). Reports out-of-fold R2 and error, residual Moran's I,
and the average predicted change in price when a sale is moved into each
project distance band (all else equal), with the spread across the 10
fold models as the range. Writes outputs/benefit/stage3/xgb_summary.json.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from esda.moran import Moran
from libpysal.weights import KNN

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
from stage3_common import ACCESS, BG, HAZARD, PROJ_CHECK, PROJ_MAIN, TYPES, features, structure_cols  # noqa: E402

OUT = paths.OUT_BENEFIT / "stage3"
SEED = 20261111
PARAMS = dict(n_estimators=600, learning_rate=0.05, max_depth=6, subsample=0.8, colsample_bytree=0.8,
              min_child_weight=5, reg_lambda=1.0, random_state=SEED, n_jobs=4, tree_method="hist")


def morans_i(d, resid, k=8):
    g = pd.DataFrame({"x": d.x.round(0), "y": d.y.round(0), "r": resid}).groupby(["x", "y"]).r.mean().reset_index()
    w = KNN.from_array(g[["x", "y"]].to_numpy(), k=k)
    w.transform = "r"
    np.random.seed(SEED)
    m = Moran(g.r.to_numpy(), w, permutations=199)
    return {"I": round(float(m.I), 3), "p_sim": float(m.p_sim), "locations": len(g)}


def main():
    s = features(pd.read_csv(paths.SALES_FEATURES_CSV, dtype={"GEOID_tract": str, "GEOID_bg": str, "PARCEL_ID": str}))
    S = {"params": PARAMS, "xgboost": xgb.__version__}
    for seg in ["single_family", "condo"]:
        d = s[s.segment == seg].copy()
        st = structure_cols(seg)
        cols = st + BG + ACCESS + HAZARD + PROJ_MAIN + PROJ_CHECK
        d = d.dropna(subset=cols + ["log_price"])
        d["month_index"] = (d.sale_year - 2025) * 12 + d.sale_month
        X = d[cols + ["month_index"]].astype(float)
        y = d.log_price.to_numpy()
        pred = np.full(len(d), np.nan)
        shifts = {f"{band}_{t}": [] for t in TYPES for band in ("near500", "band1k")}
        for f in sorted(d.fold_spatial.unique()):
            tr = (d.fold_spatial != f).to_numpy()
            m = xgb.XGBRegressor(**PARAMS).fit(X[tr], y[tr])
            pred[~tr] = m.predict(X[~tr])
            # average effect of moving every held-out sale into a band of each type (the other band set to 0),
            # with the matching distance, count and dollar features set to typical values for that band
            Xte = X[~tr]
            base = m.predict(Xte)
            for t in TYPES:
                for band, dist in (("near500", 300.0), ("band1k", 750.0)):
                    Z = Xte.copy()
                    Z[f"near500_{t}"] = 1.0 if band == "near500" else 0.0
                    Z[f"band1k_{t}"] = 1.0 if band == "band1k" else 0.0
                    Z[f"log_dist_{t}"] = np.log(dist)
                    Z[f"n500_{t}"] = np.maximum(Z[f"n500_{t}"], 1.0 if band == "near500" else 0.0)
                    shifts[f"{band}_{t}"].append(float(np.mean(np.exp(m.predict(Z) - base)) - 1) * 100)
        e = y - pred
        S[seg] = {
            "sales": len(d),
            "spatial_cv": {"r2": round(float(1 - (e ** 2).sum() / ((y - y.mean()) ** 2).sum()), 3),
                           "rmse_log": round(float(np.sqrt((e ** 2).mean())), 3),
                           "median_abs_pct_error": round(float(np.median(np.abs(np.exp(e) - 1)) * 100), 1)},
            "moran_residual_out_of_fold": morans_i(d, e),
            "project_band_effect_pct": {k: {"mean": round(float(np.mean(v)), 2), "min_fold": round(float(np.min(v)), 2),
                                            "max_fold": round(float(np.max(v)), 2)} for k, v in shifts.items()}}
        print(seg, json.dumps(S[seg]["spatial_cv"]), flush=True)
    (OUT / "xgb_summary.json").write_text(json.dumps(S, indent=2))
    print(json.dumps(S, indent=1))


if __name__ == "__main__":
    main()
