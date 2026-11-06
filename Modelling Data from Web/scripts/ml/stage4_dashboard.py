"""Stage 4, Part B data: both models for the unified admin Scenario screen.

    bash scripts/ml/run_ml.sh scripts/ml/stage4_dashboard.py      (after stage4_run.py and scenarios.py)

Writes outputs/ml/dashboard/models.json and compare.json, in the tract order of
outputs/ml/dashboard/tracts.json, plus two tables for decisions:
  outputs/ml/stage4/dollar_interval_widths.csv   (D-105; no dollars go to the dashboard)
  outputs/ml/stage4/cost_per_resident_by_type.csv (D-107)

Models (D-104, D-109)
  machine learning: the Stage 2/3 setup. The likelihood is the logistic map model's spatial
      out-of-fold, Venn-ABERS calibrated probability; a scenario adds the monotone XGBoost
      scenario model's change.
  Bayesian: Model 1, Part 1. The likelihood is the spatial out-of-fold posterior from the
      Stage 4 cross-validation fits (each tract predicted by the fit that did not see its
      fold), so it is comparable with the machine learning map. A scenario changes the
      sea level rise and surge inputs, and their vulnerability interactions, draw by draw,
      with the fold's own standardization; city and neighbourhood effects stay as they are.
      Mean and 90% interval (5th to 95th percentile of the posterior).
  Heat scenarios change need and the gap only, for both models (D-093).
Need and the primary gap do not depend on the model. The page recomputes them for any
combination of levels from the per-family percentile arrays written here, with the same
average-rank convention as scenarios.py.
"""
import itertools
import json

import joblib
import numpy as np
import pandas as pd
from scipy.special import expit
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score

import ml_common as C
import stage4_models as M
from scenarios import SCENARIOS, pct_vs

S4 = C.paths.OUT_ML / "stage4"
FITS = S4 / "fits"
SEED = C.SEED
C2 = (16 * np.sqrt(3) / (15 * np.pi)) ** 2
SLR = {f"slr_{k}ft": f"slr_{k}ft_pop_share" for k in (1, 2, 3, 6)}
SURGE = {f"surge_cat{c}": (f"surge_cat{c}_any_pop_share" if c < 5 else "surge_cat5max_any_pop_share") for c in range(1, 6)}
HEAT = {"heat_current": 0.0, "heat_plus1f": 1.0, "heat_plus2f": 2.0, "heat_plus3f": 3.0}
EXPOSED = {s["id"]: s["exposed"] for s in SCENARIOS}
PRESETS = [
    {"id": "current", "label": "Current baseline", "slr": "slr_3ft", "surge": "surge_cat3", "heat": "heat_current",
     "note": "The levels the models were trained on: 3 ft sea level rise, Category 3 surge, current surface heat."},
    {"id": "median", "label": "Professor's median", "slr": "slr_3ft", "surge": "surge_cat4", "heat": "heat_plus2f",
     "note": "3 ft sea level rise, Category 4 surge, +2°F (illustrative) surface heat."},
    {"id": "lower", "label": "Lower", "slr": "slr_1ft", "surge": "surge_cat1", "heat": "heat_current",
     "note": "1 ft sea level rise, Category 1 surge, current surface heat."},
    {"id": "higher", "label": "Higher", "slr": "slr_6ft", "surge": "surge_cat5", "heat": "heat_plus3f",
     "note": "6 ft sea level rise, Category 5 surge (corrected), +3°F (illustrative) surface heat."},
]


def r4(a):
    return [None if (v is None or np.isnan(v)) else round(float(v), 4) for v in np.asarray(a, dtype=float)]


def rx(a):
    return [None if np.isnan(v) else float(v) for v in np.asarray(a, dtype=float)]


def scores(y, p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return {"roc_auc": roc_auc_score(y, p), "pr_auc": average_precision_score(y, p), "log_loss": log_loss(y, p),
            "brier": brier_score_loss(y, p)}


def boot(y, a, b, n=2000):
    rng = np.random.default_rng(SEED)
    out = np.empty((n, 4))
    for k in range(n):
        i = rng.integers(0, len(y), len(y))
        sa, sb = scores(y[i], a[i]), scores(y[i], b[i])
        out[k] = [sa[m] - sb[m] for m in ("roc_auc", "pr_auc", "log_loss", "brier")]
    lo, hi = np.percentile(out, [2.5, 97.5], axis=0)
    return {m: [float(lo[j]), float(hi[j])] for j, m in enumerate(("roc_auc", "pr_auc", "log_loss", "brier"))}


def main():
    t = C.load_table().set_index("GEOID")
    dash = json.loads((C.DASH / "tracts.json").read_text())
    order = [r["GEOID"] for r in dash]
    t = t.loc[order]
    tp = pd.read_csv(C.STAGE2 / "tract_predictions.csv", dtype={"GEOID": str}).set_index("GEOID").loc[order]
    n = len(order)
    d = M.load_data()
    tr = d["tr"]
    gi = {g: k for k, g in enumerate(tr.GEOID)}            # training index of each dashboard tract
    tix = np.array([gi.get(g, -1) for g in order])
    bundle = joblib.load(C.STAGE2 / "model_scenario.joblib")
    xm, feats, lo, hi = bundle["model"], bundle["features"], bundle["train_min"], bundle["train_max"]

    # ---------------- need inputs: per-family percentile arrays ----------------
    base = {f: t[f].to_numpy(dtype=float) for f in C.HAZ_MAIN}
    fam_pct, extrap, exposed = {}, {}, {}
    for sid, col in SLR.items():
        v = t[col].to_numpy(dtype=float)
        fam_pct[sid] = pct_vs(base["slr_3ft_pop_share"], v)
        extrap[sid] = (v > hi["slr_3ft_pop_share"] + 1e-12) | (v < lo["slr_3ft_pop_share"] - 1e-12)
    for sid, col in SURGE.items():
        v = t[col].to_numpy(dtype=float)
        fam_pct[sid] = pct_vs(base["surge_cat3_any_pop_share"], v)
        extrap[sid] = (v > hi["surge_cat3_any_pop_share"] + 1e-12) | (v < lo["surge_cat3_any_pop_share"] - 1e-12)
    h = "heat_lst_popwt_mean_f"
    for sid, dlt in HEAT.items():
        v = base[h] + dlt
        fam_pct[sid] = pct_vs(base[h], v)
        extrap[sid] = (v > hi[h] + 1e-12) | (v < lo[h] - 1e-12)
    ex = pd.read_csv(C.paths.EXPOSURE_DIR / "exposure_tract.csv", dtype={"GEOID": str}).set_index("GEOID").loc[order]
    for sid in list(SLR) + list(SURGE) + list(HEAT):
        col = EXPOSED[sid]
        exposed[sid] = float(np.nansum(ex[col])) if col in ex else None
    base_expo = np.nanmean(np.column_stack([fam_pct["slr_3ft"], fam_pct["surge_cat3"], fam_pct["heat_current"]]), axis=1)
    vul_pct = tp.vulnerability_rc1.rank(pct=True).to_numpy()
    base_need = pct_vs(base_expo, base_expo) * vul_pct
    # check: the current baseline reproduces tracts.json
    need_pct0 = pct_vs(base_need, base_need)
    assert np.allclose(np.nan_to_num(need_pct0, nan=-1), np.nan_to_num(tp.need_pct.to_numpy(), nan=-1)), "need mismatch"

    def need_for(a, b, c):
        expo = np.nanmean(np.column_stack([fam_pct[a], fam_pct[b], fam_pct[c]]), axis=1)
        return pct_vs(base_need, pct_vs(base_expo, expo) * vul_pct)

    preset_check = []
    for p in PRESETS:
        npct = need_for(p["slr"], p["surge"], p["heat"])
        flag = (npct >= 0.75) & (t.T1.to_numpy() == 0)
        preset_check.append({"preset": p["label"], "high_need_no_sited_project": int(flag.sum()),
                             "residents": float(t.population.to_numpy()[flag].sum()),
                             "tracts_gap_over_0.5": int(np.nansum((npct - tp.sited_pct.to_numpy()) >= 0.5))})
    print(pd.DataFrame(preset_check).to_string(index=False))

    # ---------------- machine learning: monotone XGBoost changes per (slr, surge) ----------------
    X0 = t[feats].copy()
    p0 = xm.predict_proba(X0)[:, 1]
    ml_change = {}
    for a, b in itertools.product(SLR, SURGE):
        X = X0.copy()
        X["slr_3ft_pop_share"] = t[SLR[a]].to_numpy()
        X["surge_cat3_any_pop_share"] = t[SURGE[b]].to_numpy()
        ml_change[f"{a}|{b}"] = xm.predict_proba(X)[:, 1] - p0

    # ---------------- Bayesian: spatial out-of-fold posterior, with scenario shifts ----------------
    names = list(M.design(d["raw"], np.arange(len(tr)))[0].columns)
    hz = ["slr_3ft_pop_share", "surge_cat3_any_pop_share"]
    bay = {k: {"mean": np.full(n, np.nan), "lo": np.full(n, np.nan), "hi": np.full(n, np.nan)}
           for k in ml_change}
    oof_draws_ok = np.zeros(n, bool)
    folds = d["folds"]
    for f in np.unique(folds):
        z = np.load(FITS / f"cv_m1_part1_f{int(f)}.npz")
        trn = np.flatnonzero(folds != f)
        tst = np.flatnonzero(folds == f)
        mu = d["raw"].iloc[trn].mean()
        sd = d["raw"].iloc[trn].std(ddof=0).replace(0, 1)
        eta = z["eta"].reshape(-1, len(tr))[:, tst]
        # the interval averages over the tract's own unexplained effect (theta), which for an unseen tract is
        # a draw from its prior; it keeps parameter and neighbourhood uncertainty (D-109)
        eta_nt = eta - z["bunstruct_sp_1"].reshape(-1, len(tr))[:, tst]
        vth = (z["sigma_sp_1"].reshape(-1, 1) ** 2) * (1 - z["rho_sp_1"].reshape(-1, 1))
        shrink = 1.0 / np.sqrt(1.0 + C2 * vth)
        beta = z["beta_1"].reshape(-1, len(names))
        zv = ((d["raw"]["vulnerability"].iloc[tst] - mu["vulnerability"]) / sd["vulnerability"]).to_numpy()
        pos = [order.index(g) for g in tr.GEOID.iloc[tst]]
        for a, b in itertools.product(SLR, SURGE):
            new = {"slr_3ft_pop_share": tr[SLR[a]].iloc[tst].to_numpy(), "surge_cat3_any_pop_share": tr[SURGE[b]].iloc[tst].to_numpy()}
            de = np.zeros_like(eta)
            for hname in hz:
                dz = (new[hname] - d["raw"][hname].iloc[tst].to_numpy()) / sd[hname]
                dz = np.nan_to_num(dz)
                de += beta[:, [names.index(hname)]] * dz + beta[:, [names.index(f"{hname}:vulnerability")]] * (dz * zv)
            k = f"{a}|{b}"
            bay[k]["mean"][pos] = expit(eta + de).mean(0)
            pm = expit((eta_nt + de) * shrink)
            bay[k]["lo"][pos] = np.percentile(pm, 5, axis=0)
            bay[k]["hi"][pos] = np.percentile(pm, 95, axis=0)
        oof_draws_ok[pos] = True
    cur = bay["slr_3ft|surge_cat3"]
    assert oof_draws_ok.sum() == len(tr)
    oof = pd.read_csv(S4 / "spatial_cv_oof.csv", dtype={"GEOID": str}).set_index("GEOID")
    chk = oof.loc[[g for g in order if g in gi], "oof_m1_part1"].to_numpy()
    assert np.allclose(chk, cur["mean"][tix >= 0], atol=1e-9), "Bayesian current must equal the CV out-of-fold mean"

    # ---------------- Bayesian per-tract drivers and effects (full fit) ----------------
    X, _ = M.design(d["raw"], np.arange(len(tr)))
    post = np.load(FITS / "m1_part1.npz")
    bbar = post["beta_1"].reshape(-1, len(names)).mean(0)
    contrib = X.to_numpy() * bbar
    eff = pd.read_csv(S4 / "tract_effects.csv", dtype={"GEOID": str}).set_index("GEOID")

    def plain(nm):
        return f"{C.plain(nm.split(':')[0])} × vulnerability" if ":" in nm else C.plain(nm)

    drivers = []
    for g in order:
        if g not in gi:
            drivers.append([None, None, None])
            continue
        c = contrib[gi[g]]
        top = np.argsort(-np.abs(c))[:3]
        drivers.append([f"{plain(names[j])} ({'raises' if c[j] > 0 else 'lowers'})" for j in top])
    fe = pd.read_csv(S4 / "fixed_effects.csv")
    p1 = fe[fe.part == "Part 1"].set_index("feature")
    mac = np.abs(contrib).mean(0)
    bdrv = pd.DataFrame({"feature": names, "plain": [plain(x) for x in names], "mean_abs_contribution": mac,
                         "odds_ratio": p1.loc[names, "marginal_or"].to_numpy(),
                         "or_lo": p1.loc[names, "marginal_or_95lo"].to_numpy(),
                         "or_hi": p1.loc[names, "marginal_or_95hi"].to_numpy()}).sort_values("mean_abs_contribution",
                                                                                              ascending=False)
    ldrv = pd.read_csv(C.STAGE2 / "logistic_drivers_global.csv").sort_values("mean_abs_contribution", ascending=False)

    # ---------------- models.json ----------------
    ml_pred = tp.pred_likelihood.to_numpy()
    diff = cur["mean"] - ml_pred
    models = {
        "order": order,
        "levels": {"slr": [[k, f"{k.split('_')[1][:-2]} ft"] for k in SLR],
                   "surge": [[k, f"Cat {k[-1]}"] for k in SURGE],
                   "heat": [["heat_current", "Now"], ["heat_plus1f", "+1°F"], ["heat_plus2f", "+2°F"], ["heat_plus3f", "+3°F"]]},
        "presets": PRESETS,
        # full precision: need is a rank, and rounding would move tracts across the 0.75 cut
        "need": {"family_pct": {k: rx(v) for k, v in fam_pct.items()}, "base_expo": rx(base_expo),
                 "base_need": rx(base_need), "vul_pct": rx(vul_pct), "sited_pct": rx(tp.sited_pct.to_numpy())},
        "extrapolated": {k: [int(i) for i in np.flatnonzero(v)] for k, v in extrap.items()},
        "exposed": exposed,
        "ml": {"current": r4(ml_pred), "lo": r4(tp.interval_lo.to_numpy()), "hi": r4(tp.interval_hi.to_numpy()),
               "change": {k: r4(v) for k, v in ml_change.items()}, "drivers": tp[["driver1", "driver2", "driver3"]].values.tolist()},
        "bayes": {k: {"mean": r4(v["mean"]), "lo": r4(v["lo"]), "hi": r4(v["hi"])} for k, v in bay.items()},
        "bayes_drivers": drivers,
        "bayes_effects": {"city": r4([eff.city_effect.get(g, np.nan) for g in order]),
                          "neighbourhood": r4([eff.neighbourhood_effect.get(g, np.nan) for g in order])},
        "diff_current": r4(diff),
    }
    (C.DASH / "models.json").write_text(json.dumps(models, separators=(",", ":"), ensure_ascii=False))

    # ---------------- compare.json ----------------
    y = tr.T1.to_numpy()
    shown_ml = tp.pred_likelihood.loc[tr.GEOID].to_numpy()
    cvs = pd.read_csv(S4 / "spatial_cv_scores.csv").set_index("model")
    rows = [{"model": "Bayesian Model 1 (city + BYM2)", "key": "bayes", **scores(y, oof.loc[tr.GEOID, "oof_m1_part1"].to_numpy())},
            {"model": "Bayesian Model 0c (BYM2, no city), comparison", "key": "m0c",
             **scores(y, oof.loc[tr.GEOID, "oof_m0c_part1"].to_numpy())},
            {"model": "Machine learning: logistic, as shown on the map (Venn-ABERS calibrated)", "key": "ml_shown",
             **scores(y, shown_ml)},
            {"model": "Machine learning: logistic, uncalibrated", "key": "logistic", **scores(y, oof.loc[tr.GEOID, "oof_logistic"].to_numpy())},
            {"model": "Machine learning: XGBoost", "key": "xgb", **scores(y, oof.loc[tr.GEOID, "oof_xgb"].to_numpy())}]
    bm = oof.loc[tr.GEOID, "oof_m1_part1"].to_numpy()
    diffs = [{"comparison": "Bayesian minus machine learning (as shown)", **boot(y, bm, shown_ml)},
             {"comparison": "Bayesian minus logistic (uncalibrated)", **boot(y, bm, oof.loc[tr.GEOID, "oof_logistic"].to_numpy())},
             {"comparison": "Bayesian minus XGBoost", **boot(y, bm, oof.loc[tr.GEOID, "oof_xgb"].to_numpy())}]
    for r in diffs:
        k = {"Bayesian minus machine learning (as shown)": "ml_shown", "Bayesian minus logistic (uncalibrated)": "logistic",
             "Bayesian minus XGBoost": "xgb"}[r["comparison"]]
        a, b = rows[0], next(x for x in rows if x["key"] == k)
        r["point"] = {m: a[m] - b[m] for m in ("roc_auc", "pr_auc", "log_loss", "brier")}
    mi = pd.read_csv(S4 / "residual_moran.csv")
    moran = {"bayes": float(mi[(mi.model == "m1_part1") & (mi.residuals == "spatial out-of-fold")].I.iloc[0]),
             "logistic": float(mi[(mi.model == "logistic") & (mi.residuals == "spatial out-of-fold")].I.iloc[0]),
             "xgb": 0.132}
    dis = pd.DataFrame({"GEOID": order, "jurisdiction": tp.jurisdiction.to_numpy(), "bayes": cur["mean"], "ml": ml_pred,
                        "diff": diff, "observed": tp.T1_observed.to_numpy(), "i": np.arange(n)}).dropna(subset=["diff"])
    dis = dis.reindex(dis["diff"].abs().sort_values(ascending=False).index).head(12)
    city = pd.read_csv(S4 / "city_effects.csv").sort_values("effect_mean", ascending=False)
    heat = pd.read_csv(S4 / "heat_gap_after_controls.csv")
    compare = {
        "cv": rows, "cv_diffs": diffs, "moran": moran,
        "cv_note": ("Same 10 spatial folds as Stage 2: each area is predicted by a model that never saw it. "
                    "Intervals are paired bootstraps over tracts (2,000 resamples, seed 12086)."),
        "disagree": [{k: (round(float(v), 4) if isinstance(v, (float, np.floating)) else (int(v) if isinstance(v, (np.integer,)) else v))
                      for k, v in r.items()} for r in dis.to_dict("records")],
        "drivers_ml": [{"plain": r.plain, "coefficient": round(float(r.coefficient), 3),
                        "mean_abs_contribution": round(float(r.mean_abs_contribution), 3)} for r in ldrv.head(8).itertuples()],
        "drivers_bayes": [{"plain": r.plain, "odds_ratio": round(float(r.odds_ratio), 2), "or_lo": round(float(r.or_lo), 2),
                           "or_hi": round(float(r.or_hi), 2), "mean_abs_contribution": round(float(r.mean_abs_contribution), 3)}
                          for r in bdrv.head(8).itertuples()],
        "city": [{"jurisdiction": r.jurisdiction, "tracts": int(r.tracts), "mean": round(float(r.effect_mean), 3),
                  "lo": round(float(r.effect_95lo), 3), "hi": round(float(r.effect_95hi), 3)} for r in city.itertuples()],
        "heat": [{"model": r.model, "part": r.part, "effect": round(float(r.effect_mean), 3), "lo": round(float(r.effect_95lo), 3),
                  "hi": round(float(r.effect_95hi), 3), "unit": r.effect_unit} for r in heat.itertuples()],
        "heat_terciles": pd.read_csv(S4 / "heat_terciles.csv").to_dict("records"),
    }
    (C.DASH / "compare.json").write_text(json.dumps(compare, indent=1, ensure_ascii=False))
    print(pd.DataFrame(rows).drop(columns="key").to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    for r in diffs:
        print(r["comparison"], {m: f"{r['point'][m]:+.3f} [{r[m][0]:+.3f}, {r[m][1]:+.3f}]" for m in ("roc_auc", "pr_auc", "log_loss", "brier")})
    print("largest disagreements:\n", dis.drop(columns="i").to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print("Bayesian 90% interval width (current): median", np.nanmedian(cur["hi"] - cur["lo"]).round(3),
          "; machine learning Venn-ABERS width: median", np.nanmedian(tp.interval_hi - tp.interval_lo).round(3))

    # ---------------- D-105: dollar interval widths (not for the dashboard) ----------------
    z2 = np.load(FITS / "m1_part2_lognormal.npz")
    mu = z2["mu_log"].reshape(-1, len(tr))
    sg = z2["sigma_y"].reshape(-1)
    rng = np.random.default_rng(SEED)
    ypred = np.exp(mu + sg[:, None] * rng.standard_normal(mu.shape))
    q = np.percentile(ypred, [5, 50, 95], axis=0)
    typ = np.percentile(np.exp(mu), [5, 50, 95], axis=0)
    posm = y == 1
    wrows = []
    for label, m in (("tracts with a sited project (395)", posm), ("all training tracts (697)", np.ones(len(tr), bool))):
        wrows.append({"tracts": label,
                      "predictive_90_width_median_$": float(np.median((q[2] - q[0])[m])),
                      "predictive_90_low_median_$": float(np.median(q[0][m])), "predictive_90_high_median_$": float(np.median(q[2][m])),
                      "predictive_ratio_high_to_low_median": float(np.median((q[2] / q[0])[m])),
                      "typical_amount_90_width_median_$": float(np.median((typ[2] - typ[0])[m])),
                      "typical_amount_median_$": float(np.median(typ[1][m])),
                      "typical_amount_ratio_high_to_low_median": float(np.median((typ[2] / typ[0])[m]))})
    W = pd.DataFrame(wrows)
    print(W.T.to_string())
    W.to_csv(S4 / "dollar_interval_widths.csv", index=False)

    # ---------------- D-107: typical sited cost per resident, by project type ----------------
    pj = pd.read_csv(C.STAGE1 / "model_table_projects_T4.csv", dtype={"tract_GEOID": str})
    pj = pj[pj.tract_GEOID.isin(tr.GEOID)]
    popm = tr.set_index("GEOID").population
    crow = []
    for ty in ("Gray", "Green", "Blue", "Hybrid"):
        s = pj[pj.Infrastructure_Type == ty]
        sc = s[s.cost.notna() & (s.cost > 0)]
        per_tract = sc.groupby("tract_GEOID").cost.sum() / popm.loc[sc.tract_GEOID.unique()]
        crow.append({"type": ty, "projects": int(len(s)), "projects_with_cost": int(len(sc)),
                     "tracts": int(s.tract_GEOID.nunique()),
                     "median_dollars_per_resident": float(per_tract.median()),
                     "p25": float(per_tract.quantile(0.25)), "p75": float(per_tract.quantile(0.75)),
                     "few_projects_flag": ty in ("Green", "Blue")})
    allpos = tr.sited_dollars[tr.T1 == 1] / tr.population[tr.T1 == 1]
    crow.append({"type": "All types (current tool default)", "projects": int(len(pj)),
                 "projects_with_cost": int((pj.cost > 0).sum()), "tracts": int((tr.T1 == 1).sum()),
                 "median_dollars_per_resident": float(allpos.median()), "p25": float(allpos.quantile(0.25)),
                 "p75": float(allpos.quantile(0.75)), "few_projects_flag": False})
    CT = pd.DataFrame(crow)
    print(CT.to_string(index=False, float_format=lambda v: f"{v:,.0f}"))
    CT.to_csv(S4 / "cost_per_resident_by_type.csv", index=False)
    compare["cost_by_type"] = CT.to_dict("records")
    compare["preset_check"] = preset_check
    t4 = S4 / "t4_multiclass_per_class.csv"
    if t4.exists():
        compare["t4_multiclass"] = pd.read_csv(t4).fillna("").to_dict("records")
    (C.DASH / "compare.json").write_text(json.dumps(compare, indent=1, ensure_ascii=False))
    print("wrote", C.DASH / "models.json", C.DASH / "compare.json")


if __name__ == "__main__":
    main()
