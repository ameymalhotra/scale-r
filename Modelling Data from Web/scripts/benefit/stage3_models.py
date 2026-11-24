"""Stage 3: RAISE-style hedonic property value model, OLS part (prompt 27, D-149 to D-156).

    ../.venv/bin/python -I scripts/benefit/stage3_models.py

1. Baselines and OLS for single-family homes and condos, log sale price (main)
   and log just value (check), with spatial cross-validation (10 tract folds).
2. Residual Moran's I (8 nearest neighbours, one value per location).
3. Value of being near each project type (within 500 m, and 500 m to 1 km),
   in percent and dollars, with 95% intervals clustered by tract.
4. Bias checks: tract fixed effects and block group fixed effects
   (comparing properties within the same area). The before-and-after test is
   not possible: all sales are from 2025 and 2026.
5. FHFA tract index: did tracts with more projects see faster growth than
   similar tracts?
Writes outputs/benefit/stage3/ols_*.csv and ols_summary.json.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from esda.moran import Moran
from libpysal.weights import KNN

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import paths  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stage3_common import ACCESS, BG, HAZARD, PROJ_CHECK, PROJ_MAIN, TYPES, features, structure_cols  # noqa: E402

OUT = paths.OUT_BENEFIT / "stage3"
SEED = 20261111
MIN_NEAR = 300        # fewer sales within 500 m than this: too few to use (D-155)


def design(d, cols, fe=None):
    X = d[cols].astype(float)
    X = pd.concat([X, pd.get_dummies(d.ym, prefix="ym", drop_first=True, dtype=float)], axis=1)
    if fe:
        X = pd.concat([X, pd.get_dummies(d[fe], prefix=fe, drop_first=True, dtype=float)], axis=1)
    return sm.add_constant(X, has_constant="add")


def fit(d, y, cols, fe=None):
    X = design(d, cols, fe)
    X = X.loc[:, X.std() > 0].assign(const=1.0)
    groups = pd.factorize(d.GEOID_tract)[0]
    return sm.OLS(d[y], X).fit(cov_type="cluster", cov_kwds={"groups": groups})


def spatial_cv(d, y, specs):
    """Out-of-fold R2 and RMSE (log) by spatial fold, for nested specifications."""
    out = {}
    for name, cols in specs.items():
        pred = pd.Series(np.nan, index=d.index)
        for f in sorted(d.fold_spatial.unique()):
            tr, te = d[d.fold_spatial != f], d[d.fold_spatial == f]
            if cols is None:          # baseline: mean by month of sale
                m = tr.groupby("ym")[y].mean()
                pred[te.index] = te.ym.map(m).fillna(tr[y].mean()).to_numpy()
                continue
            Xtr = design(tr, cols)
            keep = Xtr.columns[Xtr.std() > 0].tolist() + ["const"]
            Xtr = Xtr[list(dict.fromkeys(keep))]
            b = np.linalg.lstsq(Xtr.to_numpy(), tr[y].to_numpy(), rcond=None)[0]
            Xte = design(te, cols).reindex(columns=Xtr.columns, fill_value=0.0)
            pred[te.index] = Xte.to_numpy() @ b
        e = d[y] - pred
        out[name] = {"r2": round(float(1 - (e ** 2).sum() / ((d[y] - d[y].mean()) ** 2).sum()), 3),
                     "rmse_log": round(float(np.sqrt((e ** 2).mean())), 3),
                     "median_abs_pct_error": round(float(np.median(np.abs(np.exp(e) - 1)) * 100), 1)}
    return out


def morans_i(d, resid, k=8):
    g = pd.DataFrame({"x": d.x.round(0), "y": d.y.round(0), "r": resid}).groupby(["x", "y"]).r.mean().reset_index()
    w = KNN.from_array(g[["x", "y"]].to_numpy(), k=k)
    w.transform = "r"
    np.random.seed(SEED)
    m = Moran(g.r.to_numpy(), w, permutations=199)
    return {"I": round(float(m.I), 3), "p_sim": float(m.p_sim), "locations": len(g)}


def effects(res, d, cols, label):
    med = float(d.sale_price.median())
    rows = []
    for c in cols:
        if c not in res.params:
            continue
        b, se = res.params[c], res.bse[c]
        lo, hi = b - 1.96 * se, b + 1.96 * se
        rows.append(dict(spec=label, variable=c, coef=b, se=se, pct=100 * (np.exp(b) - 1), pct_lo=100 * (np.exp(lo) - 1),
                         pct_hi=100 * (np.exp(hi) - 1), usd_at_median=med * (np.exp(b) - 1),
                         usd_lo=med * (np.exp(lo) - 1), usd_hi=med * (np.exp(hi) - 1), p=res.pvalues[c],
                         n_with=int((d[c] > 0).sum()) if c.startswith(("near500", "band1k")) else None,
                         median_price=med))
    return rows


def fhfa_check(S):
    h = pd.read_csv(paths.FHFA_DIR / "hpi_at_tract_miami_dade.csv", dtype={"tract": str})
    h["hpi"] = pd.to_numeric(h.hpi, errors="coerce")
    w = h.pivot_table(index="tract", columns="year", values="hpi")
    t = pd.DataFrame({"growth_2019_2024": w[2024] / w[2019] - 1, "pretrend_2014_2019": w[2019] / w[2014] - 1}).dropna()
    p = pd.read_csv(OUT / "projects_used.csv")
    import geopandas as gpd
    tr = gpd.read_file(f"zip://{paths.TRACT_2024_ZIP}")
    tr = tr[tr.COUNTYFP == "086"].to_crs(32617)[["GEOID", "geometry"]]
    pts = gpd.GeoDataFrame(p, geometry=gpd.points_from_xy(p.x, p.y), crs=32617)
    j = gpd.sjoin(pts, tr, predicate="within")
    cnt = j.groupby(["GEOID", "type"]).size().unstack(fill_value=0)
    cnt["all"] = cnt.sum(1)
    b = pd.read_parquet(paths.BUILDINGS_PARQUET, columns=["GEOID_tract", "fema_sfha", "lat", "lon"])
    bt = b.assign(sfha=b.fema_sfha.eq("T")).groupby("GEOID_tract").agg(sfha_share=("sfha", "mean"))
    bg = pd.read_csv(paths.ANALYSIS_DIR / "blockgroup_analysis.csv", dtype={"GEOID": str})
    inc = bg.assign(tract=bg.GEOID.str[:11]).groupby("tract").median_family_income.median()
    sf = pd.read_parquet(paths.SALES_FEATURES_PARQUET, columns=["GEOID_tract", "dist_coast_m"])
    coast = sf.groupby("GEOID_tract").dist_coast_m.median()
    t = t.join(cnt, how="left").fillna({c: 0 for c in cnt.columns}).join(bt).join(inc.rename("income")).join(coast.rename("coast"))
    t = t.dropna()
    t["log_income"] = np.log(t.income.clip(lower=5000))
    t["log_coast"] = np.log(t.coast.clip(lower=10))
    out = {"tracts": len(t)}
    for name, xs in [("all_projects", ["all"]), ("by_type", TYPES)]:
        X = t[[c for c in xs if c in t]].apply(np.log1p)
        X = sm.add_constant(pd.concat([X, t[["pretrend_2014_2019", "log_income", "log_coast", "sfha_share"]]], axis=1))
        r = sm.OLS(t.growth_2019_2024, X).fit(cov_type="HC1")
        out[name] = {c: {"coef": round(float(r.params[c]), 4), "ci95": [round(float(v), 4) for v in r.conf_int().loc[c]],
                         "p": round(float(r.pvalues[c]), 3)} for c in X.columns if c in xs}
        out[name]["r2"] = round(float(r.rsquared), 3)
    out["note"] = ("growth = FHFA tract index 2024 / 2019 - 1; controls: 2014-2019 growth, median family income, "
                   "distance to coast, share of buildings in the FEMA 100-year zone; project counts are log(1 + n)")
    out["median_growth"] = round(float(t.growth_2019_2024.median()), 3)
    S["fhfa"] = out


def main():
    s = features(pd.read_parquet(paths.SALES_FEATURES_PARQUET))
    S, eff_rows, cv_rows = {"rows": len(s)}, [], []
    for seg in ["single_family", "condo"]:
        d = s[s.segment == seg].copy()
        st = structure_cols(seg)
        d = d.dropna(subset=st + BG + ACCESS + HAZARD + PROJ_MAIN + PROJ_CHECK + ["log_price"])
        full = st + BG + ACCESS + HAZARD + PROJ_MAIN
        S[seg] = {"sales": len(d), "median_price": float(d.sale_price.median()), "tracts": int(d.GEOID_tract.nunique())}
        specs = {"baseline_month_mean": None, "structure": st, "structure_neighbourhood_access_hazard": st + BG + ACCESS + HAZARD,
                 "full_with_projects": full}
        cv = spatial_cv(d, "log_price", specs)
        S[seg]["spatial_cv"] = cv
        for k, v in cv.items():
            cv_rows.append(dict(segment=seg, outcome="log_price", spec=k, **v))
        # main fit and checks
        r_main = fit(d, "log_price", full)
        S[seg]["r2_in_sample"] = round(float(r_main.rsquared), 3)
        S[seg]["moran_residual"] = morans_i(d, r_main.resid.to_numpy())
        eff_rows += [dict(segment=seg, **e) for e in effects(r_main, d, PROJ_MAIN, "A: block group controls (main)")]
        r_tr = fit(d, "log_price", st + ACCESS + HAZARD + PROJ_MAIN, fe="GEOID_tract")
        eff_rows += [dict(segment=seg, **e) for e in effects(r_tr, d, PROJ_MAIN, "B: within the same tract")]
        S[seg]["moran_residual_tract_fe"] = morans_i(d, r_tr.resid.to_numpy())
        r_bg = fit(d, "log_price", st + ACCESS + HAZARD + PROJ_MAIN, fe="GEOID_bg")
        eff_rows += [dict(segment=seg, **e) for e in effects(r_bg, d, PROJ_MAIN, "C: within the same block group")]
        r_chk = fit(d, "log_price", st + BG + ACCESS + HAZARD + PROJ_CHECK)
        eff_rows += [dict(segment=seg, **e) for e in effects(r_chk, d, PROJ_CHECK, "D: distance, counts and dollars")]
        dj = d.dropna(subset=["log_jv"])
        r_jv = fit(dj, "log_jv", full)
        eff_rows += [dict(segment=seg, **e) for e in effects(r_jv, dj, PROJ_MAIN, "E: just value (check)")]
        cvj = spatial_cv(dj, "log_jv", {"full_with_projects": full})
        S[seg]["spatial_cv_just_value"] = cvj
        # other coefficients of interest (hazard and access), main spec
        S[seg]["other_coefficients"] = {c: {"coef": round(float(r_main.params[c]), 4), "se": round(float(r_main.bse[c]), 4)}
                                        for c in ACCESS + HAZARD + st}
        pd.DataFrame({"resid": r_main.resid, "fitted": r_main.fittedvalues}).to_csv(OUT / f"ols_resid_{seg}.csv")
        print(seg, "done", flush=True)
    eff = pd.DataFrame(eff_rows)
    # usable or too uncertain (D-155): an effect is "indicative" only if
    #   - at least MIN_NEAR sales fall in the distance band,
    #   - the main estimate and both within-area estimates (tract, block group) have the same sign,
    #   - at least two of those three 95% intervals exclude zero.
    # Otherwise it is "too uncertain to use".
    abc = eff[eff.spec.str[0].isin(["A", "B", "C"])]
    flags = []
    for (seg, var), g in abc.groupby(["segment", "variable"]):
        a = g[g.spec.str.startswith("A")].iloc[0]
        reasons = []
        if a.n_with is not None and a.n_with < MIN_NEAR:
            reasons.append(f"only {int(a.n_with)} sales in this distance band")
        if (np.sign(g.coef) != np.sign(a.coef)).any():
            reasons.append("sign changes when comparing within the same area")
        excl = int(((g.pct_lo > 0) | (g.pct_hi < 0)).sum())
        if excl < 2:
            reasons.append(f"{excl} of 3 intervals exclude zero")
        flags.append(dict(segment=seg, variable=var, usable=not reasons,
                          verdict="indicative" if not reasons else "too uncertain to use", reasons="; ".join(reasons),
                          pct_range_abc=f"{g.pct.min():.1f} to {g.pct.max():.1f}"))
    eff = eff.merge(pd.DataFrame(flags), on=["segment", "variable"], how="left")
    eff.round(5).to_csv(OUT / "ols_project_effects.csv", index=False)
    pd.DataFrame(cv_rows).to_csv(OUT / "ols_spatial_cv.csv", index=False)
    fhfa_check(S)
    (OUT / "ols_summary.json").write_text(json.dumps(S, indent=2, default=str))
    print(json.dumps(S, indent=1, default=str))
    show = eff[eff.variable.str.startswith(("near500", "band1k"))][["segment", "spec", "variable", "pct", "pct_lo", "pct_hi", "usd_at_median", "n_with", "verdict"]]
    print(show.round(2).to_string())


if __name__ == "__main__":
    main()
