"""Prompt 22, Stage 2: models, validation, explanation, uncertainty, need and gap.

Run through the dedicated environment:
    bash scripts/ml/run_ml.sh scripts/ml/stage2_models.py      (from Modelling Data from Web/)

What it does
  1. Nested cross-validation (inner grouped CV picks hyperparameters on the
     training folds only) for prevalence, logistic regression, LightGBM,
     XGBoost and, when TABPFN_TOKEN is set, TabPFN. Spatial folds are primary;
     random folds and leave-one-jurisdiction-out are reported beside them.
     Targets T1 (sited project), T4 (project type) and T5 (log sited dollars
     per resident). T1 also runs the sensitivity feature set (D-080), the land
     share comparison set and the monotone-constrained scenario models.
  2. T2 (planned projects, the main future check) and T3 (diagnostic only,
     D-081) scored with the chosen T1 model's spatial out-of-fold predictions.
  3. Calibration before and after isotonic calibration inside the folds;
     reliability curves.
  4. Final fits on all 697 training tracts; SHAP (global and per tract) and
     partial dependence for the hazard features.
  5. Stability: 5 fold-and-model seeds, and 50 bootstrap resamples of tracts
     (score spread, top-driver spread).
  6. Moran's I (k = 6, seed 12086) on out-of-fold residuals; spatial lags of
     the inputs (never the target) tested if residuals cluster.
  7. Conformal uncertainty inside the spatial folds (D-083): Venn-ABERS
     probability intervals and 90% prediction sets for T1, split conformal
     intervals for T5, with achieved coverage.
  8. Need (exposure x vulnerability, separate from the model) and gap.
Outputs: outputs/ml/stage2/ (tables, figures, models) and outputs/ml/dashboard/.
"""
import json
import time
import warnings
from collections import Counter

import joblib
import lightgbm as lgb
import matplotlib
import numpy as np
import pandas as pd
import shap
import xgboost as xgb
from esda.moran import Moran
from libpysal.weights import KNN
from scipy import stats
from sklearn.base import clone
from sklearn.calibration import CalibratedClassifierCV, calibration_curve
from sklearn.cluster import KMeans
from sklearn.impute import SimpleImputer
from sklearn.inspection import partial_dependence
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (average_precision_score, brier_score_loss, log_loss, mean_absolute_error,
                             mean_squared_error, r2_score, roc_auc_score)
from sklearn.model_selection import GridSearchCV, GroupKFold, KFold, ParameterGrid, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

import ml_common as C

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

warnings.filterwarnings("ignore")
SEED = C.SEED
OUT = C.STAGE2
FIG = OUT / "figures"
pd.set_option("display.width", 250)

GRIDS = {
    "lgbm": {"n_estimators": [100, 300], "num_leaves": [4, 8], "min_child_samples": [20, 40]},
    "xgb": {"n_estimators": [100, 300], "max_depth": [2, 3], "min_child_weight": [1, 5]},
    "logistic": {"clf__C": [0.01, 0.1, 1.0, 10.0]},
    "ridge": {"r__alpha": [0.1, 1.0, 10.0, 100.0]},
}


def sec(t):
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78, flush=True)


# --------------------------------------------------------------------------
# model factories
# --------------------------------------------------------------------------

def make(name, task, features, y_train=None, monotone=False, seed=SEED, params=None):
    params = dict(params or {})
    piped = {k: v for k, v in params.items() if "__" in k}   # pipeline parameters (logistic, ridge)
    if piped:
        return _make(name, task, features, y_train, monotone, seed, {}).set_params(**piped)
    return _make(name, task, features, y_train, monotone, seed, params)


def _make(name, task, features, y_train, monotone, seed, params):
    mono = C.monotone_vector(features) if monotone else None
    if name == "lgbm":
        kw = dict(learning_rate=0.05, subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0,
                  random_state=seed, n_jobs=4, verbose=-1)
        if mono:
            kw["monotone_constraints"] = mono
        if task == "bin":
            return lgb.LGBMClassifier(objective="binary", class_weight="balanced", **kw, **params)
        return lgb.LGBMRegressor(**kw, **params)
    if name == "xgb":
        kw = dict(learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, reg_lambda=1.0, tree_method="hist",
                  random_state=seed, n_jobs=4)
        if mono:
            kw["monotone_constraints"] = tuple(mono)
        if task == "bin":
            spw = float((y_train == 0).sum() / max((y_train == 1).sum(), 1)) if y_train is not None else 1.0
            return xgb.XGBClassifier(eval_metric="logloss", scale_pos_weight=spw, **kw, **params)
        return xgb.XGBRegressor(**kw, **params)
    if name == "logistic":
        return Pipeline([("imp", SimpleImputer(strategy="median", add_indicator=True)), ("sc", StandardScaler()),
                         ("clf", LogisticRegression(class_weight="balanced", max_iter=5000, **params))])
    if name == "ridge":
        return Pipeline([("imp", SimpleImputer(strategy="median", add_indicator=True)), ("sc", StandardScaler()),
                         ("r", Ridge(**params))])
    if name == "tabpfn":
        from tabpfn import TabPFNClassifier
        return TabPFNClassifier(random_state=seed, device="cpu")
    raise ValueError(name)


def outer_splits(n, y, groups, kind, seed=SEED):
    if kind == "random":
        cv = StratifiedKFold(10, shuffle=True, random_state=seed) if y is not None and set(np.unique(y)) <= {0, 1} \
            else KFold(10, shuffle=True, random_state=seed)
        return list(cv.split(np.zeros(n), y if y is not None else None))
    g = groups
    return list(GroupKFold(len(np.unique(g))).split(np.zeros(n), y, g))


def inner_splits(y, groups, kind):
    if kind == "random" or groups is None:
        if set(np.unique(y)) <= {0, 1}:
            return list(StratifiedKFold(5, shuffle=True, random_state=SEED).split(np.zeros(len(y)), y))
        return list(KFold(5, shuffle=True, random_state=SEED).split(np.zeros(len(y))))
    k = min(5, len(np.unique(groups)))
    return list(GroupKFold(k).split(np.zeros(len(y)), y, groups))


def nested_oof(X, y, task, name, kind, groups=None, monotone=False, seed=SEED, tune=True):
    """Out-of-fold predictions with the hyperparameters tuned inside each training fold."""
    n = len(y)
    splits = outer_splits(n, y if task == "bin" else None, groups, kind, seed)
    pred = np.full(n, np.nan)
    fid = np.full(n, -1)
    chosen = []
    feats = list(X.columns)
    for i, (tr, te) in enumerate(splits):
        fid[te] = i
        ytr = y[tr]
        if name in ("prevalence", "mean"):
            pred[te] = ytr.mean()
            continue
        est = make(name, task, feats, ytr, monotone, seed)
        if tune and name in GRIDS:
            g_in = groups[tr] if groups is not None and kind != "random" else None
            scoring = "average_precision" if task == "bin" else "neg_mean_squared_error"
            gs = GridSearchCV(est, GRIDS[name], scoring=scoring, cv=inner_splits(ytr, g_in, kind), n_jobs=1,
                              error_score=np.nan)
            gs.fit(X.iloc[tr], ytr)
            est = gs.best_estimator_
            chosen.append(tuple(sorted(gs.best_params_.items())))
        else:
            est.fit(X.iloc[tr], ytr)
        pred[te] = est.predict_proba(X.iloc[te])[:, 1] if task == "bin" else est.predict(X.iloc[te])
    return pred, fid, chosen


# --------------------------------------------------------------------------
# scores
# --------------------------------------------------------------------------

def bin_scores(y, p, fid=None):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    out = {"n": len(y), "base_rate": y.mean(), "roc_auc": roc_auc_score(y, p), "pr_auc": average_precision_score(y, p),
           "log_loss": log_loss(y, p, labels=[0, 1]), "brier": brier_score_loss(y, p)}
    if fid is not None:
        r, a = [], []
        for f in np.unique(fid):
            m = fid == f
            if len(np.unique(y[m])) > 1:
                const = np.ptp(p[m]) == 0
                r.append(0.5 if const else roc_auc_score(y[m], p[m]))
                a.append(y[m].mean() if const else average_precision_score(y[m], p[m]))
        out["roc_auc_fold_mean"], out["pr_auc_fold_mean"] = np.mean(r), np.mean(a)
    return out


def reg_scores(y, p):
    return {"n": len(y), "rmse": mean_squared_error(y, p) ** 0.5, "mae": mean_absolute_error(y, p),
            "r2": r2_score(y, p), "spearman": stats.spearmanr(y, p)[0] if np.ptp(p) > 0 else np.nan}


def top_share(y, p, q=0.2):
    cut = np.quantile(p, 1 - q)
    return y[p >= cut].sum() / y.sum() if y.sum() else np.nan


def mode_params(chosen):
    if not chosen:
        return {}
    return dict(Counter(chosen).most_common(1)[0][0])


# --------------------------------------------------------------------------
# conformal (D-083)
# --------------------------------------------------------------------------

def venn_abers(s_cal, y_cal, s_test):
    """Inductive Venn-ABERS: [p0, p1] for each test score, and the merged probability."""
    p0 = np.empty(len(s_test))
    p1 = np.empty(len(s_test))
    for i, s in enumerate(s_test):
        xs = np.append(s_cal, s)
        for lab, store in ((0, p0), (1, p1)):
            iso = IsotonicRegression(out_of_bounds="clip", y_min=0, y_max=1)
            iso.fit(xs, np.append(y_cal, lab))
            store[i] = iso.predict([s])[0]
    merged = p1 / (1 - p0 + p1)
    return p0, p1, merged


def conformal_t1(X, y, folds, name, params, eps=0.10):
    """Inside each outer spatial fold: hold out one training fold for calibration."""
    n = len(y)
    out = pd.DataFrame(index=range(n), columns=["p_raw", "va_p0", "va_p1", "va_p", "set_has0", "set_has1"], dtype=float)
    ids = np.unique(folds)
    for f in ids:
        te = np.flatnonzero(folds == f)
        cal_fold = ids[(np.searchsorted(ids, f) + 1) % len(ids)]
        cal = np.flatnonzero(folds == cal_fold)
        tr = np.flatnonzero((folds != f) & (folds != cal_fold))
        m = make(name, "bin", list(X.columns), y[tr], params=params).fit(X.iloc[tr], y[tr])
        s_cal = m.predict_proba(X.iloc[cal])[:, 1]
        s_te = m.predict_proba(X.iloc[te])[:, 1]
        p0, p1, pm = venn_abers(s_cal, y[cal], s_te)
        # inductive conformal prediction sets, nonconformity = 1 - p(true label)
        a_cal = np.where(y[cal] == 1, 1 - s_cal, s_cal)
        def pval(a):
            return (np.sum(a_cal >= a) + 1) / (len(a_cal) + 1)
        has0 = np.array([pval(s) > eps for s in s_te])          # label 0 nonconformity = s
        has1 = np.array([pval(1 - s) > eps for s in s_te])      # label 1 nonconformity = 1 - s
        out.loc[te, :] = np.column_stack([s_te, p0, p1, pm, has0, has1])
    covered = np.where(y == 1, out.set_has1.astype(bool), out.set_has0.astype(bool))
    size = out.set_has0.astype(int) + out.set_has1.astype(int)
    summary = {"target_coverage": 1 - eps, "achieved_coverage": covered.mean(),
               "coverage_label1": covered[y == 1].mean(), "coverage_label0": covered[y == 0].mean(),
               "share_singleton_sets": (size == 1).mean(), "share_both_labels": (size == 2).mean(),
               "share_empty_sets": (size == 0).mean(),
               "venn_abers_mean_width": float((out.va_p1 - out.va_p0).mean()),
               "venn_abers_merged_log_loss": log_loss(y, np.clip(out.va_p.astype(float), 1e-6, 1 - 1e-6)),
               "raw_log_loss": log_loss(y, np.clip(out.p_raw.astype(float), 1e-6, 1 - 1e-6)),
               "venn_abers_merged_brier": brier_score_loss(y, out.va_p.astype(float)),
               "raw_brier": brier_score_loss(y, out.p_raw.astype(float)),
               "merged_in_interval_check": float(((out.va_p >= out.va_p0 - 1e-9) & (out.va_p <= out.va_p1 + 1e-9)).mean())}
    return out, summary


def conformal_t5(X, y, folds, name, params, alpha=0.10):
    n = len(y)
    pred = np.full(n, np.nan)
    lo = np.full(n, np.nan)
    hi = np.full(n, np.nan)
    ids = np.unique(folds)
    for f in ids:
        te = np.flatnonzero(folds == f)
        cal_fold = ids[(np.searchsorted(ids, f) + 1) % len(ids)]
        cal = np.flatnonzero(folds == cal_fold)
        tr = np.flatnonzero((folds != f) & (folds != cal_fold))
        m = make(name, "reg", list(X.columns), params=params).fit(X.iloc[tr], y[tr])
        r = np.abs(y[cal] - m.predict(X.iloc[cal]))
        k = int(np.ceil((len(r) + 1) * (1 - alpha)))
        q = np.sort(r)[min(k, len(r)) - 1]
        pred[te] = m.predict(X.iloc[te])
        lo[te], hi[te] = pred[te] - q, pred[te] + q
    cov = ((y >= lo) & (y <= hi)).mean()
    return pred, lo, hi, {"target_coverage": 1 - alpha, "achieved_coverage": cov,
                          "mean_width_log_units": float(np.mean(hi - lo))}


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main():
    t0 = time.time()
    OUT.mkdir(parents=True, exist_ok=True)
    FIG.mkdir(parents=True, exist_ok=True)
    C.DASH.mkdir(parents=True, exist_ok=True)
    np.random.seed(SEED)
    t = C.load_table()
    tm = C.train_mask(t)
    tr = t[tm].reset_index(drop=True)
    folds = tr.fold_spatial.to_numpy()
    juris = pd.factorize(tr.jurisdiction)[0]
    groups = {"spatial": folds, "random": None, "jurisdiction": juris}
    y1 = tr.T1.to_numpy()
    use_tabpfn = C.tabpfn_available()
    print(f"training tracts {len(tr)}; T1 base rate {y1.mean():.3f}; TabPFN {'ON' if use_tabpfn else 'OFF (no TABPFN_TOKEN)'}")

    # ---------------- 1. T1 comparison ----------------
    sec("1. T1: SITED PROJECT PRESENT (nested CV)")
    rows, oof, chosen_params = [], {}, {}
    models = ["prevalence", "logistic", "lgbm", "xgb"] + (["tabpfn"] if use_tabpfn else [])
    for name in models:
        for kind in ("spatial", "random", "jurisdiction"):
            p, fid, ch = nested_oof(tr[C.MAIN], y1, "bin", name, kind, groups[kind])
            oof[("T1", name, kind)] = p
            chosen_params[("T1", name, kind)] = ch
            rows.append({"target": "T1", "features": "main (27)", "model": name, "cv": kind, **bin_scores(y1, p, fid)})
            print(f"  {name:10s} {kind:12s} ROC {rows[-1]['roc_auc']:.3f} PR {rows[-1]['pr_auc']:.3f} "
                  f"LL {rows[-1]['log_loss']:.3f} ({time.time() - t0:.0f}s)", flush=True)
    if not use_tabpfn:
        for kind in ("spatial", "random", "jurisdiction"):
            rows.append({"target": "T1", "features": "main (27)", "model": "tabpfn", "cv": kind,
                         "note": "not run: TabPFN weights need a license key (TABPFN_TOKEN), D-082"})
    # sensitivity, land comparison, monotone constrained (spatial only)
    for fs_name, fs in (("sensitivity (30)", C.SENS), ("land shares (27)", C.LAND)):
        for name in ("logistic", "lgbm", "xgb"):
            p, fid, ch = nested_oof(tr[fs], y1, "bin", name, "spatial", folds)
            rows.append({"target": "T1", "features": fs_name, "model": name, "cv": "spatial", **bin_scores(y1, p, fid)})
    for name in ("lgbm", "xgb"):
        p, fid, ch = nested_oof(tr[C.MAIN], y1, "bin", name, "spatial", folds, monotone=True)
        oof[("T1", name + "_mono", "spatial")] = p
        chosen_params[("T1", name + "_mono", "spatial")] = ch
        rows.append({"target": "T1", "features": "main (27)", "model": name + " monotone", "cv": "spatial",
                     **bin_scores(y1, p, fid)})

    # ---------------- choose models ----------------
    t1 = pd.DataFrame(rows)
    sp = t1[(t1.cv == "spatial") & (t1.features == "main (27)")].set_index("model")
    tree = sp.loc[["lgbm", "xgb"]]
    best_tree = tree.sort_values(["pr_auc", "log_loss"], ascending=[False, True]).index[0]
    map_model = best_tree
    if use_tabpfn and "tabpfn" in sp.index:
        d_roc = sp.loc["tabpfn", "roc_auc"] - sp.loc[best_tree, "roc_auc"]
        d_pr = sp.loc["tabpfn", "pr_auc"] - sp.loc[best_tree, "pr_auc"]
        if d_roc >= 0.02 and d_pr >= 0.02:
            map_model = "tabpfn"
    scen_model = best_tree  # monotone version of the better tree family
    params_map = mode_params(chosen_params[("T1", best_tree, "spatial")])
    params_scen = mode_params(chosen_params[("T1", scen_model + "_mono", "spatial")])
    choice = {"best_tree_model": best_tree, "map_model": map_model, "scenario_model": scen_model + " (monotone)",
              "params_map": params_map, "params_scenario": params_scen,
              "rule": "tree model with the higher spatial PR-AUC (ties: lower log loss); TabPFN drives the map only if "
                      "it beats it by at least 0.02 in both spatial ROC-AUC and PR-AUC"}
    print("\nchoice:", json.dumps(choice, default=str))

    # ---------------- T4 ----------------
    sec("T4: PROJECT TYPE (nature-based or hybrid vs gray), project level")
    proj = pd.read_csv(C.STAGE1 / "model_table_projects_T4.csv", dtype={"tract_GEOID": str})
    P = proj.merge(tr[["GEOID", "fold_spatial", "jurisdiction"] + C.MAIN], left_on="tract_GEOID", right_on="GEOID")
    dummies = pd.concat([pd.get_dummies(P.Spatial_Resolution, prefix="scale", dtype=float),
                         pd.get_dummies(P.Hazard_Focus, prefix="focus", dtype=float)], axis=1)
    X4 = pd.concat([P[C.MAIN].reset_index(drop=True), dummies.reset_index(drop=True)], axis=1)
    X4.columns = [c.replace(" ", "_").replace("&", "and") for c in X4.columns]
    y4 = P.T4.to_numpy()
    g4 = {"spatial": P.fold_spatial.to_numpy(), "random": None, "jurisdiction": pd.factorize(P.jurisdiction)[0]}
    t4rows, oof4 = [], {}
    for name in ["prevalence", "logistic", "lgbm", "xgb"] + (["tabpfn"] if use_tabpfn else []):
        for kind in ("spatial", "random", "jurisdiction"):
            p, fid, ch = nested_oof(X4, y4, "bin", name, kind, g4[kind])
            oof4[(name, kind)] = (p, ch)
            t4rows.append({"target": "T4", "features": "main + scale + hazard focus", "model": name, "cv": kind,
                           **bin_scores(y4, p, fid)})
    if not use_tabpfn:
        for kind in ("spatial", "random", "jurisdiction"):
            t4rows.append({"target": "T4", "features": "main + scale + hazard focus", "model": "tabpfn", "cv": kind,
                           "note": "not run: TabPFN weights need a license key (TABPFN_TOKEN), D-082"})
    Xf = dummies.reset_index(drop=True)
    Xf.columns = [c.replace(" ", "_").replace("&", "and") for c in Xf.columns]
    for name in ("logistic", "lgbm"):
        p, fid, _ = nested_oof(Xf, y4, "bin", name, "spatial", g4["spatial"])
        t4rows.append({"target": "T4", "features": "scale + hazard focus only", "model": name, "cv": "spatial",
                       **bin_scores(y4, p, fid)})
    Xn = P[C.MAIN].reset_index(drop=True)
    for name in ("logistic", "lgbm"):
        p, fid, _ = nested_oof(Xn, y4, "bin", name, "spatial", g4["spatial"])
        t4rows.append({"target": "T4", "features": "tract features only (no hazard focus)", "model": name,
                       "cv": "spatial", **bin_scores(y4, p, fid)})
    t4 = pd.DataFrame(t4rows)
    print(t4.drop(columns=[c for c in ("note",) if c in t4]).to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    # hazard focus effect on type (descriptive)
    hf = P.groupby("Hazard_Focus").agg(projects=("T4", "size"), nature_based_or_hybrid=("T4", "sum"))
    hf["share"] = hf.nature_based_or_hybrid / hf.projects
    hf.to_csv(OUT / "T4_hazard_focus.csv")

    # ---------------- T5 ----------------
    sec("T5: LOG SITED DOLLARS PER RESIDENT (tracts with a sited project)")
    d5 = tr[tr.T5.notna()].reset_index(drop=True)
    y5 = d5.T5.to_numpy()
    g5 = {"spatial": d5.fold_spatial.to_numpy(), "random": None, "jurisdiction": pd.factorize(d5.jurisdiction)[0]}
    t5rows, ch5 = [], {}
    for name in ("mean", "ridge", "lgbm", "xgb"):
        for kind in ("spatial", "random", "jurisdiction"):
            p, fid, ch = nested_oof(d5[C.MAIN], y5, "reg", name, kind, g5[kind])
            ch5[(name, kind)] = ch
            t5rows.append({"target": "T5", "model": name, "cv": kind, **reg_scores(y5, p)})
    t5 = pd.DataFrame(t5rows)
    print(t5.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    t5_best = t5[(t5.cv == "spatial") & t5.model.isin(["ridge", "lgbm", "xgb"])].sort_values("rmse").model.iloc[0]

    allres = pd.concat([t1, t4], ignore_index=True)
    allres.to_csv(OUT / "results_binary.csv", index=False)
    t5.to_csv(OUT / "results_T5.csv", index=False)
    sec("T1 RESULTS")
    print(t1.drop(columns=[c for c in ("note",) if c in t1]).to_string(index=False, float_format=lambda v: f"{v:.3f}"))

    # ---------------- 2. T2 and T3 ----------------
    sec("2. T2 (main future check) AND T3 (diagnostic only, D-081)")
    fut = []
    for label, key in (("chosen T1 model", ("T1", best_tree, "spatial")),
                       ("scenario model (monotone)", ("T1", scen_model + "_mono", "spatial")),
                       ("logistic baseline", ("T1", "logistic", "spatial"))):
        p = oof[key]
        for subset, m in (("all training tracts", np.ones(len(tr), bool)), ("tracts with no current project", y1 == 0)):
            yy = tr.T2.to_numpy()[m]
            s = bin_scores(yy, p[m])
            s["share_of_T2_tracts_in_top20pct"] = top_share(yy, p[m])
            s["share_of_planned_projects_in_top20pct"] = top_share(tr.T2_planned_projects.to_numpy()[m], p[m])
            fut.append({"check": f"T2 ({subset})", "model": label, **s})
    yT3 = tr.T3_train.to_numpy()
    p3, _, _ = nested_oof(tr[C.MAIN], yT3, "bin", best_tree, "spatial", folds)
    ev = tr.T3_eval_set.to_numpy() == 1
    s = bin_scores(tr.T3_new_2024_26.to_numpy()[ev], p3[ev])
    s["share_of_T2_tracts_in_top20pct"] = top_share(tr.T3_new_2024_26.to_numpy()[ev], p3[ev])
    fut.append({"check": "T3 DIAGNOSTIC ONLY (Reported_Year is a document year)", "model": "chosen T1 model, 2023 label", **s})
    fut = pd.DataFrame(fut).rename(columns={"share_of_T2_tracts_in_top20pct": "share_of_positive_tracts_in_top20pct"})
    print(fut.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    fut.to_csv(OUT / "results_future_checks.csv", index=False)

    # ---------------- 3. calibration ----------------
    sec("3. CALIBRATION (isotonic inside the folds)")
    cal_rows = []
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    for ax, (label, X, y, g, name, params) in zip(axes, (
            ("T1", tr[C.MAIN], y1, folds, best_tree, params_map),
            ("T4", X4, y4, g4["spatial"], "lgbm", mode_params(oof4[("lgbm", "spatial")][1])))):
        raw = np.full(len(y), np.nan)
        cal = np.full(len(y), np.nan)
        for f in np.unique(g):
            te, trn = g == f, g != f
            est = make(name, "bin", list(X.columns), y[trn], params=params)
            raw[te] = clone(est).fit(X[trn], y[trn]).predict_proba(X[te])[:, 1]
            inner = inner_splits(y[trn], g[trn], "spatial")
            cc = CalibratedClassifierCV(est, method="isotonic", cv=inner).fit(X[trn], y[trn])
            cal[te] = cc.predict_proba(X[te])[:, 1]
        for kind, p in (("before", raw), ("after isotonic", cal)):
            cal_rows.append({"target": label, "model": name, "calibration": kind, **bin_scores(y, p)})
            fx, fy = calibration_curve(y, np.clip(p, 0, 1), n_bins=10, strategy="quantile")
            ax.plot(fy, fx, marker="o", label=kind)
        ax.plot([0, 1], [0, 1], "k--", lw=1, label="perfect")
        ax.set_title(f"{label} reliability ({name}, spatial out-of-fold)")
        ax.set_xlabel("predicted probability")
        ax.set_ylabel("observed share")
        ax.legend()
    plt.tight_layout()
    plt.savefig(FIG / "reliability_T1_T4.png", dpi=130)
    plt.close()
    cal_df = pd.DataFrame(cal_rows)
    print(cal_df.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    cal_df.to_csv(OUT / "results_calibration.csv", index=False)

    # ---------------- 6. residual Moran's I ----------------
    sec("6. MORAN'S I ON OUT-OF-FOLD RESIDUALS (k = 6, seed 12086)")
    W = KNN.from_array(tr[["x_km", "y_km"]].to_numpy(), k=6)
    W.transform = "r"
    moran_rows = []
    res = y1 - oof[("T1", best_tree, "spatial")]
    np.random.seed(SEED)
    mi = Moran(res, W, permutations=999)
    moran_rows.append({"model": best_tree, "features": "main", "I": mi.I, "p_perm": mi.p_sim})
    print(f"  residual Moran's I {mi.I:.3f}, p {mi.p_sim:.3f}")
    lag_used = False
    if mi.p_sim < 0.05 and mi.I > 0.05:
        Xl = tr[C.MAIN].copy()
        filled = Xl.fillna(Xl.median())
        for c in C.MAIN:
            Xl[f"lag_{c}"] = W.sparse @ filled[c].to_numpy()
        p_l, fid_l, ch_l = nested_oof(Xl, y1, "bin", best_tree, "spatial", folds)
        s_l = bin_scores(y1, p_l, fid_l)
        np.random.seed(SEED)
        mi_l = Moran(y1 - p_l, W, permutations=999)
        moran_rows.append({"model": best_tree, "features": "main + spatial lags of the inputs", "I": mi_l.I,
                           "p_perm": mi_l.p_sim, "spatial_roc_auc": s_l["roc_auc"], "spatial_pr_auc": s_l["pr_auc"],
                           "spatial_log_loss": s_l["log_loss"]})
        print(f"  with lags: Moran's I {mi_l.I:.3f}, p {mi_l.p_sim:.3f}; spatial ROC {s_l['roc_auc']:.3f} "
              f"PR {s_l['pr_auc']:.3f} (without lags ROC {sp.loc[best_tree, 'roc_auc']:.3f} PR {sp.loc[best_tree, 'pr_auc']:.3f})")
        lag_used = bool(s_l["pr_auc"] > sp.loc[best_tree, "pr_auc"] + 0.01 and mi_l.I < mi.I)
    moran = pd.DataFrame(moran_rows)
    moran["lags_adopted"] = lag_used
    moran.to_csv(OUT / "results_residual_moran.csv", index=False)
    print(f"  spatial lags adopted in the final models: {lag_used}")

    # ---------------- 4. final fits, SHAP, partial dependence ----------------
    sec("4. FINAL FITS, SHAP AND PARTIAL DEPENDENCE")
    Xall = t[C.MAIN]
    m_map = make(best_tree, "bin", C.MAIN, y1, params=params_map).fit(tr[C.MAIN], y1)
    m_scen = make(scen_model, "bin", C.MAIN, y1, monotone=True, params=params_scen).fit(tr[C.MAIN], y1)
    joblib.dump({"model": m_map, "features": C.MAIN, "name": best_tree, "params": params_map}, OUT / "model_map.joblib")
    joblib.dump({"model": m_scen, "features": C.MAIN, "name": scen_model + "_monotone", "params": params_scen,
                 "train_min": tr[C.MAIN].min().to_dict(), "train_max": tr[C.MAIN].max().to_dict()},
                OUT / "model_scenario.joblib")
    expl = shap.TreeExplainer(m_map)
    sv = expl.shap_values(Xall)
    sv = sv[1] if isinstance(sv, list) else sv
    glob = pd.DataFrame({"feature": C.MAIN, "mean_abs_shap": np.abs(sv[tm]).mean(axis=0)}).sort_values(
        "mean_abs_shap", ascending=False)
    glob["plain"] = glob.feature.map(C.plain)
    glob.to_csv(OUT / "shap_global.csv", index=False)
    print(glob.head(12).to_string(index=False, float_format=lambda v: f"{v:.4f}"))
    plt.figure(figsize=(7, 6))
    g12 = glob.head(15)[::-1]
    plt.barh(g12.plain, g12.mean_abs_shap)
    plt.xlabel("mean |SHAP| (log-odds)")
    plt.title(f"T1 top drivers ({best_tree}, final fit)")
    plt.tight_layout()
    plt.savefig(FIG / "shap_global_T1.png", dpi=130)
    plt.close()
    local = []
    for i, gid in enumerate(t.GEOID):
        order = np.argsort(-np.abs(sv[i]))[:3]
        local.append({"GEOID": gid, **{f"driver{k + 1}": f"{C.plain(C.MAIN[j])} ({'raises' if sv[i, j] > 0 else 'lowers'})"
                                         for k, j in enumerate(order)},
                      **{f"driver{k + 1}_shap": float(sv[i, j]) for k, j in enumerate(order)}})
    local = pd.DataFrame(local)
    local.to_csv(OUT / "shap_local_top3.csv", index=False)
    pd_rows = []
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    for ax, f in zip(axes, C.HAZ_MAIN):
        for label, m in (("unconstrained", m_map), ("monotone (scenario)", m_scen)):
            r = partial_dependence(m, tr[C.MAIN], [f], grid_resolution=20, kind="average", response_method="predict_proba")
            grid, avg = r["grid_values"][0], r["average"][0]
            ax.plot(grid, avg, label=label)
            pd_rows += [{"feature": f, "model": label, "value": v, "avg_prediction": a} for v, a in zip(grid, avg)]
        ax.set_title(C.plain(f), fontsize=9)
        ax.set_ylabel("average predicted likelihood")
        ax.legend(fontsize=8)
    plt.tight_layout()
    plt.savefig(FIG / "partial_dependence_hazards.png", dpi=130)
    plt.close()
    pd.DataFrame(pd_rows).to_csv(OUT / "partial_dependence.csv", index=False)

    # ---------------- 5. stability ----------------
    sec("5. STABILITY: 5 seeds and 50 bootstrap resamples")
    seed_rows = []
    for s in (SEED, 1, 2, 3, 4):
        km = KMeans(10, random_state=s, n_init=10).fit(tr[["x_km", "y_km"]])
        fs = km.labels_
        p = np.full(len(y1), np.nan)
        for f in np.unique(fs):
            te, trn = fs == f, fs != f
            p[te] = make(best_tree, "bin", C.MAIN, y1[trn], seed=s, params=params_map).fit(
                tr[C.MAIN][trn], y1[trn]).predict_proba(tr[C.MAIN][te])[:, 1]
        seed_rows.append({"seed": s, **bin_scores(y1, p)})
    seeds = pd.DataFrame(seed_rows)
    print(seeds.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print("spread (sd):", seeds[["roc_auc", "pr_auc", "log_loss"]].std().round(4).to_dict())
    seeds.to_csv(OUT / "stability_seeds.csv", index=False)
    rng = np.random.default_rng(SEED)
    ranks, boot_pred = [], []
    for b in range(50):
        idx = rng.integers(0, len(tr), len(tr))
        mb = make(best_tree, "bin", C.MAIN, y1[idx], seed=SEED + b, params=params_map).fit(tr[C.MAIN].iloc[idx], y1[idx])
        svb = shap.TreeExplainer(mb).shap_values(tr[C.MAIN])
        svb = svb[1] if isinstance(svb, list) else svb
        imp = pd.Series(np.abs(svb).mean(axis=0), index=C.MAIN).rank(ascending=False)
        ranks.append(imp)
        boot_pred.append(mb.predict_proba(Xall)[:, 1])
    R = pd.DataFrame(ranks)
    stab = pd.DataFrame({"median_rank": R.median(), "rank_sd": R.std(), "share_in_top5": (R <= 5).mean()}).sort_values(
        "median_rank")
    stab["plain"] = stab.index.map(C.plain)
    print(stab.head(10).to_string(float_format=lambda v: f"{v:.2f}"))
    stab.to_csv(OUT / "stability_shap_ranks.csv")
    BP = np.array(boot_pred)

    # ---------------- 7. conformal ----------------
    sec("7. CONFORMAL UNCERTAINTY INSIDE THE SPATIAL FOLDS (D-083)")
    conf1, s1 = conformal_t1(tr[C.MAIN], y1, folds, best_tree, params_map)
    print("T1:", json.dumps({k: round(v, 4) for k, v in s1.items()}))
    p5, lo5, hi5, s5 = conformal_t5(d5[C.MAIN], y5, d5.fold_spatial.to_numpy(), t5_best if t5_best != "ridge" else "ridge",
                                    mode_params(ch5[(t5_best, "spatial")]))
    print(f"T5 ({t5_best}):", json.dumps({k: round(v, 4) for k, v in s5.items()}))
    pd.DataFrame([{"target": "T1", "method": "Venn-ABERS + inductive conformal sets", **s1},
                  {"target": "T5", "method": f"split conformal ({t5_best})", **s5}]).to_csv(
        OUT / "results_conformal.csv", index=False)

    # ---------------- 8. need and gap ----------------
    sec("8. NEED AND GAP")
    pca = pd.read_csv(C.paths.OUT_PCA / "pca_scores_tract.csv", dtype={"GEOID": str}).set_index("GEOID")
    vul = t.GEOID.map(pca.RC1)
    sign = np.sign(pd.Series(vul.values).corr(t.EP_POV150, method="spearman"))
    vul = vul * sign
    pct = lambda s: s.rank(pct=True)  # noqa: E731
    expo = pd.concat([pct(t[c]) for c in C.HAZ_MAIN], axis=1).mean(axis=1)
    need_raw = pct(expo) * pct(vul)
    pred = pd.Series(np.nan, index=t.index)
    pred[np.flatnonzero(tm)] = conf1.va_p.astype(float).values
    pred_raw_final = pd.Series(m_map.predict_proba(Xall)[:, 1], index=t.index)
    pred = pred.fillna(pred_raw_final)  # the tract under 100 residents: final-fit prediction, flagged
    out = pd.DataFrame({
        "GEOID": t.GEOID, "jurisdiction": t.jurisdiction, "low_pop_flag": t.low_pop_flag, "population": t.population,
        "T1_observed": t.T1, "T2_planned_projects": t.T2_planned_projects,
        "pred_likelihood": pred, "pred_source": np.where(tm, "spatial out-of-fold, Venn-ABERS calibrated", "final fit (not in training)"),
        "interval_lo": np.nan, "interval_hi": np.nan,
        "boot_p05": np.percentile(BP, 5, axis=0), "boot_p95": np.percentile(BP, 95, axis=0),
        "exposure_index": expo, "vulnerability_rc1": vul, "need": need_raw,
    })
    out.loc[np.flatnonzero(tm), "interval_lo"] = conf1.va_p0.astype(float).values
    out.loc[np.flatnonzero(tm), "interval_hi"] = conf1.va_p1.astype(float).values
    out["need_pct"] = out.need.rank(pct=True)
    out["pred_pct"] = out.pred_likelihood.rank(pct=True)
    out["gap"] = out.need_pct - out.pred_pct
    out = out.merge(local[["GEOID", "driver1", "driver2", "driver3"]], on="GEOID")
    for c in ("slr_3ft_pop_exposed", "surge_cat3_any_pop_exposed", "surge_cat4_any_pop_exposed", "heat_p95_pop_exposed"):
        out[c] = t[c].values
    out.to_csv(OUT / "tract_predictions.csv", index=False)
    g = out[out.low_pop_flag == 0]
    print(f"need vs predicted likelihood, Spearman {g.need.corr(g.pred_likelihood, method='spearman'):+.3f}; "
          f"tracts with gap >= 0.5: {int((g.gap >= 0.5).sum())}; vulnerability sign used {sign:+.0f}; "
          f"tracts without a need score {int(out.need.isna().sum())}")

    # ---------------- dashboard export ----------------
    scores = {
        "generated": "5 Nov 2026", "preliminary": True,
        "map_model": map_model, "scenario_model": scen_model + " (monotone)", "tabpfn_run": use_tabpfn,
        "T1_spatial": {m: {k: round(float(sp.loc[m, k]), 3) for k in ("roc_auc", "pr_auc", "log_loss", "brier")}
                       for m in sp.index if pd.notna(sp.loc[m].get("roc_auc", np.nan))},
        "T1_base_rate": round(float(y1.mean()), 3),
        "T2": fut.iloc[0][["roc_auc", "pr_auc", "base_rate", "share_of_planned_projects_in_top20pct"]].astype(float).round(3).to_dict(),
        "conformal_T1": {k: round(float(v), 3) for k, v in s1.items()},
        "residual_moran_I": round(float(mi.I), 3),
        "top_drivers": glob.head(8)[["feature", "plain", "mean_abs_shap"]].round(4).to_dict("records"),
    }
    (C.DASH / "scores.json").write_text(json.dumps(scores, indent=1, default=float))
    recs = out.round(4).replace({np.nan: None}).to_dict("records")
    (C.DASH / "tracts.json").write_text(json.dumps(recs, separators=(",", ":")))
    json.dump(choice, open(OUT / "model_choice.json", "w"), indent=1, default=str)
    print(f"\ndone in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
