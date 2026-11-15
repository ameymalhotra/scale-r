"""Module D, step 2: OLS benchmark and MGWR property value models (spec D1 to D3; D-180).

    /Users/.../Climate-Resilience---Miami-Dade/.venv/bin/python -I scripts/benefit/module_d_fit.py <segment> search
    /Users/.../Climate-Resilience---Miami-Dade/.venv/bin/python -I scripts/benefit/module_d_fit.py <segment> variants

segment: single_family or condo.
"search": the main model. Training sales = main sample (2025 and 2026
qualified sales) minus a 20% hold-out (random within tracts, fixed seed).
OLS on all training sales (standard errors clustered by tract). MGWR on a
stratified sample of 5,000 training sales (each tract in proportion to its
sales). Flood variable = anchored expected yearly damage in $1,000s.
Bandwidths are searched with a floor of 500 neighbours (10% of the sample):
smaller windows made local fits unstable in Stage 3 (D-153). The yes/no
controls (waterfront, pool proxy) are held countywide for the same reason.
"variants": refits with the main bandwidths held fixed:
- flood variable = storms 10% to 2% only (sensitivity);
- training sales including the 2021 to 2024 latest sales that pass the
  non-market rule (D-179), same 5,000 size, same hold-out.
Update (D-184, D-186): the main flood variable is the damage rate
(flood_rate, $100 a year per $100,000 of building value); variants
"frequent" (flood_freq_rate), "dollar" (flood_k, the spec's dollar
variable, for comparison) and "with_older". MGWR_N=all uses every training
sale (the specification asks for 10,000 to 30,000 per model); MGWR_OUTDIR
names a sub-folder for those runs; MGWR_CHUNKS splits the final fit to
limit memory.
"fixed <b1,b2,...>": the main model with bandwidths given (intercept first, then the
variables in XV order), for a rerun after an interrupted final fit (D-193).
MGWR_TOL sets the backfitting tolerance (default 0.00001; 0.00002 for condo,
D-194). Checkpoint (D-194): right after backfitting, the fitted selector is
saved to <segment>_<variant>_checkpoint.pkl and the local coefficients
(no standard errors yet) to <segment>_<variant>_backfit.parquet and .json;
a rerun with the same sales, bandwidths and tolerance resumes from the
checkpoint and goes straight to the standard-error step.
Progress (D-192): step start and end times, percent of the standard-error
step done with time left, a heartbeat every 5 minutes, and a status file
(PROGRESS_STATUS), all through scripts/common/progress.py.
Writes outputs/benefit/module_d/<segment>_<variant>.json and the local
estimates <segment>_<variant>_local.parquet (coefficients and standard errors
in original units, at the calibration points).
"""
import json
import os
import pickle
import sys
import time
from pathlib import Path

import warnings

import numpy as np
import pandas as pd
from scipy.linalg import LinAlgWarning

warnings.filterwarnings("ignore", category=LinAlgWarning)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import paths  # noqa: E402
from progress import Progress, joblib_progress  # noqa: E402

P = None  # set in main(); progress reporting (D-192)

OUT = paths.OUT_BENEFIT / "module_d" / os.environ.get("MGWR_OUTDIR", "")
FLOOD_OF = {"main": "flood_rate", "frequent": "flood_freq_rate", "dollar": "flood_k", "with_older": "flood_rate"}
N_MAX = 30000
SEED = 20261112
N = os.environ.get("MGWR_N", "5000")
N = N_MAX if N == "all" else int(N)
MIN_BW = int(os.environ.get("MGWR_MIN_BW", "500"))
# worker processes for the local fits (joblib); -1 = all cores, 1 = one core (D-189)
JOBS = int(os.environ.get("MGWR_JOBS", "-1"))
# backfitting convergence tolerance (mgwr default 0.00001); condo uses 0.00002 (D-194)
TOL = float(os.environ.get("MGWR_TOL", "1e-5"))
HOLDOUT = 0.2
GLOBAL_VARS = {"waterfront", "pool_proxy"}
XV = {"single_family": ["FLOOD", "log_living_area", "log_lot", "age", "bedrooms", "bathrooms", "pool_proxy",
                        "waterfront", "log_dist_water", "ground_elev_ft", "time"],
      "condo": ["FLOOD", "log_living_area", "age", "bedrooms", "bathrooms", "waterfront", "log_dist_water",
                "ground_elev_ft", "time"]}


def load(segment):
    s = pd.read_parquet(paths.MODULE_D_SALES_PARQUET)
    s = s[s.segment == segment].reset_index(drop=True)
    s["GEOID_tract"] = tract_of(s)
    rng = np.random.default_rng(SEED)
    hold = np.zeros(len(s), bool)
    m = (s.sample_name == "main").to_numpy()
    for tr, idx in s[m].groupby("GEOID_tract").groups.items():
        idx = np.asarray(idx)
        k = int(round(HOLDOUT * len(idx)))
        if k:
            hold[rng.choice(idx, size=k, replace=False)] = True
    s["holdout"] = hold
    return s


def tract_of(s):
    import geopandas as gpd
    bg = gpd.read_file(f"zip://{paths.BOUNDARY_DIR / 'tl_2024_12_bg.zip'}")
    bg = bg[bg.COUNTYFP == "086"].to_crs(32617)[["GEOID", "geometry"]]
    g = gpd.GeoDataFrame(geometry=gpd.points_from_xy(s.x, s.y), crs=32617)
    j = gpd.sjoin(g, bg, predicate="within", how="left")
    j = j[~j.index.duplicated()]
    return j.GEOID.str[:11].to_numpy()


def stratified(s, n, seed):
    rng = np.random.default_rng(seed)
    share = s.GEOID_tract.value_counts(normalize=True)
    take = np.maximum(1, np.round(share * n)).astype(int)
    idx = []
    for tr, k in take.items():
        rows = s.index[s.GEOID_tract == tr]
        idx.extend(rng.choice(rows, size=min(k, len(rows)), replace=False))
    idx = np.array(idx)
    if len(idx) > n:
        idx = rng.choice(idx, size=n, replace=False)
    return s.loc[np.sort(idx)]


def ols(train, test, xs):
    import statsmodels.api as sm
    X = sm.add_constant(train[xs].astype(float))
    m = sm.OLS(train.log_price.to_numpy(), X).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(train.GEOID_tract)[0]})
    pred = m.predict(sm.add_constant(test[xs].astype(float), has_constant="add"))
    err = np.abs(np.exp(test.log_price - pred) - 1)
    return m, err


def moran(x, y, r):
    from esda.moran import Moran
    from libpysal.weights import KNN
    g = pd.DataFrame({"x": np.round(x), "y": np.round(y), "r": r}).groupby(["x", "y"]).r.mean().reset_index()
    w = KNN.from_array(g[["x", "y"]].to_numpy(), k=8)
    w.transform = "r"
    np.random.seed(SEED)
    m = Moran(g.r.to_numpy(), w, permutations=199)
    return {"I": round(float(m.I), 3), "p_sim": float(m.p_sim)}


def smooth_to(cal_xy, cal_vals, bws, tgt_xy, progress=None):
    """Carry local estimates to new points: bisquare kernel over each variable's own adaptive bandwidth
    (nearest calibration points), the same kernel MGWR uses (spec D4, route 2).
    Target points go in blocks so memory stays small: a bandwidth near the whole sample (single-family
    flood, 9,993 of 10,000) times every building would need about 24 GB at once (D-195). Variables
    with the same bandwidth share one neighbour search. Results are the same as without blocks."""
    from scipy.spatial import cKDTree
    tree = cKDTree(cal_xy)
    tgt_xy = np.asarray(tgt_xy)
    out = np.zeros((len(tgt_xy), cal_vals.shape[1]))
    ks = [int(min(max(bw, 2), len(cal_xy))) for bw in bws]
    groups = {k: [j for j, kk in enumerate(ks) if kk == k] for k in dict.fromkeys(ks)}
    for k, js in groups.items():
        step = max(1, int(2e7 // k))          # about 160 MB per array per block
        blocks = range(0, len(tgt_xy), step)
        if progress:
            progress.start(f"carry coefficients, {k} neighbours", total=len(blocks))
        for n, a in enumerate(blocks, 1):
            d, i = tree.query(tgt_xy[a:a + step], k=k)
            h = d[:, -1:] + 1e-9
            w = (1 - (d / h) ** 2) ** 2
            for j in js:
                out[a:a + step, j] = (w * cal_vals[i, j]).sum(1) / w.sum(1)
            if progress:
                progress.update(n)
        if progress:
            progress.end()
    return out


def unscale(p, sd, ymu, ysd):
    """Standardised local coefficients back to original units (log price per unit of x); intercept centred."""
    out = p * np.r_[ysd, ysd / sd.to_numpy()]
    out[:, 0] = ymu + ysd * p[:, 0]
    return out


def mgwr_fit(d, xs, bws=None, pool=None, tag=None):
    import mgwr.gwr
    from mgwr.gwr import MGWR
    from mgwr.sel_bw import Sel_BW
    coords = d[["x", "y"]].to_numpy() + np.random.default_rng(SEED).normal(0, 0.5, (len(d), 2))
    mu, sd = d[xs].mean(), d[xs].std().replace(0, 1)
    X = ((d[xs] - mu) / sd).to_numpy()
    ymu, ysd = d.log_price.mean(), d.log_price.std()
    y = ((d.log_price - ymu) / ysd).to_numpy().reshape(-1, 1)
    names = ["intercept"] + xs
    ckpt = OUT / f"{tag}_checkpoint.pkl" if tag else None
    sel = None
    if ckpt is not None and ckpt.exists():
        with open(ckpt, "rb") as f:
            c = pickle.load(f)
        if c["n"] == len(d) and np.allclose(c["y"], y) and c["tol"] == TOL and (bws is None or list(c["bws"]) == list(bws)):
            sel = c["sel"]
            P.log(f"RESUME from checkpoint {ckpt.name} (backfitting done {c['saved']}); going to the standard-error step")
        else:
            P.log(f"checkpoint {ckpt.name} does not match this run (sales, bandwidths or tolerance); refitting")
    if sel is None:
        sel = backfit(coords, y, X, xs, d, bws, pool)
        if ckpt is not None:
            with open(ckpt, "wb") as f:
                pickle.dump({"sel": sel, "n": len(d), "y": y, "bws": list(sel.bw[0]), "tol": TOL,
                             "saved": time.strftime("%Y-%m-%d %H:%M")}, f)
            loc = pd.DataFrame(unscale(np.asarray(sel.bw[3]), sd, ymu, ysd), columns=[f"b_{n}" for n in names])
            loc["x"], loc["y"] = d.x.to_numpy(), d.y.to_numpy()
            loc.to_parquet(OUT / f"{tag}_backfit.parquet", index=False)
            (OUT / f"{tag}_backfit.json").write_text(json.dumps(
                {"bandwidths": dict(zip(names, np.asarray(sel.bw[0], float).tolist())), "tolerance": TOL,
                 "rounds": int(len(sel.bw[2])), "last_change": float(np.asarray(sel.bw[2])[-1]),
                 "coef_median": dict(zip(names, np.median(loc[[f"b_{n}" for n in names]].to_numpy(), 0).tolist()))},
                indent=2))
            P.log(f"CHECKPOINT saved {ckpt.name} and {tag}_backfit.parquet/.json")
    b = sel.bw[0]
    # standard-error step: run in chunks (n_jobs x MGWR_CHUNKS parts) and report each finished part
    orig = mgwr.gwr.Parallel
    mgwr.gwr.Parallel = joblib_progress(P, "standard errors (final fit)")
    try:
        res = MGWR(coords, y, X, sel, constant=True, n_jobs=JOBS).fit(n_chunks=int(os.environ.get("MGWR_CHUNKS", "1")), pool=pool)
    finally:
        mgwr.gwr.Parallel = orig
    params = unscale(res.params, sd, ymu, ysd)
    bse = res.bse * np.r_[ysd, ysd / sd.to_numpy()]
    bse[:, 0] = res.bse[:, 0] * ysd
    return res, names, np.asarray(b, float), params, bse, coords, (mu, sd, ymu, ysd), sel


def backfit(coords, y, X, xs, d, bws, pool):
    from mgwr.sel_bw import Sel_BW
    sel = Sel_BW(coords, y, X, multi=True, constant=True, n_jobs=JOBS)
    k = X.shape[1] + 1
    P.start(("bandwidth search (backfitting)" if bws is None else "backfitting with fixed bandwidths") + f", tolerance {TOL:g}")
    if bws is None:
        # yes/no controls (waterfront, pool proxy) are all zero in many local windows, which makes local fits
        # singular (D-153); they are held countywide (bandwidth = whole sample)
        n = len(d)
        mins = [MIN_BW] + [n if v in GLOBAL_VARS else MIN_BW for v in xs]
        # backfitting starts from a countywide regression (init_multi = whole sample) instead of a local
        # regression with every variable at once, which is singular where yes/no controls are all zero
        b = sel.search(init_multi=n, multi_bw_min=mins, multi_bw_max=[n] * k, pool=pool,
                       tol_multi=TOL, verbose=os.environ.get("MGWR_VERBOSE", "1") == "1")  # prints each round
    else:
        sel.search(init_multi=len(d), multi_bw_min=list(bws), multi_bw_max=list(bws), pool=pool, tol_multi=TOL)
    P.end()
    P.log(f"backfitting rounds {len(sel.bw[2])}, last change {np.asarray(sel.bw[2])[-1]:.3g} (tolerance {TOL:g})")
    return sel


def summary_local(names, params, bse, bws, filt):
    out = {}
    for j, n in enumerate(names):
        p = params[:, j]
        out[n] = {"bandwidth": float(bws[j]), "p10": float(np.percentile(p, 10)), "median": float(np.median(p)),
                  "p90": float(np.percentile(p, 90)), "se_median": float(np.nanmedian(bse[:, j])),
                  "se_finite_share": float(np.isfinite(bse[:, j]).mean()),
                  "share_significant_corrected": float((filt[:, j] != 0).mean()) if filt is not None else None,
                  "share_negative": float((p < 0).mean())}
    return out


def run(segment, variant, bws=None):
    t0 = time.time()
    P.start(f"{segment} {variant}: load data and OLS")
    s = load(segment)
    xs0 = XV[segment]
    flood = FLOOD_OF[variant]
    s["FLOOD"] = s[flood]
    xs = xs0
    pool_n = int(os.environ.get("MGWR_POOL", "4"))
    pool = None
    if pool_n > 1:
        import multiprocessing as mp
        pool = mp.Pool(pool_n)
    use = (s.sample_name == "main") if variant in ("main", "frequent") else s.sample_name.isin(["main", "older"])
    train = s[use & ~s.holdout].dropna(subset=xs + ["log_price", "x", "y", "GEOID_tract"]).reset_index(drop=True)
    test = s[s.holdout].dropna(subset=xs + ["log_price", "x", "y"]).reset_index(drop=True)
    R = {"segment": segment, "variant": variant, "flood_variable": flood, "training_sales": len(train),
         "holdout_sales": len(test), "variables": xs}
    m, err = ols(train, test, xs)
    R["ols"] = {"flood_coef": float(m.params["FLOOD"]), "flood_se": float(m.bse["FLOOD"]),
                "flood_pct_per_1000": float((np.exp(m.params["FLOOD"]) - 1) * 100),
                "r2": float(m.rsquared), "holdout_median_abs_pct_error": float(np.median(err) * 100),
                "coefs": {k: [float(m.params[k]), float(m.bse[k])] for k in m.params.index},
                "moran_resid": moran(train.x.to_numpy(), train.y.to_numpy(), m.resid.to_numpy())}
    P.end()
    # with_older: same size as the main model, so only the sales mix changes
    n_use = min(N, int((train.sample_name == "main").sum())) if variant == "with_older" else N
    d = (train if len(train) <= n_use else stratified(train, n_use, SEED)).reset_index(drop=True)
    res, names, b, params, bse, coords, scal, sel = mgwr_fit(d, xs, bws, pool, tag=f"{segment}_{variant}")
    try:
        filt = res.filter_tvals()
    except Exception:
        filt = None
    R["mgwr"] = {"sample": len(d), "tracts": int(d.GEOID_tract.nunique()), "aicc": float(res.aicc), "r2": float(res.R2),
                 "bandwidths": dict(zip(names, b.tolist())), "bandwidths_fixed_from_main": bws is not None,
                 "tolerance": TOL, "backfitting_rounds": int(len(sel.bw[2])),
                 "backfitting_last_change": float(np.asarray(sel.bw[2])[-1]),
                 "centre": dict(zip(xs, scal[0].to_numpy().tolist())),
                 "local": summary_local(names, params, bse, b, filt),
                 "moran_resid": moran(d.x.to_numpy(), d.y.to_numpy(), (res.resid_response.ravel() * scal[3]))}
    P.start(f"{segment} {variant}: hold-out error and save")
    # hold-out error: carry local coefficients to held-out sales, predict
    beta = smooth_to(coords, params, b, test[["x", "y"]].to_numpy())
    pred = beta[:, 0] + (beta[:, 1:] * (test[xs].to_numpy(float) - scal[0].to_numpy())).sum(1)
    e = np.abs(np.exp(test.log_price.to_numpy() - pred) - 1)
    test = test.assign(abs_pct_err=e * 100)
    R["mgwr"]["holdout_median_abs_pct_error"] = float(np.median(e) * 100)
    pl = pd.read_csv(paths.OUT_BENEFIT / "stage2" / "tract_places.csv", dtype={"GEOID_tract": str}).set_index("GEOID_tract").place
    test["place"] = test.GEOID_tract.map(pl).fillna("unincorporated")
    g = test.groupby("place").abs_pct_err.agg(["size", "median"])
    R["mgwr"]["holdout_error_by_place"] = g[g["size"] >= 30].round(1).sort_values("median").to_dict("index")
    loc = pd.DataFrame(params, columns=[f"b_{n}" for n in names])
    for j, n in enumerate(names):
        loc[f"se_{n}"] = bse[:, j]
    loc["x"], loc["y"] = d.x.to_numpy(), d.y.to_numpy()
    loc.to_parquet(OUT / f"{segment}_{variant}_local.parquet", index=False)
    R["seconds"] = round(time.time() - t0)
    (OUT / f"{segment}_{variant}.json").write_text(json.dumps(R, indent=2, default=str))
    P.end()
    P.log(f"SAVED {OUT / f'{segment}_{variant}.json'} and the local estimates")
    if pool is not None:
        pool.close()
    print(json.dumps({k: v for k, v in R.items() if k != "ols"}, indent=1, default=str)[:4000], flush=True)
    return R


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"N={N} out={OUT}", flush=True)
    segment, mode = sys.argv[1], sys.argv[2]
    global P
    P = Progress(f"{segment} {mode} {' '.join(sys.argv[3:])}".strip())
    if mode == "search":
        run(segment, "main")
    elif mode == "fixed":
        bws = [float(v) for v in sys.argv[3].split(",")]
        assert len(bws) == len(XV[segment]) + 1, "one bandwidth for the intercept and each variable"
        run(segment, "main", bws)
    else:
        main_json = json.loads((OUT / f"{segment}_main.json").read_text())
        bws = [main_json["mgwr"]["bandwidths"][n] for n in ["intercept"] + XV[segment]]
        for v in sys.argv[3:] or ["frequent", "dollar", "with_older"]:
            run(segment, v, bws)
    P.finish()


if __name__ == "__main__":
    main()
