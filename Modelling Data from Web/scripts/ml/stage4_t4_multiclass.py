"""Four-class project type (T4): gray, green, blue, hybrid (D-108).

    bash scripts/ml/run_ml.sh scripts/ml/stage4_t4_multiclass.py      (from Modelling Data from Web/)

Same project-level frame, features and spatial folds as the binary T4 in
stage2_models.py: the 27 tract features of the receiving tract, plus project
scale and hazard focus. Folds are inherited from the project's tract.
  - logistic: multinomial, class weights 'balanced', C tuned inside each
    training fold (inner group folds, macro F1);
  - xgb: multi:softprob with balanced sample weights, depth and trees tuned
    inside each training fold.
Reported: per-class precision, recall, F1 and counts, the confusion matrix,
and the binary collapse (green, blue or hybrid vs gray) for comparison with
the binary model.
Outputs: outputs/ml/stage4/t4_multiclass_*.csv
"""
import itertools
import warnings

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, f1_score, precision_recall_fscore_support, roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.utils.class_weight import compute_sample_weight

import ml_common as C

warnings.filterwarnings("ignore")
OUT = C.paths.OUT_ML / "stage4"
CLASSES = ["Gray", "Green", "Blue", "Hybrid"]
SEED = C.SEED


def frame():
    t = C.load_table()
    tr = t[C.train_mask(t)].reset_index(drop=True)
    proj = pd.read_csv(C.STAGE1 / "model_table_projects_T4.csv", dtype={"tract_GEOID": str})
    P = proj.merge(tr[["GEOID", "fold_spatial"] + C.MAIN], left_on="tract_GEOID", right_on="GEOID")
    dummies = pd.concat([pd.get_dummies(P.Spatial_Resolution, prefix="scale", dtype=float),
                         pd.get_dummies(P.Hazard_Focus, prefix="focus", dtype=float)], axis=1)
    X = pd.concat([P[C.MAIN].reset_index(drop=True), dummies.reset_index(drop=True)], axis=1)
    X.columns = [c.replace(" ", "_").replace("&", "and") for c in X.columns]
    y = P.Infrastructure_Type.map({c: i for i, c in enumerate(CLASSES)}).to_numpy()
    assert not np.isnan(y.astype(float)).any()
    return X, y.astype(int), P.fold_spatial.to_numpy()


def logistic(C_):
    return Pipeline([("imp", SimpleImputer(strategy="median", add_indicator=True)), ("sc", StandardScaler()),
                     ("clf", LogisticRegression(C=C_, class_weight="balanced", max_iter=5000))])


def booster(depth, n):
    return xgb.XGBClassifier(objective="multi:softprob", num_class=4, learning_rate=0.05, subsample=0.8,
                             colsample_bytree=0.8, reg_lambda=1.0, tree_method="hist", random_state=SEED, n_jobs=4,
                             max_depth=depth, n_estimators=n, eval_metric="mlogloss")


def fit(name, params, X, y):
    if name == "logistic":
        m = logistic(params["C"])
        m.fit(X, y)
    else:
        m = booster(params["depth"], params["n"])
        m.fit(X, y, sample_weight=compute_sample_weight("balanced", y))
    return m


GRID = {"logistic": [{"C": c} for c in (0.01, 0.1, 1.0, 10.0)],
        "xgb": [{"depth": d, "n": n} for d, n in itertools.product((2, 3), (100, 300))]}


def nested(name, X, y, g):
    proba = np.zeros((len(y), 4))
    chosen = []
    for trn, tst in GroupKFold(len(np.unique(g))).split(X, y, g):
        inner = list(GroupKFold(5).split(X.iloc[trn], y[trn], g[trn]))
        best, best_s = None, -1
        for params in GRID[name]:
            s = []
            for a, b in inner:
                if len(np.unique(y[trn][a])) < 4:
                    continue
                m = fit(name, params, X.iloc[trn[a]], y[trn[a]])
                s.append(f1_score(y[trn[b]], m.predict_proba(X.iloc[trn[b]]).argmax(1), average="macro", labels=range(4),
                                  zero_division=0))
            if np.mean(s) > best_s:
                best, best_s = params, np.mean(s)
        chosen.append(best)
        m = fit(name, best, X.iloc[trn], y[trn])
        pr = m.predict_proba(X.iloc[tst])
        proba[tst] = pr
    return proba, chosen


def main():
    X, y, g = frame()
    print("projects by type:", dict(zip(CLASSES, np.bincount(y, minlength=4))))
    rows, conf, binr = [], [], []
    for name in ("logistic", "xgb"):
        proba, chosen = nested(name, X, y, g)
        pred = proba.argmax(1)
        pr, rc, f1, sup = precision_recall_fscore_support(y, pred, labels=range(4), zero_division=0)
        for k, c in enumerate(CLASSES):
            rows.append({"model": name, "class": c, "projects": int(sup[k]), "predicted": int((pred == k).sum()),
                         "precision": pr[k], "recall": rc[k], "f1": f1[k],
                         "one_vs_rest_roc_auc": roc_auc_score(y == k, proba[:, k])})
        rows.append({"model": name, "class": "macro average", "projects": int(len(y)), "precision": pr.mean(),
                     "recall": rc.mean(), "f1": f1.mean()})
        cm = pd.DataFrame(confusion_matrix(y, pred, labels=range(4)), index=[f"true {c}" for c in CLASSES],
                          columns=[f"predicted {c}" for c in CLASSES])
        cm.insert(0, "model", name)
        conf.append(cm)
        nb = proba[:, 1:].sum(1)
        yb = (y > 0).astype(int)
        binr.append({"model": name, "binary_collapse_roc_auc": roc_auc_score(yb, nb),
                     "chosen_params": str(chosen)})
        print(f"{name}: chosen {chosen}")
    R = pd.DataFrame(rows)
    print(R.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    CM = pd.concat(conf)
    print(CM.to_string())
    B = pd.DataFrame(binr)
    print(B.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print("binary T4 reference (Stage 2, spatial): logistic ROC-AUC 0.792, XGBoost 0.803")
    R.to_csv(OUT / "t4_multiclass_per_class.csv", index=False)
    CM.to_csv(OUT / "t4_multiclass_confusion.csv")
    B.to_csv(OUT / "t4_multiclass_binary_collapse.csv", index=False)


if __name__ == "__main__":
    main()
