"""Standard hedonic model with block group fixed effects, flood rate as the key variable (D-191).

    /Users/.../Climate-Resilience---Miami-Dade/.venv/bin/python -I scripts/benefit/module_d_fe.py

All qualified 2025 to 2026 sales (sample "main", training and held-out together), separately for
single-family and condo. Log price on the specification's variables (as module_d_fit.py) plus one
dummy per block group, so the flood rate is compared only between homes in the same block group.
Flood rate: $100 of expected yearly damage per $100,000 of building value (D-184).
Reports the flood coefficient (% price change per unit) with standard errors clustered by block group
and, as a stricter check, by tract; the same with the frequent-storm rate; how much of the flood rate's
variation is within block groups; and the held-out error (fit on the training sales, predict the
held-out sales) for comparison with MGWR.
Writes outputs/benefit/module_d/fe_block_group.json.
"""
import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
from module_d_fit import XV, load  # noqa: E402


def design(d, xs):
    X = pd.concat([d[xs].astype(float), pd.get_dummies(d.GEOID_bg, prefix="bg", drop_first=True, dtype=float)], axis=1)
    return sm.add_constant(X)


def coef(m, name="FLOOD"):
    b, se = m.params[name], m.bse[name]
    return {"pct_per_unit": round(float((np.exp(b) - 1) * 100), 3), "t": round(float(b / se), 2),
            "p": round(float(m.pvalues[name]), 4),
            "ci95": [round(float((np.exp(b - 1.96 * se) - 1) * 100), 3), round(float((np.exp(b + 1.96 * se) - 1) * 100), 3)]}


def main():
    bg = gpd.read_file(f"zip://{paths.BOUNDARY_DIR / 'tl_2024_12_bg.zip'}")
    bg = bg[bg.COUNTYFP == "086"].to_crs(32617)[["GEOID", "geometry"]]
    R = {"unit": "% price change per $100 of yearly damage per $100,000 of building value"}
    for seg in ["single_family", "condo"]:
        s = load(seg)
        xs = XV[seg]
        d = s[s.sample_name == "main"].copy()
        d["FLOOD"] = d.flood_rate
        j = gpd.sjoin(gpd.GeoDataFrame(geometry=gpd.points_from_xy(d.x, d.y), crs=32617, index=d.index), bg,
                      predicate="within", how="left")
        d["GEOID_bg"] = j[~j.index.duplicated()].GEOID
        d = d.dropna(subset=xs + ["log_price", "flood_rate", "flood_freq_rate", "GEOID_bg", "GEOID_tract"])
        r = {"sales": int(len(d)), "block_groups": int(d.GEOID_bg.nunique())}
        fr = d.flood_rate
        r["flood_rate_share_of_variance_within_block_groups"] = round(
            float(((fr - d.groupby("GEOID_bg").flood_rate.transform("mean")) ** 2).sum() / ((fr - fr.mean()) ** 2).sum()), 3)
        r["sales_in_block_groups_with_flood_rate_variation"] = round(
            float(d.groupby("GEOID_bg").flood_rate.transform("std").fillna(0).gt(0).mean()), 3)
        for v, col in [("main", "flood_rate"), ("frequent", "flood_freq_rate")]:
            d["FLOOD"] = d[col]
            X = design(d, xs)
            y = d.log_price.to_numpy()
            r[v] = {"cluster_block_group": coef(sm.OLS(y, X).fit(cov_type="cluster",
                                                                 cov_kwds={"groups": pd.factorize(d.GEOID_bg)[0]})),
                    "cluster_tract": coef(sm.OLS(y, X).fit(cov_type="cluster",
                                                           cov_kwds={"groups": pd.factorize(d.GEOID_tract)[0]}))}
            if v == "main":
                r[v]["r2"] = round(float(sm.OLS(y, X).fit().rsquared), 3)
        # held-out error: fit on training sales, predict held-out sales in block groups seen in training
        d["FLOOD"] = d.flood_rate
        tr, te = d[~d.holdout], d[d.holdout]
        te = te[te.GEOID_bg.isin(set(tr.GEOID_bg))]
        cols = design(tr, xs).columns
        m = sm.OLS(tr.log_price.to_numpy(), design(tr, xs)).fit()
        Xte = design(te, xs).reindex(columns=cols, fill_value=0.0)
        Xte["const"] = 1.0
        e = np.abs(np.exp(te.log_price.to_numpy() - m.predict(Xte).to_numpy()) - 1) * 100
        r["holdout"] = {"sales": int(len(te)), "median_abs_pct_error": round(float(np.median(e)), 1),
                        "training_flood_pct_per_unit": coef(m)["pct_per_unit"]}
        R[seg] = r
    out = paths.OUT_BENEFIT / "module_d" / "fe_block_group.json"
    out.write_text(json.dumps(R, indent=2))
    print(json.dumps(R, indent=1))


if __name__ == "__main__":
    main()
