"""Stage 2b: choose the map model, switch the primary gap to actual investment, re-export.

    bash scripts/ml/run_ml.sh scripts/ml/stage2b_map_model.py     (from Modelling Data from Web/)

1. Map model (D-091): recompute the spatial out-of-fold T1 predictions for
   logistic regression and XGBoost (nested, as in stage2_models.py), add their
   simple average and, when TABPFN_TOKEN is set, TabPFN. A paired bootstrap of
   the tracts (2,000 resamples, seed 12086) gives 95% intervals for the
   differences in ROC-AUC, PR-AUC and log loss. The best model on spatial CV
   drives the map; if no interval excludes zero, logistic regression does,
   because it is simpler and more transparent. Monotone XGBoost stays the
   scenario model.
2. Drivers for the map: for logistic regression, each feature's contribution
   to the log-odds (coefficient x standardized value) from the final fit.
3. Gap (D-092): primary = need percentile minus the percentile of ACTUAL sited
   dollars per resident, plus a flag for high need (top quarter) with no sited
   project. Secondary = need versus expected investment (the model).
Writes outputs/ml/stage2/map_model_test.csv, tract_predictions.csv (replaced),
and outputs/ml/dashboard/tracts.json and scores.json.
"""
import json

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, log_loss, roc_auc_score

import ml_common as C
import stage2_models as S2

SEED = C.SEED
N_BOOT = 2000
HIGH_NEED = 0.75


def boot_diff(y, pa, pb, rng):
    n = len(y)
    out = np.empty((N_BOOT, 3))
    for b in range(N_BOOT):
        i = rng.integers(0, n, n)
        yy = y[i]
        if len(np.unique(yy)) < 2:
            out[b] = np.nan
            continue
        a, c = np.clip(pa[i], 1e-6, 1 - 1e-6), np.clip(pb[i], 1e-6, 1 - 1e-6)
        out[b] = [roc_auc_score(yy, a) - roc_auc_score(yy, c),
                  average_precision_score(yy, a) - average_precision_score(yy, c),
                  log_loss(yy, a, labels=[0, 1]) - log_loss(yy, c, labels=[0, 1])]
    lo, hi = np.nanpercentile(out, [2.5, 97.5], axis=0)
    return lo, hi


def main():
    np.random.seed(SEED)
    t = C.load_table()
    tm = C.train_mask(t)
    tr = t[tm].reset_index(drop=True)
    folds = tr.fold_spatial.to_numpy()
    y = tr.T1.to_numpy()
    preds, chosen = {}, {}
    for name in ("logistic", "xgb") + (("tabpfn",) if C.tabpfn_available() else ()):
        p, fid, ch = S2.nested_oof(tr[C.MAIN], y, "bin", name, "spatial", folds)
        preds[name], chosen[name] = p, ch
        print(f"{name}: ROC {roc_auc_score(y, p):.3f}", flush=True)
    preds["average (logistic + xgb)"] = (preds["logistic"] + preds["xgb"]) / 2
    rows = []
    for name, p in preds.items():
        rows.append({"model": name, **S2.bin_scores(y, p, folds)})
    res = pd.DataFrame(rows)
    if not C.tabpfn_available():
        res = pd.concat([res, pd.DataFrame([{"model": "tabpfn", "note": "not run: no TABPFN_TOKEN (D-082)"}])])
    rng = np.random.default_rng(SEED)
    comps = []
    for a, b in (("logistic", "xgb"), ("average (logistic + xgb)", "logistic"), ("average (logistic + xgb)", "xgb")) + \
            ((("tabpfn", "logistic"),) if "tabpfn" in preds else ()):
        lo, hi = boot_diff(y, preds[a], preds[b], rng)
        comps.append({"comparison": f"{a} minus {b}",
                      "roc_auc_diff": roc_auc_score(y, preds[a]) - roc_auc_score(y, preds[b]),
                      "roc_auc_95lo": lo[0], "roc_auc_95hi": hi[0],
                      "pr_auc_diff": average_precision_score(y, preds[a]) - average_precision_score(y, preds[b]),
                      "pr_auc_95lo": lo[1], "pr_auc_95hi": hi[1],
                      "log_loss_diff": log_loss(y, preds[a]) - log_loss(y, preds[b]),
                      "log_loss_95lo": lo[2], "log_loss_95hi": hi[2]})
    comp = pd.DataFrame(comps)
    comp["any_interval_excludes_0"] = ((comp.roc_auc_95lo > 0) | (comp.roc_auc_95hi < 0) | (comp.pr_auc_95lo > 0)
                                       | (comp.pr_auc_95hi < 0) | (comp.log_loss_95lo > 0) | (comp.log_loss_95hi < 0))
    pd.set_option("display.width", 250)
    print(res.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print(comp.to_string(index=False, float_format=lambda v: f"{v:+.4f}"))
    res.to_csv(C.STAGE2 / "map_model_scores.csv", index=False)
    comp.to_csv(C.STAGE2 / "map_model_test.csv", index=False)

    # decision rule (fixed before the run): best on spatial CV only if it is clearly better, else logistic
    sc = res.dropna(subset=["roc_auc"]).set_index("model")
    best = sc.sort_values(["pr_auc", "log_loss"], ascending=[False, True]).index[0]
    map_model = "logistic"
    if best != "logistic":
        row = comp[comp.comparison.isin([f"{best} minus logistic", f"logistic minus {best}"])]
        if len(row) and bool(row.any_interval_excludes_0.iloc[0]):
            sign = 1 if row.comparison.iloc[0].startswith(best) else -1
            clearly_better = (sign * row.pr_auc_95lo.iloc[0] > 0 if sign == 1 else row.pr_auc_95hi.iloc[0] < 0)
            if clearly_better:
                map_model = best
    print(f"best on spatial PR-AUC: {best}; map model: {map_model}")
    if map_model != "logistic":
        raise SystemExit("map model is not logistic regression; the logistic export below would not apply")

    # final logistic fit and per-tract log-odds contributions
    params = S2.mode_params(chosen["logistic"])
    m = S2.make("logistic", "bin", C.MAIN, y, params=params).fit(tr[C.MAIN], y)
    Xall = t[C.MAIN]
    Z = m.named_steps["sc"].transform(m.named_steps["imp"].transform(Xall))
    coef = m.named_steps["clf"].coef_[0]
    names = list(C.MAIN) + [f"missing_{c}" for c in np.array(C.MAIN)[m.named_steps["imp"].indicator_.features_]]
    contrib = Z * coef
    glob = pd.DataFrame({"feature": names, "coefficient": coef, "mean_abs_contribution": np.abs(contrib[tm]).mean(axis=0)})
    glob = glob[~glob.feature.str.startswith("missing_")].sort_values("mean_abs_contribution", ascending=False)
    glob["plain"] = glob.feature.map(C.plain)
    glob.to_csv(C.STAGE2 / "logistic_drivers_global.csv", index=False)
    print(glob.head(10).to_string(index=False, float_format=lambda v: f"{v:+.3f}"))
    local = []
    for i, gid in enumerate(t.GEOID):
        order = [j for j in np.argsort(-np.abs(contrib[i])) if not names[j].startswith("missing_")][:3]
        local.append({"GEOID": gid, **{f"driver{k + 1}": f"{C.plain(names[j])} ({'raises' if contrib[i, j] > 0 else 'lowers'})"
                                         for k, j in enumerate(order)}})
    local = pd.DataFrame(local)

    # Venn-ABERS interval for the logistic map predictions, inside the spatial folds
    conf, summary = S2.conformal_t1(tr[C.MAIN], y, folds, "logistic", params)
    print("conformal (logistic):", json.dumps({k: round(v, 4) for k, v in summary.items()}))

    tp = pd.read_csv(C.STAGE2 / "tract_predictions.csv", dtype={"GEOID": str}).set_index("GEOID").loc[t.GEOID].reset_index()
    tp = tp.drop(columns=["driver1", "driver2", "driver3", "gap"], errors="ignore")
    final_p = m.predict_proba(Xall)[:, 1]
    pred = final_p.copy()
    pred[np.flatnonzero(tm)] = conf.va_p.astype(float).values
    tp["pred_likelihood"] = pred
    tp["pred_source"] = np.where(tm, "spatial out-of-fold, logistic, Venn-ABERS calibrated", "final fit (not in training)")
    tp["interval_lo"] = np.nan
    tp["interval_hi"] = np.nan
    tp.loc[np.flatnonzero(tm), "interval_lo"] = conf.va_p0.astype(float).values
    tp.loc[np.flatnonzero(tm), "interval_hi"] = conf.va_p1.astype(float).values
    tp = tp.drop(columns=["boot_p05", "boot_p95"], errors="ignore")
    tp["pred_pct"] = tp.pred_likelihood.rank(pct=True)
    # gaps
    sited_pr = (t.sited_dollars / t.population.where(t.population > 0)).fillna(0).to_numpy()
    tp["sited_dollars_per_resident_observed"] = sited_pr
    tp["sited_pct"] = pd.Series(sited_pr).rank(pct=True, method="average").to_numpy()
    tp["gap_actual"] = tp.need_pct - tp.sited_pct
    tp["high_need_no_sited_project"] = ((tp.need_pct >= HIGH_NEED) & (tp.T1_observed == 0)).astype(int)
    tp["gap_expected"] = tp.need_pct - tp.pred_pct
    tp = tp.merge(local, on="GEOID")
    tp.to_csv(C.STAGE2 / "tract_predictions.csv", index=False)
    g = tp[tp.low_pop_flag == 0]
    print(f"gap_actual >= 0.5: {int((g.gap_actual >= 0.5).sum())}; high need with no sited project: "
          f"{int(g.high_need_no_sited_project.sum())} tracts, {g.population[g.high_need_no_sited_project == 1].sum():,.0f} residents; "
          f"Spearman need vs sited $/resident {g.need.corr(g.sited_dollars_per_resident_observed, method='spearman'):+.3f}")

    # dashboard export: no dollar PREDICTIONS (T5 is unreliable, D-088); the OBSERVED sited dollars per
    # resident are included so the dashboard can recompute the actual-investment gap for interventions
    dash = tp.round(4).replace({np.nan: None})
    (C.DASH / "tracts.json").write_text(json.dumps(dash.to_dict("records"), separators=(",", ":")))
    sc_old = json.loads((C.DASH / "scores.json").read_text())
    sc_old.update({
        "map_model": "logistic regression",
        "map_model_reason": ("No model was clearly better on spatial CV (paired bootstrap 95% intervals include zero), "
                             "so the simpler, more transparent logistic regression drives the map (D-091)."),
        "map_model_test": comp.round(4).to_dict("records"),
        "T1_spatial_map_candidates": res.dropna(subset=["roc_auc"])[["model", "roc_auc", "pr_auc", "log_loss", "brier"]].round(3).to_dict("records"),
        "conformal_T1": {k: round(float(v), 3) for k, v in summary.items()},
        "top_drivers": glob.head(8)[["feature", "plain", "coefficient", "mean_abs_contribution"]].round(4).to_dict("records"),
        "gap_definitions": {"gap_actual": "need percentile minus the percentile of actual sited dollars per resident (primary)",
                            "gap_expected": "need percentile minus the percentile of predicted likelihood (need versus expected investment)",
                            "high_need_no_sited_project": f"need in the top quarter (percentile >= {HIGH_NEED}) and no sited project"},
    })
    (C.DASH / "scores.json").write_text(json.dumps(sc_old, indent=1, default=float))
    print("wrote tracts.json and scores.json")


if __name__ == "__main__":
    main()
