"""Stage 4, Part A: fit, check and summarize the Bayesian multiscale models.

    bash scripts/ml/run_ml.sh scripts/ml/stage4_graph.py      (once: graph and scaling factor)
    bash scripts/ml/run_ml.sh scripts/ml/stage4_run.py        (everything else; fits are cached in outputs/ml/stage4/fits/)

Models (Part 1 = sited project yes or no; Part 2 = sited dollars per resident, given > 0;
the two parts of the hurdle are fitted separately, which is exact because they share no parameters):
  0a  fixed effects only            0b  + jurisdiction intercept      0c  + BYM2 only
  1   + jurisdiction + BYM2 (main)  2   model 1 + spatially varying hazard slopes (Part 1)
Every model uses the same 30 standardized predictors: the 27 Stage 2 features (one per hazard
family, D-080) and three hazard x vulnerability interactions.
Outputs: outputs/ml/stage4/ (tables, figures, per-tract effects).
"""
import json
import time
import warnings

import arviz as az
import geopandas as gpd
import matplotlib
import numpy as np
import pandas as pd
from esda.moran import Moran
from libpysal.weights import KNN
from scipy.special import expit, logsumexp, polygamma
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score

import ml_common as C
import stage2_models as S2
import stage4_models as M

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

warnings.filterwarnings("ignore")
OUT = M.OUT
FIG = OUT / "figures"
SEED = C.SEED
N_BOOT = 2000
pd.set_option("display.width", 250)


def sec(t):
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78, flush=True)


def diag(post, meta, skip=("eta", "mu_log", "loglik")):
    """R-hat and ESS over every sampled parameter (vector parameters: worst element)."""
    rows = []
    for k, v in post.items():
        if k in skip or k.startswith(("bstruct", "bunstruct", "u_juris", "slope_dev")):
            continue
        arr = v.reshape(v.shape[0], v.shape[1], -1)
        for j in range(arr.shape[2]):
            x = arr[:, :, j]
            rows.append({"param": k if arr.shape[2] == 1 else f"{k}[{j}]",
                         "rhat": float(az.rhat(x)), "ess_bulk": float(az.ess(x, method="bulk")),
                         "ess_tail": float(az.ess(x, method="tail", prob=(0.05, 0.95)))})
    d = pd.DataFrame(rows)
    return {"model": meta["name"], "divergences": meta["divergences"], "tree_depth_hits": meta["max_tree_depth_hits"],
            "max_rhat": d.rhat.max(), "min_ess_bulk": d.ess_bulk.min(), "min_ess_tail": d.ess_tail.min(),
            "n_params": len(d), "worst_rhat_param": d.sort_values("rhat").param.iloc[-1],
            "pass": bool(d.rhat.max() < 1.01 and d.ess_bulk.min() > 400 and d.ess_tail.min() > 400
                         and meta["divergences"] == 0)}, d


def loo_of(post):
    ll = post["loglik"]
    idata = az.from_dict({"posterior": {"alpha": post[[k for k in post if k.startswith("alpha")][0]]},
                          "log_likelihood": {"y": ll}})
    return az.loo(idata, pointwise=True)


def trace_plot(post, names, path, title):
    fig, axes = plt.subplots(len(names), 2, figsize=(10, 2.2 * len(names)))
    for r, k in enumerate(names):
        v = post[k]
        for c in range(v.shape[0]):
            axes[r, 0].plot(v[c], lw=0.4)
            axes[r, 1].hist(v[c], bins=40, histtype="step")
        axes[r, 0].set_ylabel(k, fontsize=8)
    fig.suptitle(title)
    plt.tight_layout()
    plt.savefig(path, dpi=110)
    plt.close()


C2 = (16 * np.sqrt(3) / (15 * np.pi)) ** 2  # logistic-normal approximation (Zeger, Liang and Albert 1988)


def marginal_scale(post, tag="1"):
    """Per-draw factor that turns latent (tract-specific) logit coefficients into population-averaged ones."""
    v = sum(post[k].ravel() ** 2 for k in (f"sigma_juris_{tag}", f"sigma_sp_{tag}") if k in post)
    return 1.0 / np.sqrt(1.0 + C2 * v)


def bin_scores(y, p):
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return {"roc_auc": roc_auc_score(y, p), "pr_auc": average_precision_score(y, p),
            "log_loss": log_loss(y, p), "brier": brier_score_loss(y, p)}


def boot_diff(y, pa, pb, rng):
    n = len(y)
    out = np.empty((N_BOOT, 3))
    for b in range(N_BOOT):
        i = rng.integers(0, n, n)
        a, c = np.clip(pa[i], 1e-6, 1 - 1e-6), np.clip(pb[i], 1e-6, 1 - 1e-6)
        out[b] = [roc_auc_score(y[i], a) - roc_auc_score(y[i], c),
                  average_precision_score(y[i], a) - average_precision_score(y[i], c),
                  log_loss(y[i], a, labels=[0, 1]) - log_loss(y[i], c, labels=[0, 1])]
    return np.percentile(out, [2.5, 97.5], axis=0)


def main():
    t0 = time.time()
    FIG.mkdir(parents=True, exist_ok=True)
    d = M.load_data()
    tr, n = d["tr"], len(d["y1"])
    X, Z = M.design(d["raw"], np.arange(n))
    Xn = X.to_numpy()
    names = list(X.columns)
    hz_cols = [names.index(h) for h in M.HAZ]
    rho_lp, lam = M.pc_rho_logpdf_fn(d["edges"], n, d["scale"])
    nj = len(d["juris_names"])
    base = dict(X=Xn, n_j=nj, juris=d["juris"], edges=d["edges"], scale=d["scale"], rho_logpdf=rho_lp)
    allidx = np.arange(n)
    y1 = d["y1"]
    pos = np.flatnonzero(y1 == 1)
    y2 = np.where(y1 == 1, d["y2"], 1.0)
    pr2 = dict(M.PRIORS["amount"], alpha_mu=float(np.log(d["y2"][pos]).mean()))

    sec("JURISDICTIONS (training tracts)")
    jc = tr.jurisdiction.value_counts().rename("tracts").to_frame()
    jc["sited_rate"] = tr.groupby("jurisdiction").T1.mean()
    jc["under_3_tracts"] = jc.tracts < 3
    print(jc.to_string())
    jc.to_csv(OUT / "jurisdiction_counts.csv")

    # ---------------- prior predictive ----------------
    sec("PRIOR PREDICTIVE CHECKS")
    B = M.icar_basis(d["edges"], n)
    ppri = M.prior_predictive(M.model_binary, dict(base, y=None, obs_idx=allidx, prior=M.PRIORS["binary"], basis=B))["y"]
    share_prior = np.asarray(ppri).mean(axis=1)
    ppri2 = M.prior_predictive(M.model_amount, dict(base, y=None, obs_idx=pos, prior=pr2, family="gamma", basis=B))["y"]
    lp2 = np.log10(np.clip(np.asarray(ppri2), 1e-3, None))
    obs_l = np.log10(d["y2"][pos])
    prior_tab = pd.DataFrame({
        "quantity": ["share of tracts with a project (Part 1)", "median log10 $/resident (Part 2)",
                     "90th pct log10 $/resident (Part 2)"],
        "observed": [y1.mean(), np.median(obs_l), np.percentile(obs_l, 90)],
        "prior_5pct": [np.percentile(share_prior, 5), np.percentile(np.median(lp2, 1), 5), np.percentile(np.percentile(lp2, 90, 1), 5)],
        "prior_median": [np.median(share_prior), np.median(np.median(lp2, 1)), np.median(np.percentile(lp2, 90, 1))],
        "prior_95pct": [np.percentile(share_prior, 95), np.percentile(np.median(lp2, 1), 95), np.percentile(np.percentile(lp2, 90, 1), 95)]})
    print(prior_tab.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    prior_tab.to_csv(OUT / "prior_predictive.csv", index=False)
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.6))
    ax[0].hist(share_prior, bins=40, color="#9bb")
    ax[0].axvline(y1.mean(), color="k", ls="--", label="observed")
    ax[0].set_title("Prior predictive: share of tracts with a sited project")
    ax[0].legend()
    ax[1].hist(np.median(lp2, 1), bins=40, color="#9bb")
    ax[1].axvline(np.median(obs_l), color="k", ls="--", label="observed")
    ax[1].set_title("Prior predictive: median log10 sited $/resident")
    ax[1].legend()
    plt.tight_layout()
    plt.savefig(FIG / "prior_predictive.png", dpi=120)
    plt.close()

    # ---------------- fits ----------------
    sec("FITS (4 chains, NUTS; 2,000 warmup and 2,000 draws, or 5,000 draws for spatial models)")
    specs = {
        "m0a_part1": (M.model_binary, dict(use_juris=False, use_bym2=False), 0.95),
        "m0b_part1": (M.model_binary, dict(use_juris=True, use_bym2=False), 0.95),
        "m0c_part1": (M.model_binary, dict(use_juris=False, use_bym2=True), 0.95),
        "m1_part1": (M.model_binary, dict(), 0.95),
        "m2_part1": (M.model_binary, dict(svc_cols=hz_cols), 0.99),
        "m1_part1_narrow": (M.model_binary, dict(), 0.95),
        "m1_part1_wide": (M.model_binary, dict(), 0.95),
    }
    fits, diags = {}, []
    for name, (model, extra, ta) in specs.items():
        prior = M.PRIORS["binary_narrow" if name.endswith("narrow") else "binary_wide" if name.endswith("wide") else "binary"]
        kw = dict(base, y=y1, obs_idx=allidx, prior=prior, **extra)
        t1 = time.time()
        long = extra.get("use_bym2", True)            # spatial models mix slowly in rho: longer chains
        slow = name in ("m2_part1", "m1_part1_narrow")  # slowest mixing: 10,000 draws kept every 2nd
        post, meta = M.fit(model, kw, name, warmup=3000 if slow else 2000,
                           samples=10000 if slow else 5000 if long else 2000, thinning=2 if slow else 1,
                           target_accept=ta)
        fits[name] = (post, meta, kw)
        dg, _ = diag(post, meta)
        diags.append(dg)
        print(f"  {name}: {time.time() - t1:.0f}s {json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in dg.items()})}", flush=True)
    for fam in ("gamma", "lognormal"):
        name = f"m1_part2_{fam}"
        kw = dict(base, y=y2, obs_idx=pos, prior=pr2, family=fam)
        t1 = time.time()
        post, meta = M.fit(M.model_amount, kw, name, warmup=2000, samples=10000, thinning=2, target_accept=0.95)
        fits[name] = (post, meta, kw)
        dg, _ = diag(post, meta)
        diags.append(dg)
        print(f"  {name}: {time.time() - t1:.0f}s {json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in dg.items()})}", flush=True)
    D = pd.DataFrame(diags)
    D.to_csv(OUT / "diagnostics.csv", index=False)
    for name in ("m1_part1", "m2_part1", "m1_part2_gamma", "m1_part2_lognormal"):
        post = fits[name][0]
        keys = [k for k in post if k.startswith(("sigma_", "rho_", "alpha_", "shape", "sigma_y"))]
        trace_plot(post, keys, FIG / f"trace_{name}.png", f"Trace and posterior: {name}")

    # ---------------- LOO ----------------
    sec("MODEL COMPARISON (PSIS-LOO)")
    loo_rows = []
    for name in ("m0a_part1", "m0b_part1", "m0c_part1", "m1_part1", "m2_part1", "m1_part2_gamma", "m1_part2_lognormal"):
        lo = loo_of(fits[name][0])
        k = np.asarray(lo.pareto_k).ravel()
        ll = fits[name][0]["loglik"].reshape(-1, fits[name][0]["loglik"].shape[-1])
        lppd_i = logsumexp(ll, axis=0) - np.log(ll.shape[0])
        pw_i = ll.var(axis=0, ddof=1)
        loo_rows.append({"model": name, "elpd_loo": float(lo.elpd), "se": float(lo.se), "p_loo": float(lo.p),
                         "pareto_k_over_0.7": int((k > 0.7).sum()), "share_k_over_0.7": float((k > 0.7).mean()),
                         "elpd_waic": float((lppd_i - pw_i).sum()), "p_waic": float(pw_i.sum()),
                         "waic_terms_var_over_0.4": int((pw_i > 0.4).sum())})
    L = pd.DataFrame(loo_rows)
    for part in ("part1", "part2"):
        m = L.model.str.contains(part)
        L.loc[m, "elpd_diff_from_best"] = L.loc[m, "elpd_loo"] - L.loc[m, "elpd_loo"].max()
    print(L.to_string(index=False, float_format=lambda v: f"{v:.2f}"))
    L.to_csv(OUT / "loo.csv", index=False)
    l2 = L.set_index("model").elpd_loo
    # Part 2 family (D-102): among fits that pass every MCMC check and whose PSIS-LOO is reliable
    # (no more than 1% of Pareto k above 0.7), the higher elpd; the posterior predictive checks must also pass
    ok = {f: bool(D.set_index("model").loc[f"m1_part2_{f}", "pass"])
          and L.set_index("model").loc[f"m1_part2_{f}", "share_k_over_0.7"] <= 0.01 for f in ("gamma", "lognormal")}
    cands = [f for f in ok if ok[f]] or ["gamma", "lognormal"]
    fam2 = max(cands, key=lambda f: l2[f"m1_part2_{f}"])
    print(f"Part 2 family: {fam2} (eligible: {ok}; checked against the posterior predictive checks below)")

    # ---------------- posterior predictive ----------------
    sec("POSTERIOR PREDICTIVE CHECKS")
    pp1 = np.asarray(M.predictive(M.model_binary, fits["m1_part1"][0], dict(fits["m1_part1"][2], y=None))["y"])
    share_rep = pp1.mean(axis=1)
    ppc = [{"check": "share of tracts with a sited project", "observed": y1.mean(),
            "rep_mean": share_rep.mean(), "rep_95lo": np.percentile(share_rep, 2.5), "rep_95hi": np.percentile(share_rep, 97.5)},
           {"check": "share of zeros (no sited project)", "observed": 1 - y1.mean(),
            "rep_mean": 1 - share_rep.mean(), "rep_95lo": 1 - np.percentile(share_rep, 97.5), "rep_95hi": 1 - np.percentile(share_rep, 2.5)}]
    qs = (10, 25, 50, 75, 90)
    obs_q = np.percentile(d["y2"][pos], qs)
    for fam in ("gamma", "lognormal"):
        name = f"m1_part2_{fam}"
        rep = np.asarray(M.predictive(M.model_amount, fits[name][0], dict(fits[name][2], y=None))["y"])
        rq = np.percentile(rep, qs, axis=1)
        for q, o, r in zip(qs, obs_q, rq):
            ppc.append({"check": f"{fam}: {q}th percentile of sited $/resident", "observed": o, "rep_mean": float(np.median(r)),
                        "rep_95lo": float(np.percentile(r, 2.5)), "rep_95hi": float(np.percentile(r, 97.5))})
    P = pd.DataFrame(ppc)
    P["inside_95"] = (P.observed >= P.rep_95lo) & (P.observed <= P.rep_95hi)
    print(P.to_string(index=False, float_format=lambda v: f"{v:,.3f}"))
    P.to_csv(OUT / "posterior_predictive.csv", index=False)

    # ---------------- spatial CV, Part 1 ----------------
    sec("SPATIAL CROSS-VALIDATION, PART 1 (Stage 2 folds; each fold 4 chains x 1,000 warmup x 2,000 draws)")
    folds = d["folds"]
    cv, cv_elpd, cv_diag = {}, {}, []
    for name in ("m0a_part1", "m0b_part1", "m0c_part1", "m1_part1", "m2_part1"):
        model, extra, ta = specs[name]
        p = np.full(n, np.nan)
        lp = np.full(n, np.nan)
        for f in np.unique(folds):
            trn, tst = np.flatnonzero(folds != f), np.flatnonzero(folds == f)
            Xf, _ = M.design(d["raw"], trn)
            kw = dict(base, X=Xf.to_numpy(), y=y1, obs_idx=trn, prior=M.PRIORS["binary"], **extra)
            post, meta = M.fit(model, kw, f"cv_{name}_f{int(f)}", chains=4, warmup=1000, samples=2000, target_accept=ta)
            cv_diag.append({"model": name, "fold": int(f), "divergences": meta["divergences"],
                            **{f"rhat_{k}": float(az.rhat(post[k])) for k in ("alpha_1", "sigma_sp_1", "rho_sp_1", "sigma_juris_1")
                               if k in post}})
            e = post["eta"][:, :, tst].reshape(-1, len(tst))
            p[tst] = expit(e).mean(axis=0)
            ll = -np.logaddexp(0, -e) * y1[tst] - np.logaddexp(0, e) * (1 - y1[tst])
            lp[tst] = logsumexp(ll, axis=0) - np.log(ll.shape[0])
        cv[name] = p
        cv_elpd[name] = lp
        print(f"  {name}: {json.dumps({k: round(v, 3) for k, v in bin_scores(y1, p).items()})} ({time.time() - t0:.0f}s)", flush=True)
    CVD = pd.DataFrame(cv_diag)
    CVD.to_csv(OUT / "spatial_cv_fold_diagnostics.csv", index=False)
    print("fold fits: worst hyperparameter R-hat by model",
          CVD.set_index("model").filter(like="rhat").max(axis=1).groupby(level=0).max().round(3).to_dict(),
          "divergences", int(CVD.divergences.sum()))
    for name in ("logistic", "xgb"):
        p, _, _ = S2.nested_oof(tr[C.MAIN], y1, "bin", name, "spatial", folds)
        cv[name] = p
    rows = [{"model": k, **bin_scores(y1, v), "elpd_spatial_cv": float(cv_elpd[k].sum()) if k in cv_elpd else np.nan,
             "elpd_se": float(cv_elpd[k].std(ddof=1) * np.sqrt(n)) if k in cv_elpd else np.nan} for k, v in cv.items()]
    CVt = pd.DataFrame(rows)
    rng = np.random.default_rng(SEED)
    comps = []
    for a in ("m1_part1", "m2_part1"):
        for b in ("logistic", "xgb"):
            lo, hi = boot_diff(y1, cv[a], cv[b], rng)
            sa, sb = bin_scores(y1, cv[a]), bin_scores(y1, cv[b])
            comps.append({"comparison": f"{a} minus {b}",
                          "roc_auc_diff": sa["roc_auc"] - sb["roc_auc"], "roc_95": f"[{lo[0]:+.3f}, {hi[0]:+.3f}]",
                          "pr_auc_diff": sa["pr_auc"] - sb["pr_auc"], "pr_95": f"[{lo[1]:+.3f}, {hi[1]:+.3f}]",
                          "log_loss_diff": sa["log_loss"] - sb["log_loss"], "ll_95": f"[{lo[2]:+.3f}, {hi[2]:+.3f}]",
                          "roc_lo": lo[0], "roc_hi": hi[0], "pr_lo": lo[1], "pr_hi": hi[1], "ll_lo": lo[2], "ll_hi": hi[2]})
    CMP = pd.DataFrame(comps)
    print(CVt.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print(CMP[["comparison", "roc_auc_diff", "roc_95", "pr_auc_diff", "pr_95", "log_loss_diff", "ll_95"]].to_string(
        index=False, float_format=lambda v: f"{v:+.3f}"))
    CVt.to_csv(OUT / "spatial_cv_scores.csv", index=False)
    CMP.to_csv(OUT / "spatial_cv_comparison.csv", index=False)
    pd.DataFrame({"GEOID": tr.GEOID, **{f"oof_{k}": v for k, v in cv.items()},
                  **{f"oof_elpd_{k}": v for k, v in cv_elpd.items()}}).to_csv(OUT / "spatial_cv_oof.csv", index=False)
    erows = []
    for a, b in (("m1_part1", "m0a_part1"), ("m1_part1", "m0b_part1"), ("m1_part1", "m0c_part1"), ("m2_part1", "m1_part1"),
                 ("m0c_part1", "m0a_part1"), ("m0b_part1", "m0a_part1")):
        dd = cv_elpd[a] - cv_elpd[b]
        erows.append({"comparison": f"{a} minus {b}", "elpd_diff": dd.sum(), "se": dd.std(ddof=1) * np.sqrt(n)})
    E = pd.DataFrame(erows)
    print(E.to_string(index=False, float_format=lambda v: f"{v:+.2f}"))
    E.to_csv(OUT / "spatial_cv_elpd_differences.csv", index=False)

    # ---------------- residual Moran's I ----------------
    sec("RESIDUAL MORAN'S I (k = 6, seed 12086)")
    W = KNN.from_array(tr[["x_km", "y_km"]].to_numpy(), k=6)
    W.transform = "r"
    mrows = []
    for name, p, kind in [("m1_part1", cv["m1_part1"], "spatial out-of-fold"), ("m2_part1", cv["m2_part1"], "spatial out-of-fold"),
                          ("logistic", cv["logistic"], "spatial out-of-fold"),
                          ("m1_part1", expit(fits["m1_part1"][0]["eta"]).mean(axis=(0, 1)), "in-sample posterior mean"),
                          ("m0a_part1", expit(fits["m0a_part1"][0]["eta"]).mean(axis=(0, 1)), "in-sample posterior mean")]:
        np.random.seed(SEED)
        mi = Moran(y1 - p, W, permutations=999)
        mrows.append({"model": name, "residuals": kind, "I": mi.I, "p_perm": mi.p_sim})
    MI = pd.DataFrame(mrows)
    print(MI.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    print("Stage 2 reference: XGBoost out-of-fold residual Moran's I 0.132")
    MI.to_csv(OUT / "residual_moran.csv", index=False)

    # ---------------- results from model 1 ----------------
    sec("VARIANCE BY SCALE (model 1, latent scale)")
    post1 = fits["m1_part1"][0]
    vrows = []
    for tag, post, resid, label in (("1", post1, np.pi ** 2 / 3, "Part 1 (logit scale)"),):
        su2 = post[f"sigma_juris_{tag}"] ** 2
        sb2 = post[f"sigma_sp_{tag}"] ** 2
        rho = post[f"rho_sp_{tag}"]
        parts = {"city (jurisdiction)": su2, "neighbourhood (structured spatial)": sb2 * rho,
                 "tract (unstructured)": sb2 * (1 - rho), "individual residual": np.full_like(su2, resid)}
        tot = sum(parts.values())
        for k, v in parts.items():
            vrows.append({"part": label, "component": k, "variance_mean": float(v.mean()),
                          "share_mean": float((v / tot).mean()), "share_95lo": float(np.percentile(v / tot, 2.5)),
                          "share_95hi": float(np.percentile(v / tot, 97.5))})
        vrows.append({"part": label, "component": "BYM2 mixing parameter rho", "variance_mean": float(rho.mean()),
                      "share_95lo": float(np.percentile(rho, 2.5)), "share_95hi": float(np.percentile(rho, 97.5))})
        vrows.append({"part": label, "component": "jurisdiction SD", "variance_mean": float(np.sqrt(su2).mean()),
                      "share_95lo": float(np.percentile(np.sqrt(su2), 2.5)), "share_95hi": float(np.percentile(np.sqrt(su2), 97.5))})
    post = fits[f"m1_part2_{fam2}"][0]
    su2, sb2 = post["sigma_juris_2"] ** 2, post["sigma_sp_2"] ** 2
    resid = polygamma(1, post["shape"]) if fam2 == "gamma" else post["sigma_y"] ** 2
    parts = {"city (jurisdiction)": su2, "neighbourhood (structured spatial)": sb2,
             "tract and project residual": resid}
    tot = sum(parts.values())
    for k, v in parts.items():
        vrows.append({"part": f"Part 2 (log dollars, {fam2})", "component": k, "variance_mean": float(v.mean()),
                      "share_mean": float((v / tot).mean()), "share_95lo": float(np.percentile(v / tot, 2.5)),
                      "share_95hi": float(np.percentile(v / tot, 97.5))})
    V = pd.DataFrame(vrows)
    print(V.to_string(index=False, float_format=lambda v: f"{v:.3f}"))
    V.to_csv(OUT / "variance_by_scale.csv", index=False)

    sec("FIXED EFFECTS (model 1)")
    frows = []
    for part, key, post in (("Part 1", "beta_1", post1), ("Part 2", "beta_2", fits[f"m1_part2_{fam2}"][0])):
        b = post[key].reshape(-1, post[key].shape[-1])
        for j, nm in enumerate(names):
            x = b[:, j]
            eff = np.exp(x) if part == "Part 1" else (np.exp(x) - 1) * 100
            pa = {}
            if part == "Part 1":
                xm = x * marginal_scale(post)
                pa = {"marginal_coef_mean": xm.mean(), "marginal_or": np.exp(xm).mean(),
                      "marginal_or_95lo": np.percentile(np.exp(xm), 2.5), "marginal_or_95hi": np.percentile(np.exp(xm), 97.5)}
            frows.append({**pa, "part": part, "feature": nm, "plain": C.plain(nm) if ":" not in nm else f"{C.plain(nm.split(':')[0])} x vulnerability",
                          "coef_mean": x.mean(), "coef_95lo": np.percentile(x, 2.5), "coef_95hi": np.percentile(x, 97.5),
                          ("odds_ratio" if part == "Part 1" else "pct_change"): np.mean(eff),
                          "eff_95lo": np.percentile(eff, 2.5), "eff_95hi": np.percentile(eff, 97.5),
                          "interval_excludes_0": bool(np.percentile(x, 2.5) > 0 or np.percentile(x, 97.5) < 0),
                          "prob_positive": float((x > 0).mean())})
    F = pd.DataFrame(frows)
    print(F[["part", "feature", "coef_mean", "coef_95lo", "coef_95hi", "eff_95lo", "eff_95hi", "interval_excludes_0"]].to_string(
        index=False, float_format=lambda v: f"{v:+.3f}"))
    F.to_csv(OUT / "fixed_effects.csv", index=False)

    sec("HAZARD x VULNERABILITY: hazard slope (log-odds per SD) at low, average and high vulnerability")
    hrows = []
    b = post1["beta_1"].reshape(-1, len(names))
    for h, inter in zip(M.HAZ, M.INTER):
        for v in (-1.0, 0.0, 1.0):
            s = b[:, names.index(h)] + v * b[:, names.index(inter)]
            hrows.append({"hazard": C.plain(h), "vulnerability_sd": v, "slope_mean": s.mean(),
                          "slope_95lo": np.percentile(s, 2.5), "slope_95hi": np.percentile(s, 97.5), "prob_positive": (s > 0).mean()})
    H = pd.DataFrame(hrows)
    print(H.to_string(index=False, float_format=lambda v: f"{v:+.3f}"))
    H.to_csv(OUT / "hazard_by_vulnerability.csv", index=False)

    sec("CITY EFFECTS (model 1, Part 1)")
    u = post1["u_juris_1"].reshape(-1, nj)
    cty = pd.DataFrame({"jurisdiction": d["juris_names"], "effect_mean": u.mean(0), "effect_95lo": np.percentile(u, 2.5, 0),
                        "effect_95hi": np.percentile(u, 97.5, 0), "prob_positive": (u > 0).mean(0)})
    cty = cty.merge(jc[["tracts", "sited_rate"]], left_on="jurisdiction", right_index=True).sort_values("effect_mean")
    cty["under_3_tracts"] = cty.tracts < 3
    print(cty.to_string(index=False, float_format=lambda v: f"{v:+.3f}"))
    cty.to_csv(OUT / "city_effects.csv", index=False)
    fig, ax = plt.subplots(figsize=(7, 9))
    yy = np.arange(len(cty))
    ax.errorbar(cty.effect_mean, yy, xerr=[cty.effect_mean - cty.effect_95lo, cty.effect_95hi - cty.effect_mean],
                fmt="o", color="#01321e", ecolor="#9bb", capsize=2)
    ax.axvline(0, color="k", lw=0.8)
    ax.set_yticks(yy)
    ax.set_yticklabels([f"{j} ({t}{'*' if t < 3 else ''})" for j, t in zip(cty.jurisdiction, cty.tracts)], fontsize=8)
    ax.set_xlabel("jurisdiction effect on the log-odds of a sited project (95% interval)")
    ax.set_title("City effects, model 1 (* fewer than 3 tracts: strongly shrunk)")
    plt.tight_layout()
    plt.savefig(FIG / "city_effects.png", dpi=130)
    plt.close()

    sec("PER-TRACT EFFECTS AND MAPS")
    geo = gpd.read_file(f"zip://{C.paths.BOUNDARY_DIR / 'tl_2024_12_tract.zip'}", where="COUNTYFP='086'")
    geo = geo.set_index("GEOID").loc[tr.GEOID].reset_index().to_crs(6346)
    eff = pd.DataFrame({"GEOID": tr.GEOID, "jurisdiction": tr.jurisdiction,
                        "city_effect": u.mean(0)[d["juris"]],
                        "neighbourhood_effect": post1["bstruct_sp_1"].reshape(-1, n).mean(0),
                        "tract_effect": post1["bunstruct_sp_1"].reshape(-1, n).mean(0),
                        "p_sited_insample": expit(post1["eta"]).mean(axis=(0, 1)),
                        "p_sited_spatial_oof_m1": cv["m1_part1"]})
    post2 = fits["m2_part1"][0]
    b2 = post2["beta_1"].reshape(-1, len(names))
    for k, h in enumerate(M.HAZ):
        sl = b2[:, names.index(h)][:, None] + post2[f"slope_dev{k}_1"].reshape(-1, n)
        eff[f"svc_{h}_mean"] = sl.mean(0)
        eff[f"svc_{h}_prob_positive"] = (sl > 0).mean(0)
        eff[f"svc_{h}_class"] = np.select([eff[f"svc_{h}_prob_positive"] >= 0.9, eff[f"svc_{h}_prob_positive"] <= 0.1],
                                          ["positive", "negative"], "near zero or uncertain")
    eff.to_csv(OUT / "tract_effects.csv", index=False)
    print(eff.describe().T[["mean", "std", "min", "max"]].round(3).to_string())
    for k, h in enumerate(M.HAZ):
        print(f"  model 2 {C.plain(h)}: {eff[f'svc_{h}_class'].value_counts().to_dict()}")
    g = geo.merge(eff, on="GEOID")
    fig, axes = plt.subplots(1, 2, figsize=(12, 7))
    for ax, col, title in ((axes[0], "neighbourhood_effect", "Neighbourhood (structured spatial) effect"),
                           (axes[1], "city_effect", "City (jurisdiction) effect")):
        lim = np.nanmax(np.abs(g[col]))
        g.plot(column=col, cmap="RdBu_r", vmin=-lim, vmax=lim, legend=True, ax=ax, linewidth=0)
        ax.set_title(title + "\n(log-odds of a sited project; red = more than features predict)", fontsize=9)
        ax.set_axis_off()
    plt.tight_layout()
    plt.savefig(FIG / "map_spatial_and_city_effects.png", dpi=120)
    plt.close()
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))
    for k, h in enumerate(M.HAZ):
        col = f"svc_{h}_mean"
        lim = np.nanmax(np.abs(g[col]))
        g.plot(column=col, cmap="RdBu_r", vmin=-lim, vmax=lim, legend=True, ax=axes[0, k], linewidth=0)
        axes[0, k].set_title(f"Model 2: local effect of {C.plain(h)}\n(log-odds per SD)", fontsize=9)
        g.plot(column=f"svc_{h}_prob_positive", cmap="PuOr", vmin=0, vmax=1, legend=True, ax=axes[1, k], linewidth=0)
        axes[1, k].set_title("probability the local effect is positive", fontsize=9)
        for a in axes[:, k]:
            a.set_axis_off()
    plt.tight_layout()
    plt.savefig(FIG / "map_model2_hazard_effects.png", dpi=110)
    plt.close()

    sec("PRIOR SENSITIVITY (model 1, Part 1)")
    srows = []
    for name in ("m1_part1_narrow", "m1_part1", "m1_part1_wide"):
        post = fits[name][0]
        bb = post["beta_1"].reshape(-1, len(names))
        row = {"model": name, "sigma_juris": post["sigma_juris_1"].mean(), "sigma_spatial": post["sigma_sp_1"].mean(),
               "rho": post["rho_sp_1"].mean()}
        for nm in M.HAZ + ["dist_coast_km", "pop_density", "in_municipality"] + M.INTER:
            x = bb[:, names.index(nm)]
            row[nm] = f"{x.mean():+.2f} [{np.percentile(x, 2.5):+.2f}, {np.percentile(x, 97.5):+.2f}]"
            xm = x * marginal_scale(post)
            row[f"{nm} (population-averaged)"] = f"{xm.mean():+.2f} [{np.percentile(xm, 2.5):+.2f}, {np.percentile(xm, 97.5):+.2f}]"
        tot = post["sigma_juris_1"] ** 2 + post["sigma_sp_1"] ** 2
        row["latent_icc"] = f"{(tot / (tot + np.pi ** 2 / 3)).mean():.2f}"
        srows.append(row)
    S = pd.DataFrame(srows)
    print(S.T.to_string())
    S.to_csv(OUT / "prior_sensitivity.csv", index=False)
    sec("HEAT GAP: does the surface-heat association hold after controls?")
    heat = "heat_lst_popwt_mean_f"
    Xh = X[[heat]].to_numpy()
    terc = pd.qcut(tr[heat], 3, labels=["coolest", "middle", "hottest"])
    desc = pd.DataFrame({"tercile": terc, "T1": y1, "sited": tr.sited_dollars, "pop": tr.population}).groupby(
        "tercile", observed=True).agg(tracts=("T1", "size"), share_with_sited_project=("T1", "mean"),
                                      sited_dollars=("sited", "sum"), residents=("pop", "sum"))
    desc["sited_dollars_per_resident_pooled"] = desc.sited_dollars / desc.residents
    print(desc.to_string(float_format=lambda v: f"{v:,.3f}"))
    grows = []
    hu1, _ = M.fit(M.model_binary, dict(base, X=Xh, y=y1, obs_idx=allidx, prior=M.PRIORS["binary"], use_juris=False,
                                        use_bym2=False), "heat_only_part1", warmup=1000, samples=1000)
    hu2, _ = M.fit(M.model_amount, dict(base, X=Xh, y=y2, obs_idx=pos, prior=pr2, family="gamma", use_juris=False,
                                        use_bym2=False), "heat_only_part2", warmup=1000, samples=1000)
    for part, label, post, col in (("Part 1", "heat alone", hu1["beta_1"][..., 0], None),
                                   ("Part 1", "model 0a (all controls, no city or spatial effects)",
                                    fits["m0a_part1"][0]["beta_1"], heat),
                                   ("Part 1", "model 1 (all controls, city and spatial effects)", post1["beta_1"], heat),
                                   ("Part 1", "model 1, population-averaged",
                                    post1["beta_1"] * marginal_scale(post1).reshape(post1["beta_1"].shape[:2] + (1,)), heat),
                                   ("Part 2", "heat alone", hu2["beta_2"][..., 0], None),
                                   ("Part 2", "model 1 (all controls, city and spatial effects)",
                                    fits[f"m1_part2_{fam2}"][0]["beta_2"], heat)):
        x = (post[..., names.index(col)] if col else post).ravel()
        eff = np.exp(x) if part == "Part 1" else (np.exp(x) - 1) * 100
        grows.append({"part": part, "model": label, "coef_mean": x.mean(), "coef_95lo": np.percentile(x, 2.5),
                      "coef_95hi": np.percentile(x, 97.5), "effect_mean": eff.mean(), "effect_95lo": np.percentile(eff, 2.5),
                      "effect_95hi": np.percentile(eff, 97.5), "prob_negative": (x < 0).mean(),
                      "effect_unit": "odds ratio per SD of heat" if part == "Part 1" else "% change in $/resident per SD of heat"})
    for ctl in ("pop_density", "dist_coast_km", "in_municipality", "nri_eal_per_person", "vulnerability"):
        Xc = np.column_stack([Xh, (Z[ctl] if ctl == "vulnerability" else X[ctl]).to_numpy()])
        hc, _ = M.fit(M.model_binary, dict(base, X=Xc, y=y1, obs_idx=allidx, prior=M.PRIORS["binary"], use_juris=False,
                                           use_bym2=False), f"heat_plus_{ctl}_part1", warmup=1000, samples=1000)
        x = hc["beta_1"][..., 0].ravel()
        grows.append({"part": "Part 1", "model": f"heat + {C.plain(ctl) if ctl != 'vulnerability' else 'vulnerability (RC1)'} only",
                      "coef_mean": x.mean(), "coef_95lo": np.percentile(x, 2.5), "coef_95hi": np.percentile(x, 97.5),
                      "effect_mean": np.exp(x).mean(), "effect_95lo": np.percentile(np.exp(x), 2.5),
                      "effect_95hi": np.percentile(np.exp(x), 97.5), "prob_negative": (x < 0).mean(),
                      "effect_unit": "odds ratio per SD of heat"})
    print("Spearman correlation of heat with:", {c: round(float(tr[heat].corr(tr[c], method="spearman")), 2)
                                                for c in ("pop_density", "dist_coast_km", "in_municipality", "nri_eal_per_person")})
    G = pd.DataFrame(grows)
    print(G.to_string(index=False, float_format=lambda v: f"{v:+.3f}"))
    print(f"one SD of heat = {tr[heat].std(ddof=0):.2f} F")
    desc.to_csv(OUT / "heat_terciles.csv")
    G.to_csv(OUT / "heat_gap_after_controls.csv", index=False)

    json.dump({"elapsed_s": round(time.time() - t0), "rho_pc_lambda": float(lam), "predictors": names,
               "missing_imputed": {k: int(v) for k, v in d["missing"].items()}}, open(OUT / "run_meta.json", "w"), indent=1)
    print(f"\ndone in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
