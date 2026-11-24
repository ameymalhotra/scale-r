"""Prompt 22, Stage 1: modelling table, targets and baselines.

Builds the tract modelling table (features and targets), the project-level
table for T4, the feature dictionary and the input inventory, then scores
two baselines (prevalence and regularized logistic regression) under spatial,
random and leave-one-jurisdiction-out cross-validation. No gradient boosting
here (Stage 2).

Rules kept (see DECISIONS.md D-071 onward):
  * GEOID as string; the 698-tract frame; the tract under 100 residents
    (Pennsuco, 12086981100) is excluded from training and kept, flagged, in
    the outputs.
  * Targets use single-unit sited projects only (parcel, neighborhood,
    corridor). Planned projects never enter training.
  * No feature is built from investment, project counts or anything
    downstream of a target. Imputation, scaling and PCA are fitted inside
    each training fold (scikit-learn pipelines).
  * One hazard measure per family at the primary scenarios (D-040), the heat
    75th percentile not used (D-036), Category 5 only in its corrected form.

Usage: ../.venv/bin/python scripts/ml/stage1_build.py   (from Modelling Data from Web/)
Outputs: outputs/ml/stage1/
"""
import sys
import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from scipy import stats
from sklearn.base import clone
from sklearn.cluster import KMeans
from sklearn.compose import ColumnTransformer
from sklearn.decomposition import PCA
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.metrics import (average_precision_score, brier_score_loss, log_loss, mean_absolute_error,
                             mean_squared_error, r2_score, roc_auc_score)
from sklearn.model_selection import GridSearchCV, GroupKFold, KFold, StratifiedKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import paths  # noqa: E402
from allocation import assign_municipality, load_units  # noqa: E402
from analysis_variables import PCA_TRACT_VARS, load_tract  # noqa: E402

warnings.filterwarnings("ignore")
SEED = 12086
N_SPATIAL_FOLDS = 10
OUT = paths.OUT_ML / "stage1"
SITED = ["Parcel", "Neighborhood", "Corridor"]
DONE = ["Completed", "Funded", "Ongoing"]

HAZARD_POP = ["slr_3ft_pop_share", "surge_cat3_any_pop_share", "surge_cat4_any_pop_share",
              "surge_cat3_over3ft_pop_share", "heat_lst_popwt_mean_f", "heat_p95_pop_share"]
HAZARD_LAND = ["slr_3ft_land_share", "surge_cat3_any_land_share", "surge_cat4_any_land_share",
               "surge_cat3_over3ft_land_share", "heat_land_mean_f", "heat_p95_land_share"]
NRI = ["nri_eal_per_person", "nri_ealb_per_building_value"]
CONTEXT_ALL = ["pop_density", "housing_density", "land_km2", "dist_coast_km", "in_municipality"]
# 0.75 rule (D-073): housing_density (rho +0.94 with pop_density) and land_km2 (-0.86) leave the main set
CONTEXT = ["pop_density", "dist_coast_km", "in_municipality"]
# skewed positive features get a fixed log1p (elementwise, nothing fitted, so no leakage; D-074)
LOG1P = ["pop_density", "housing_density", "land_km2", "dist_coast_km", "nri_eal_per_person",
         "nri_ealb_per_building_value"]
FLOOD_ZONE_SLOT = []   # FEMA flood zone shares go here once a file with geometry exists (D-032)
SOCIAL = list(PCA_TRACT_VARS)
FEATURES_MAIN = SOCIAL + HAZARD_POP + NRI + CONTEXT + FLOOD_ZONE_SLOT
FEATURES_LAND = SOCIAL + HAZARD_LAND + NRI + CONTEXT + FLOOD_ZONE_SLOT


def sec(t):
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78, flush=True)


# --------------------------------------------------------------------------
# 1a. inputs
# --------------------------------------------------------------------------

def inventory():
    sec("1a. INPUT INVENTORY")
    rows = []

    def add(name, df, key, note=""):
        miss = df.isna().mean()
        rows.append({"input": name, "rows": len(df), "columns": df.shape[1], "key": key,
                     "key_unique": bool(df[key].is_unique) if key in df else None,
                     "cols_with_missing": int((miss > 0).sum()), "max_missing_share": round(float(miss.max()), 4),
                     "note": note})

    t = pd.read_csv(paths.ANALYSIS_DIR / "tract_analysis.csv", dtype={"GEOID": str})
    add("tract_analysis.csv", t, "GEOID", "698-tract frame, social indicators and investment")
    for f in ("slr_tract.csv", "surge_tract.csv"):
        add(f, pd.read_csv(paths.HAZARDS_DIR / f, dtype={"GEOID": str}), "GEOID", "land shares, 707 tracts")
    n = pd.read_csv(paths.NRI_CSV, dtype={"TRACTFIPS": str}, low_memory=False)
    add("fema_miami_dade_dec_2025.csv", n, "TRACTFIPS", "FEMA NRI; expected annual loss columns only")
    for f in ("exposure_tract.csv", "exposure_blockgroup.csv"):
        add(f, pd.read_csv(paths.EXPOSURE_DIR / f, dtype={"GEOID": str}), "GEOID", "population exposure (prompt 21)")
    g = gpd.read_file(paths.REPO / "output" / "lst" / "lst_blockgroups_miami_dade.geojson")
    add("lst_blockgroups_miami_dade.geojson", pd.DataFrame(g.drop(columns="geometry")), "GEOID",
        "Landsat block group means; used only for the land-weighted comparison feature")
    p = pd.read_csv(paths.PROJECT_CSV, dtype=str, encoding="utf-8-sig")
    add("SCALE-R_Database.csv", p, "Project_ID", "projects; targets only")
    k = pd.read_csv(paths.INVESTMENT_DIR / "project_join_keys.csv", dtype=str)
    add("project_join_keys.csv", k, "Project_ID", "project point to tract")
    rows.append({"input": "FEMA flood zones", "rows": 0, "columns": 0, "key": "", "key_unique": None,
                 "cols_with_missing": 0, "max_missing_share": None,
                 "note": "NOT AVAILABLE: the CSV has no geometry (D-032); empty slot in the feature list"})
    inv = pd.DataFrame(rows)
    print(inv.to_string(index=False))
    inv.to_csv(OUT / "input_inventory.csv", index=False)


# --------------------------------------------------------------------------
# 1b. features
# --------------------------------------------------------------------------

def coast_distance(units):
    """Distance (km) from each tract's land centroid to the nearest marine water polygon.

    Marine water = TIGER area water with MTFCC H2051 (bay, estuary, sound) or
    H2053 (ocean): Biscayne Bay, the Atlantic, Card, Barnes and Little Card Sound.
    """
    w = gpd.read_file(f"zip://{paths.BOUNDARY_DIR / 'tl_2024_12086_areawater.zip'}").to_crs(paths_crs())
    marine = shapely.union_all(w[w.MTFCC.isin(["H2051", "H2053"])].geometry.values)
    cen = units.to_crs(paths_crs()).geometry.representative_point()
    return pd.Series(cen.distance(marine).values / 1000, index=units.GEOID.values)


def paths_crs():
    return "EPSG:6346"


def build_features():
    sec("1b. FEATURES")
    t = load_tract()
    ex = pd.read_csv(paths.EXPOSURE_DIR / "exposure_tract.csv", dtype={"GEOID": str})
    df = t[["GEOID", "population"] + SOCIAL].merge(
        ex[["GEOID", "ALAND", "low_pop_flag", "jurisdiction"] + [c for c in HAZARD_POP + HAZARD_LAND if c in ex]],
        on="GEOID", how="left", validate="1:1")
    # land-weighted mean surface temperature from the block group means (comparison model only)
    g = gpd.read_file(paths.REPO / "output" / "lst" / "lst_blockgroups_miami_dade.geojson")
    g["area"] = g.to_crs(paths_crs()).area
    g["tract"] = g.GEOID.str[:11]
    g = g.dropna(subset=["lst_mean_f"])
    lw = (g.lst_mean_f * g.area).groupby(g.tract).sum() / g.area.groupby(g.tract).sum()
    df["heat_land_mean_f"] = df.GEOID.map(lw)
    # FEMA NRI expected annual loss (no composite scores)
    n = pd.read_csv(paths.NRI_CSV, dtype={"TRACTFIPS": str},
                    usecols=["TRACTFIPS", "POPULATION", "BUILDVALUE", "EAL_VALT", "EAL_VALB"]).set_index("TRACTFIPS")
    df["nri_eal_per_person"] = df.GEOID.map(n.EAL_VALT / n.POPULATION.where(n.POPULATION > 0))
    df["nri_ealb_per_building_value"] = df.GEOID.map(n.EAL_VALB / n.BUILDVALUE.where(n.BUILDVALUE > 0))
    # context
    units = load_units("tract")
    units = units[units.GEOID.isin(df.GEOID)]
    km2 = (df.ALAND / 1e6).where(df.ALAND > 0)
    df["land_km2"] = km2
    df["pop_density"] = df.population / km2
    ej = pd.read_csv(paths.EJSCREEN_PATH, dtype=str, usecols=["ID", "ACSTOTHU"], low_memory=False)
    ej["tract"] = ej.ID.str.zfill(12).str[:11]
    hu = pd.to_numeric(ej.ACSTOTHU, errors="coerce").groupby(ej.tract).sum(min_count=1)
    df["housing_density"] = df.GEOID.map(hu) / km2
    df["dist_coast_km"] = df.GEOID.map(coast_distance(units))
    muni = assign_municipality(units)
    df["in_municipality"] = (df.GEOID.map(muni) != "Unincorporated Miami-Dade").astype(int)
    # centroid for spatial folds
    cen = units.set_index("GEOID").to_crs(paths_crs()).geometry.representative_point()
    df["x_km"] = df.GEOID.map(cen.x / 1000)
    df["y_km"] = df.GEOID.map(cen.y / 1000)
    for c in LOG1P:
        df[c] = np.log1p(df[c])
    print(f"tracts {len(df)}, low population (under 100) {int(df.low_pop_flag.sum())}; log1p applied to {LOG1P}")
    miss = df[FEATURES_MAIN + HAZARD_LAND].isna().sum()
    print("feature missingness (count of 698):")
    print(miss[miss > 0].to_string())
    return df


def screen(df):
    sec("FEATURE SCREEN: Spearman |rho| >= 0.75 among the main features (training tracts)")
    d = df[df.low_pop_flag == 0][FEATURES_MAIN + ["housing_density", "land_km2"]]
    m = d.corr(method="spearman")
    rows = []
    cols = list(m.columns)
    for i, a in enumerate(cols):
        for b in cols[i + 1:]:
            if abs(m.loc[a, b]) >= 0.75:
                rows.append({"a": a, "b": b, "rho": m.loc[a, b]})
    s = pd.DataFrame(rows, columns=["a", "b", "rho"]).sort_values("rho", key=abs, ascending=False)
    print(s.to_string(index=False) if len(s) else "none")
    s.to_csv(OUT / "feature_screen_pairs.csv", index=False)
    return s


def feature_dictionary():
    src = {
        "social": ("CDC/ATSDR SVI 2022 EP_* or ACS 2020-2024 (tract_analysis.csv)", "percent", "none; standardized in fold"),
        "hazard": ("population exposure layers (exposure_tract.csv, prompt 21)", "share 0 to 1 or degrees F", "none; standardized in fold"),
        "land": ("existing land shares (slr_tract.csv, surge_tract.csv, exposure_tract.csv) and Landsat block group means", "share 0 to 1 or degrees F", "comparison model only"),
        "nri": ("FEMA NRI tract table, December 2025 file", "dollars per person per year; dollars per dollar of building value per year", "log1p in fold is not applied; standardized"),
        "context": ("TIGER 2024, ACS 2020-2024, EJScreen ACSTOTHU (ACS 2018-2022)", "see meaning", "standardized in fold"),
    }
    meaning = {
        "slr_3ft_pop_share": "share of residents on land inundated by 3 ft sea level rise (ocean-connected)",
        "surge_cat3_any_pop_share": "share of residents on land with any Category 3 worst-case surge",
        "surge_cat4_any_pop_share": "share of residents on land with any Category 4 worst-case surge",
        "surge_cat3_over3ft_pop_share": "share of residents on land with more than 3 ft of Category 3 surge",
        "heat_lst_popwt_mean_f": "population-weighted mean summer surface temperature, degrees F",
        "heat_p95_pop_share": "share of residents on land at or above the county 95th percentile (113.27 F)",
        "slr_3ft_land_share": "share of land inundated by 3 ft sea level rise",
        "surge_cat3_any_land_share": "share of land with any Category 3 surge",
        "surge_cat4_any_land_share": "share of land with any Category 4 surge",
        "surge_cat3_over3ft_land_share": "share of land with more than 3 ft of Category 3 surge",
        "heat_land_mean_f": "land-area-weighted mean of block group surface temperature, degrees F",
        "heat_p95_land_share": "share of land at or above the county 95th percentile",
        "nri_eal_per_person": "NRI total expected annual loss (EAL_VALT) divided by NRI population",
        "nri_ealb_per_building_value": "NRI building expected annual loss (EAL_VALB) divided by building value (BUILDVALUE)",
        "pop_density": "residents per km2 of land (ACS 2020-2024, TIGER ALAND)",
        "housing_density": "housing units per km2 of land (EJScreen ACSTOTHU summed over block groups)",
        "land_km2": "land area, km2 (TIGER ALAND)",
        "dist_coast_km": "distance from the tract's representative point to Biscayne Bay, the Atlantic or the sounds, km",
        "in_municipality": "1 if the tract centroid is in an incorporated municipality, 0 if unincorporated",
    }
    rows = []
    for v in SOCIAL:
        rows.append({"name": v, "group": "social", "meaning": f"SVI or ACS indicator {v} (PCA input list, D-026)",
                     "source": src["social"][0], "units": src["social"][1], "transform": src["social"][2]})
    for grp, cols in (("hazard", HAZARD_POP), ("land", HAZARD_LAND), ("nri", NRI), ("context", CONTEXT_ALL)):
        for v in cols:
            tf = ("log1p, then standardized in fold" if v in LOG1P else src[grp][2])
            if v in ("housing_density", "land_km2"):
                tf += "; NOT in the main set (0.75 rule with pop_density, D-073)"
            rows.append({"name": v, "group": grp, "meaning": meaning[v], "source": src[grp][0],
                         "units": src[grp][1], "transform": tf})
    rows.append({"name": "fema_flood_zone_share (slot)", "group": "flood_zone",
                 "meaning": "share of residents in FEMA high-risk flood zones (A, V)", "source": "FEMA NFHL, not available",
                 "units": "share", "transform": "PENDING: no geometry in the current file (D-032)"})
    d = pd.DataFrame(rows)
    d.to_csv(OUT / "feature_dictionary.csv", index=False)
    return d


# --------------------------------------------------------------------------
# 1c. targets
# --------------------------------------------------------------------------

def build_targets(df):
    sec("1c. TARGETS")
    p = pd.read_csv(paths.PROJECT_CSV, dtype=str, encoding="utf-8-sig")
    k = pd.read_csv(paths.INVESTMENT_DIR / "project_join_keys.csv", dtype=str)
    p = p.merge(k, on="Project_ID", validate="1:1")
    p["year"] = pd.to_numeric(p.Reported_Year, errors="coerce")
    p["cost"] = pd.to_numeric(p.Estimated_Cost, errors="coerce")
    p["sited"] = p.Spatial_Resolution.isin(SITED)
    cfo = p[p.sited & p.Project_Status.isin(DONE) & p.tract_GEOID.isin(df.GEOID)]
    pl = p[p.sited & (p.Project_Status == "Planned") & p.tract_GEOID.isin(df.GEOID)]
    df["T1"] = df.GEOID.isin(cfo.tract_GEOID).astype(int)
    t = pd.read_csv(paths.ANALYSIS_DIR / "tract_analysis.csv", dtype={"GEOID": str}).set_index("GEOID")
    assert (df.T1.values == t.loc[df.GEOID, "investment_any_single_unit"].values).all(), "T1 disagrees with the analysis table"
    df["T2"] = df.GEOID.isin(pl.tract_GEOID).astype(int)
    df["T2_planned_projects"] = df.GEOID.map(pl.tract_GEOID.value_counts()).fillna(0).astype(int)
    first = cfo.groupby("tract_GEOID").year.min()
    df["first_sited_year"] = df.GEOID.map(first)
    df["T3_train"] = (df.first_sited_year <= 2023).astype(int)
    df["T3_eval_set"] = (df.first_sited_year.isna() | (df.first_sited_year >= 2024)).astype(int)
    df["T3_new_2024_26"] = (df.first_sited_year >= 2024).astype(int)
    dollars = cfo.groupby("tract_GEOID").cost.sum()
    df["sited_dollars"] = df.GEOID.map(dollars).fillna(0)
    df["T5"] = np.where(df.T1 == 1, np.log(df.sited_dollars / df.population.where(df.population > 0)), np.nan)

    print("year distribution of sited completed, funded and ongoing projects (Reported_Year is the year of the "
          "source document, not the build year):")
    print(cfo.year.value_counts().sort_index().to_string())
    proj = cfo.copy()
    proj["T4"] = proj.Infrastructure_Type.isin(["Green", "Blue", "Hybrid"]).astype(int)
    print("\nT4 project types (sited, completed, funded or ongoing):")
    print(proj.Infrastructure_Type.value_counts().to_string())
    print(pd.crosstab(proj.Hazard_Focus, proj.T4, margins=True).to_string())
    tr = df[df.low_pop_flag == 0]
    counts = pd.DataFrame([
        {"target": "T1 sited project present", "units": "tracts", "n": len(tr), "positives": int(tr.T1.sum())},
        {"target": "T2 planned sited project present", "units": "tracts", "n": len(tr), "positives": int(tr.T2.sum())},
        {"target": "T2 among tracts without a T1 project", "units": "tracts", "n": int((tr.T1 == 0).sum()),
         "positives": int(tr[tr.T1 == 0].T2.sum())},
        {"target": "T3 train label: first sited project by 2023", "units": "tracts", "n": len(tr), "positives": int(tr.T3_train.sum())},
        {"target": "T3 test: first sited project 2024 to 2026, among tracts with none by 2023", "units": "tracts",
         "n": int(tr.T3_eval_set.sum()), "positives": int(tr.T3_new_2024_26.sum())},
        {"target": "T4 nature-based or hybrid (green, blue, hybrid) vs gray", "units": "projects",
         "n": int(proj.tract_GEOID.isin(tr.GEOID).sum()), "positives": int(proj[proj.tract_GEOID.isin(tr.GEOID)].T4.sum())},
        {"target": "T5 log sited dollars per resident (tracts with T1)", "units": "tracts", "n": int(tr.T5.notna().sum()),
         "positives": None},
    ])
    counts["base_rate"] = counts.positives / counts.n
    print("\ntarget counts (training tracts: 697, the tract under 100 residents excluded):")
    print(counts.to_string(index=False))
    counts.to_csv(OUT / "target_counts.csv", index=False)
    return df, proj


# --------------------------------------------------------------------------
# 1d. baselines
# --------------------------------------------------------------------------

def logit_pipeline(features, pca=False, weighted=True):
    social = [c for c in features if c in SOCIAL]
    other = [c for c in features if c not in SOCIAL]
    if pca:
        pre = ColumnTransformer([
            ("social", Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler()),
                                 ("pca", PCA(n_components=5, random_state=SEED))]), social),
            ("other", Pipeline([("imp", SimpleImputer(strategy="median", add_indicator=True)),
                                ("sc", StandardScaler())]), other)])
    else:
        pre = Pipeline([("imp", SimpleImputer(strategy="median", add_indicator=True)), ("sc", StandardScaler())])
    clf = LogisticRegression(penalty="l2", class_weight="balanced" if weighted else None, max_iter=5000)
    return Pipeline([("pre", pre), ("clf", clf)])


GRID = {"clf__C": [0.01, 0.1, 1.0, 10.0]}


def fold_sets(df, kind):
    if kind == "spatial":
        return df.fold_spatial.to_numpy(), None
    if kind == "jurisdiction":
        return pd.factorize(df.jurisdiction)[0], None
    return None, StratifiedKFold(10, shuffle=True, random_state=SEED)


def oof_binary(df, X, y, model, kind, inner_groups=True):
    """Out-of-fold probabilities. Nested: C tuned by an inner grouped CV on the training folds."""
    groups, skf = fold_sets(df, kind)
    splits = (GroupKFold(len(np.unique(groups))).split(X, y, groups) if skf is None else skf.split(X, y))
    p = np.full(len(y), np.nan)
    fid = np.full(len(y), -1)
    for i, (tr, te) in enumerate(splits):
        fid[te] = i
        if model == "prevalence":
            p[te] = y[tr].mean()
            continue
        if inner_groups and groups is not None:
            g = groups[tr]
            inner = GroupKFold(min(5, len(np.unique(g)))).split(X.iloc[tr], y[tr], g)
        else:
            inner = StratifiedKFold(5, shuffle=True, random_state=SEED).split(X.iloc[tr], y[tr])
        gs = GridSearchCV(clone(model), GRID, scoring="average_precision", cv=list(inner), n_jobs=1)
        gs.fit(X.iloc[tr], y[tr])
        p[te] = gs.predict_proba(X.iloc[te])[:, 1]
    LAST_FOLDS["fid"] = fid
    return p


LAST_FOLDS = {}


def bin_scores(y, p, fid=None):
    """Pooled out-of-fold scores, plus ROC-AUC and PR-AUC averaged over folds.

    A constant-per-fold predictor (prevalence) has no ranking ability, but
    pooling folds with different base rates gives it a spurious pooled
    ROC-AUC; the fold-averaged value (0.5) is the fair one.
    """
    p = np.clip(p, 1e-6, 1 - 1e-6)
    out = {"n": len(y), "base_rate": y.mean(), "roc_auc": roc_auc_score(y, p) if len(np.unique(y)) > 1 else np.nan,
           "pr_auc": average_precision_score(y, p), "log_loss": log_loss(y, p, labels=[0, 1]),
           "brier": brier_score_loss(y, p)}
    if fid is not None:
        r, a = [], []
        for f in np.unique(fid):
            m = fid == f
            if len(np.unique(y[m])) > 1:
                r.append(0.5 if np.ptp(p[m]) == 0 else roc_auc_score(y[m], p[m]))
                a.append(y[m].mean() if np.ptp(p[m]) == 0 else average_precision_score(y[m], p[m]))
        out["roc_auc_fold_mean"] = np.mean(r)
        out["pr_auc_fold_mean"] = np.mean(a)
        out["pr_auc_fold_mean_base_rate"] = np.mean([y[fid == f].mean() for f in np.unique(fid)
                                                     if len(np.unique(y[fid == f])) > 1])
    return out


def top_share(y, p, q=0.2):
    cut = np.quantile(p, 1 - q)
    return y[p >= cut].sum() / y.sum() if y.sum() else np.nan


def baselines(df, proj):
    sec("1d. BASELINES")
    tr = df[df.low_pop_flag == 0].reset_index(drop=True)
    km = KMeans(N_SPATIAL_FOLDS, random_state=SEED, n_init=10).fit(tr[["x_km", "y_km"]])
    tr["fold_spatial"] = km.labels_
    fs = tr.groupby("fold_spatial").agg(tracts=("GEOID", "size"), T1_rate=("T1", "mean"))
    print("spatial folds (k-means on tract representative points, k = 10):")
    print(fs.to_string(float_format=lambda v: f"{v:.2f}"))
    fs.to_csv(OUT / "spatial_folds.csv")
    tr[["GEOID", "fold_spatial"]].to_csv(OUT / "spatial_fold_assignment.csv", index=False)
    rows, oof_keep = [], {}
    models = {"prevalence": "prevalence",
              "logistic (class-weighted)": logit_pipeline(FEATURES_MAIN),
              "logistic (unweighted)": logit_pipeline(FEATURES_MAIN, weighted=False),
              "logistic, PCA scores in fold": logit_pipeline(FEATURES_MAIN, pca=True),
              "logistic, land shares (comparison)": logit_pipeline(FEATURES_LAND)}
    # T1
    for target, feats_key in (("T1", None), ("T3_train", None)):
        y = tr[target].to_numpy()
        for name, m in models.items():
            if target == "T3_train" and name not in ("prevalence", "logistic (class-weighted)"):
                continue
            feats = FEATURES_LAND if "land" in name else FEATURES_MAIN
            for kind in ("spatial", "random", "jurisdiction"):
                if target == "T3_train" and kind != "spatial":
                    continue
                p = oof_binary(tr, tr[feats], y, m, kind)
                oof_keep[(target, name, kind)] = p
                if target == "T1":
                    rows.append({"target": "T1", "model": name, "cv": kind, **bin_scores(y, p, LAST_FOLDS["fid"])})
    # T2: score with the out-of-fold T1 predictions (spatial)
    for name in ("prevalence", "logistic (class-weighted)", "logistic (unweighted)"):
        p = oof_keep[("T1", name, "spatial")]
        for subset, mask in (("all training tracts", np.ones(len(tr), bool)), ("tracts without a T1 project", tr.T1.values == 0)):
            y = tr.T2.to_numpy()[mask]
            s = bin_scores(y, p[mask])
            s["share_of_positive_tracts_in_top20pct"] = top_share(y, p[mask])
            w = tr.T2_planned_projects.to_numpy()[mask]
            s["share_of_planned_projects_in_top20pct"] = top_share(w, p[mask])
            rows.append({"target": f"T2 ({subset})", "model": f"T1 {name}, spatial OOF", "cv": "spatial", **s})
    # T3: trained on the 2023 label, tested on tracts with no project by 2023
    ev = tr.T3_eval_set.to_numpy() == 1
    for name in ("prevalence", "logistic (class-weighted)"):
        p = oof_keep[("T3_train", name, "spatial")]
        y = tr.T3_new_2024_26.to_numpy()[ev]
        s = bin_scores(y, p[ev])
        s["share_of_positive_tracts_in_top20pct"] = top_share(y, p[ev])
        rows.append({"target": "T3 (first project 2024 to 2026)", "model": f"{name} trained on 2023 label", "cv": "spatial", **s})
    # T4 at project level; folds inherited from the project's tract
    P = proj.merge(tr[["GEOID", "fold_spatial", "jurisdiction"] + FEATURES_MAIN], left_on="tract_GEOID",
                   right_on="GEOID", how="inner")
    scale = pd.get_dummies(P.Spatial_Resolution, prefix="scale", dtype=float)
    focus = pd.get_dummies(P.Hazard_Focus, prefix="focus", dtype=float)
    X4 = pd.concat([P[FEATURES_MAIN].reset_index(drop=True), scale.reset_index(drop=True),
                    focus.reset_index(drop=True)], axis=1)
    X4_focus_only = pd.concat([scale, focus], axis=1).reset_index(drop=True)
    y4 = P.T4.to_numpy()
    for name, m, X in (("prevalence", "prevalence", X4),
                       ("logistic (class-weighted)", logit_pipeline(list(X4.columns)), X4),
                       ("logistic, scale and hazard focus only", logit_pipeline(list(X4_focus_only.columns)), X4_focus_only)):
        for kind in ("spatial", "random", "jurisdiction"):
            p = oof_binary(P, X, y4, m, kind)
            rows.append({"target": "T4 (project level)", "model": name, "cv": kind, **bin_scores(y4, p, LAST_FOLDS["fid"])})
    res = pd.DataFrame(rows)
    print(res.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    res.to_csv(OUT / "baselines_binary.csv", index=False)

    # T5 regression among tracts with a sited project
    sec("T5 BASELINES (log sited dollars per resident, tracts with a sited project)")
    d5 = tr[tr.T5.notna()].reset_index(drop=True)
    y5 = d5.T5.to_numpy()
    rrows = []
    ridge = Pipeline([("imp", SimpleImputer(strategy="median", add_indicator=True)), ("sc", StandardScaler()),
                      ("r", Ridge())])
    for kind in ("spatial", "random", "jurisdiction"):
        if kind == "spatial":
            splits = list(GroupKFold(N_SPATIAL_FOLDS).split(d5, y5, d5.fold_spatial))
        elif kind == "jurisdiction":
            g = pd.factorize(d5.jurisdiction)[0]
            splits = list(GroupKFold(len(np.unique(g))).split(d5, y5, g))
        else:
            splits = list(KFold(10, shuffle=True, random_state=SEED).split(d5))
        for name in ("mean", "ridge"):
            p = np.full(len(y5), np.nan)
            for a, b in splits:
                if name == "mean":
                    p[b] = y5[a].mean()
                else:
                    gs = GridSearchCV(clone(ridge), {"r__alpha": [0.1, 1, 10, 100]}, scoring="neg_mean_squared_error",
                                      cv=KFold(5, shuffle=True, random_state=SEED))
                    gs.fit(d5[FEATURES_MAIN].iloc[a], y5[a])
                    p[b] = gs.predict(d5[FEATURES_MAIN].iloc[b])
            rrows.append({"target": "T5", "model": name, "cv": kind, "n": len(y5),
                          "rmse": mean_squared_error(y5, p) ** 0.5, "mae": mean_absolute_error(y5, p),
                          "r2": r2_score(y5, p), "spearman": stats.spearmanr(y5, p)[0] if name != "mean" else np.nan})
    r5 = pd.DataFrame(rrows)
    print(r5.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    r5.to_csv(OUT / "baselines_T5.csv", index=False)
    return tr


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    np.random.seed(SEED)
    inventory()
    df = build_features()
    screen(df)
    feature_dictionary()
    df, proj = build_targets(df)
    keep = (["GEOID", "jurisdiction", "low_pop_flag", "population", "x_km", "y_km"] + FEATURES_MAIN
            + [c for c in HAZARD_LAND if c not in FEATURES_MAIN]
            + ["T1", "T2", "T2_planned_projects", "first_sited_year", "T3_train", "T3_eval_set", "T3_new_2024_26",
               "sited_dollars", "T5"])
    df[keep].to_csv(OUT / "model_table_tract.csv", index=False)
    proj[["Project_ID", "tract_GEOID", "Project_Status", "Spatial_Resolution", "Infrastructure_Type", "Hazard_Focus",
          "year", "cost", "T4"]].to_csv(OUT / "model_table_projects_T4.csv", index=False)
    baselines(df, proj)


if __name__ == "__main__":
    main()
