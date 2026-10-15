"""Principal component analysis of the vulnerability indicators, tract and
block group analysed separately (never mixed). Inputs are ONLY the lists
recorded in DATA_PROCESSING.md Sec 7 (analysis_variables.PCA_TRACT_VARS,
PCA_BG_VARS, PCA_BG_VARS_REDUCED). No hazard or investment column is read
into any PCA. No modelling. No imputation: complete cases only, n reported.

Per run
  - preparation: z-scores (primary) and z-scored ranks (sensitivity, average
    ranks on the complete-case sample, consistent with the Spearman screen)
  - suitability: KMO (overall and per variable, flag < 0.5), Bartlett's test
  - eigenvalues, variance explained, and three retention criteria side by
    side: eigenvalue > 1, scree plot, Horn's parallel analysis (95th
    percentile of eigenvalues from random normal data of the same n and p)
  - unrotated loadings, varimax (Kaiser-normalised) loadings for the
    retained components, communalities (flag < 0.5)
  - primary vs rank run compared by Tucker's congruence coefficient on
    matched varimax components (>= 0.95 treated as equal, 0.85-0.95 as fair
    similarity; Lorenzo-Seva and ten Berge 2006)

The number of components and the component names are PROPOSALS for the user
to confirm (PROPOSED_K, SCREE_ELBOW, SUGGESTED_NAMES below); nothing here is
final. Component scores are saved, not used.

Usage:   python scripts/pca_analysis.py
Outputs: output/pca/*  and  pca_analysis.md
"""
import sys
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.optimize import linear_sum_assignment
from scipy.stats import chi2

sys.path.insert(0, str(Path(__file__).resolve().parent))
from analysis_variables import (  # noqa: E402
    PCA_BG_HIGH_MISSING, PCA_BG_VARS, PCA_BG_VARS_REDUCED, PCA_TRACT_VARS,
)
from professor_labels import BG_VARS, TRACT_VARS, ordered_vars  # noqa: E402
from scaler_projects import BASE, OUTPUT_DIR  # noqa: E402

OUT = OUTPUT_DIR / "pca"
REPORT = BASE / "pca_analysis.md"

LOAD_CUT = 0.5          # loadings reported as "salient" at |l| >= this
KMO_FLAG = 0.5
COMMUNALITY_FLAG = 0.5
PA_ITER = 1000
PA_PCTL = 95
SEED = 20260927
LOW_N = 1200            # below this, the block-group reduced run is also reported

# ---------------------------------------------------------------------------
# PROPOSALS, pending the user's confirmation. Set after reading the criteria
# table and the scree plots in output/pca/. Keys are run ids.
# ---------------------------------------------------------------------------
SCREE_ELBOW = {         # run id -> reading of output/pca/scree_<run>.png
    "tract": "3 (sharp break after 1; curve flattens after 3)",
    "bg24": "3 (sharp break after 1; curve flattens after 3)",
    "bg21": "3 (sharp break after 1; curve flattens after 3)",
}
PROPOSED_K = {          # run id -> (k, rationale)
    "tract": (5, "Eigenvalue above 1 and parallel analysis agree on 5 in the standardized "
                 "run, and PC5 (1.225) clears the parallel-analysis line (1.161) by a clear "
                 "margin. The scree reads 3, but 3 components leave seven variables with "
                 "communality below 0.5, and none of the three replicates cleanly under ranks "
                 "(congruence 0.80 to 0.85). **Caveats:** RC5 is essentially a single "
                 "variable (group quarters), and RC4 and RC5 do not replicate in the rank "
                 "run, where PC5 falls below the parallel-analysis line (rank run: parallel "
                 "analysis 4). **Alternative: k = 4.** RC1 to RC3 then replicate at 0.95 or "
                 "above; RC4 (multi-unit versus minority) still does not (0.56); group "
                 "quarters is left almost unexplained (communality 0.06)."),
    "bg24": (6, "Parallel analysis gives 6 in both the standardized and rank runs; eigenvalue "
                "above 1 gives 7 in the standardized run (PC7 = 1.06, below the "
                "parallel-analysis line of 1.18) and is known to over-extract. All six "
                "components replicate under ranks (congruence 0.95 or above for five, 0.949 "
                "for the sixth). The scree reads 3, but 3 components leave 16 of 24 variables "
                "with communality below 0.5. **Caveat:** n = 518 complete cases."),
    "bg21": (4, "Parallel analysis gives 4 in both the standardized and rank runs. PC5 "
                "(1.136) sits on the parallel-analysis line (1.137); re-running the "
                "simulation with five other seeds put the line between 1.135 and 1.137, so "
                "PC5 is indistinguishable from random-data noise at the 95th percentile. "
                "Eigenvalue above 1 gives 6 and is known to over-extract; the scree reads 3, "
                "but 3 components replicate poorly under ranks (congruence as low as 0.24). "
                "**Alternative: k = 5**, which adds a plumbing and kitchen component (the "
                "counterpart of RC6 in the 24-variable version) but replicates less well "
                "under ranks (lowest congruence 0.84 against 0.88 at k = 4)."),
}
SUGGESTED_NAMES = {     # run id -> {"RC1": "name", ...}; suggestions only
    "tract": {"RC1": "General socioeconomic disadvantage",
              "RC2": "Older, non-working and disabled households",
              "RC3": "Families with children and unemployment",
              "RC4": "Multi-unit housing versus minority share",
              "RC5": "Group quarters"},
    "bg24": {"RC1": "Low income, low education and people of colour",
             "RC2": "Renters without a vehicle or broadband",
             "RC3": "Housing costs and family income",
             "RC4": "Older residents versus young families",
             "RC5": "Low life expectancy and unemployment",
             "RC6": "Incomplete plumbing and kitchens"},
    "bg21": {"RC1": "Low income, low education and people of colour",
             "RC2": "Poverty, renting and lack of vehicle or broadband",
             "RC3": "Older residents versus single-parent families",
             "RC4": "Incomplete kitchens"},
}

HEADLINE = {
    "tract": ["EP_NOVEH", "EP_MUNIT", "EP_NOINT", "EP_MINRTY"],
    "bg": ["no_vehicle", "no_broadband", "PEOPCOLORPCT"],
}


# ---------------------------------------------------------------------------
# linear algebra
# ---------------------------------------------------------------------------

def prepare(x, method):
    if method == "rank":
        x = x.rank(method="average")
    return (x - x.mean()) / x.std(ddof=1)


def eig_desc(r):
    vals, vecs = np.linalg.eigh(r)
    order = np.argsort(vals)[::-1]
    return vals[order], vecs[:, order]


def orient(mat):
    """Flip each column so its largest-magnitude entry is positive."""
    idx = np.abs(mat).argmax(axis=0)
    signs = np.sign(mat[idx, np.arange(mat.shape[1])])
    signs[signs == 0] = 1
    return signs


def varimax(loadings, max_iter=1000, tol=1e-10):
    """Kaiser-normalised varimax. Returns rotated loadings and rotation T,
    with rotated = loadings @ T (T orthogonal)."""
    h = np.sqrt((loadings ** 2).sum(axis=1))
    a = loadings / h[:, None]
    p, k = a.shape
    t = np.eye(k)
    d = 0.0
    for _ in range(max_iter):
        lam = a @ t
        u, s, vh = np.linalg.svd(a.T @ (lam ** 3 - lam @ np.diag((lam ** 2).sum(axis=0)) / p))
        t = u @ vh
        d_old, d = d, s.sum()
        if d_old and d / d_old < 1 + tol:
            break
    return loadings @ t, t


def kmo(r):
    inv = np.linalg.inv(r)
    d = np.sqrt(np.outer(np.diag(inv), np.diag(inv)))
    partial = -inv / d
    off = ~np.eye(len(r), dtype=bool)
    r2 = np.where(off, r ** 2, 0)
    p2 = np.where(off, partial ** 2, 0)
    per_var = r2.sum(axis=0) / (r2.sum(axis=0) + p2.sum(axis=0))
    overall = r2.sum() / (r2.sum() + p2.sum())
    return overall, per_var


def bartlett(r, n):
    p = len(r)
    _, logdet = np.linalg.slogdet(r)
    stat = -(n - 1 - (2 * p + 5) / 6) * logdet
    df = p * (p - 1) / 2
    return stat, df, chi2.sf(stat, df)


def parallel_analysis(n, p, rng):
    sims = np.empty((PA_ITER, p))
    for i in range(PA_ITER):
        sims[i] = np.sort(np.linalg.eigvalsh(np.corrcoef(rng.standard_normal((n, p)),
                                                         rowvar=False)))[::-1]
    return sims.mean(axis=0), np.percentile(sims, PA_PCTL, axis=0)


def congruence(a, b):
    """Tucker's phi between every column of a and every column of b."""
    num = a.T @ b
    den = np.sqrt(np.outer((a ** 2).sum(axis=0), (b ** 2).sum(axis=0)))
    return num / den


def kaiser_count(vals):
    return int((vals > 1).sum())


def pa_count(vals, pa95):
    k = 0
    for v, ref in zip(vals, pa95):
        if v > ref:
            k += 1
        else:
            break
    return k


# ---------------------------------------------------------------------------
# one PCA run
# ---------------------------------------------------------------------------

def pca_run(x, method, k=None):
    z = prepare(x, method)
    r = np.corrcoef(z.values, rowvar=False)
    vals, vecs = eig_desc(r)
    vecs = vecs * orient(vecs)
    load = vecs * np.sqrt(vals)
    out = {"z": z, "r": r, "vals": vals, "vecs": vecs, "load": load}
    if k is not None:
        out.update(rotate(z, vals, vecs, load, k))
    return out


def rotate(z, vals, vecs, load, k):
    rot, t = varimax(load[:, :k])
    # order rotated components by variance carried, then orient
    ss = (rot ** 2).sum(axis=0)
    order = np.argsort(ss)[::-1]
    rot, t = rot[:, order], t[:, order]
    s = orient(rot)
    rot, t = rot * s, t * s
    f = z.values @ vecs[:, :k] / np.sqrt(vals[:k])      # unit-variance PC scores
    return {"k": k, "rot": rot, "T": t, "pc_scores": f, "rc_scores": f @ t,
            "communality": (load[:, :k] ** 2).sum(axis=1)}


def analyse(df, varlist, varmap, run_id, title, rng):
    varlist = [v for v in ordered_vars(varmap) if v in varlist]
    x = df[varlist].dropna()
    n, p = x.shape
    drop_reason = df[varlist].isna().sum()
    prim = pca_run(x, "standardized")
    rank = pca_run(x, "rank")
    pa_mean, pa95 = parallel_analysis(n, p, rng)
    kmo_all, kmo_var = kmo(prim["r"])
    bart = bartlett(prim["r"], n)
    kmo_all_r, kmo_var_r = kmo(rank["r"])
    bart_r = bartlett(rank["r"], n)

    crit = {"kaiser": kaiser_count(prim["vals"]), "pa": pa_count(prim["vals"], pa95),
            "scree": SCREE_ELBOW.get(run_id),
            "kaiser_rank": kaiser_count(rank["vals"]), "pa_rank": pa_count(rank["vals"], pa95)}
    if run_id in PROPOSED_K:
        k, why = PROPOSED_K[run_id]
    else:
        k, why = crit["pa"], "PLACEHOLDER: no proposal recorded yet; parallel-analysis count used"
        print(f"  [{run_id}] no PROPOSED_K entry; using parallel analysis k={k}")
    prim.update(rotate(prim["z"], prim["vals"], prim["vecs"], prim["load"], k))
    rank.update(rotate(rank["z"], rank["vals"], rank["vecs"], rank["load"], k))

    # match rank components to primary components by |congruence|
    phi = congruence(prim["rot"], rank["rot"])
    ri, ci = linear_sum_assignment(-np.abs(phi))
    match = []
    for a, b in zip(ri, ci):
        sign = np.sign(phi[a, b]) or 1
        score_r = np.corrcoef(prim["rc_scores"][:, a], sign * rank["rc_scores"][:, b])[0, 1]
        match.append({"primary": f"RC{a + 1}", "rank": f"RC{b + 1}", "phi": phi[a, b],
                      "score_corr": score_r})
    phi_unrot = np.diag(congruence(prim["load"][:, :k], rank["load"][:, :k]))

    return {"id": run_id, "title": title, "vars": varlist, "varmap": varmap,
            "n": n, "n_total": len(df), "p": p, "missing": drop_reason,
            "prim": prim, "rank": rank, "pa_mean": pa_mean, "pa95": pa95,
            "kmo": (kmo_all, kmo_var), "bart": bart,
            "kmo_rank": (kmo_all_r, kmo_var_r), "bart_rank": bart_r,
            "crit": crit, "k": k, "k_why": why, "match": match,
            "phi_unrot": phi_unrot, "index": x.index}


# ---------------------------------------------------------------------------
# figures and files
# ---------------------------------------------------------------------------

def scree_plot(res):
    p = res["p"]
    xs = np.arange(1, p + 1)
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(xs, res["prim"]["vals"], marker="o", lw=2, color="#1f4e79",
            label="Observed eigenvalue (standardized)")
    ax.plot(xs, res["rank"]["vals"], marker="s", lw=1.2, ls=":", color="#6c8ebf",
            label="Observed eigenvalue (rank sensitivity)")
    ax.plot(xs, res["pa95"], lw=1.5, ls="--", color="#c0504d",
            label=f"Parallel analysis, {PA_PCTL}th percentile")
    ax.axhline(1, color="#7f7f7f", lw=1, label="Eigenvalue = 1")
    ax.axvline(res["k"] + 0.5, color="#333333", lw=0.8, ls="-.",
               label=f"Proposed k = {res['k']} (pending confirmation)")
    ax.set_xticks(xs)
    ax.set_xlabel("Component")
    ax.set_ylabel("Eigenvalue")
    ax.set_title(f"{res['title']}: scree plot (n = {res['n']:,}, {p} variables)")
    ax.grid(axis="y", color="#e0e0e0", lw=0.6)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(frameon=False, fontsize=8)
    plt.tight_layout()
    fig.savefig(OUT / f"scree_{res['id']}.png", dpi=150)
    plt.close(fig)


def loading_heatmap(res, which):
    varmap, k = res["varmap"], res["k"]
    if which == "varimax":
        mat, cols = res["prim"]["rot"], [f"RC{i + 1}" for i in range(k)]
        names = SUGGESTED_NAMES.get(res["id"], {})
        cols = [f"{c}\n" + textwrap.fill(names[c], 16) if c in names else c for c in cols]
    else:
        mat, cols = res["prim"]["load"][:, :k], [f"PC{i + 1}" for i in range(k)]
    labels = [varmap[v][0] for v in res["vars"]]
    fig, ax = plt.subplots(figsize=(2.0 + 1.5 * k, 0.4 * len(labels) + 2))
    sns.heatmap(pd.DataFrame(mat, index=labels, columns=cols), cmap="RdBu_r",
                vmin=-1, vmax=1, center=0, annot=True, fmt=".2f",
                annot_kws={"fontsize": 8}, linewidths=0.4, linecolor="white",
                cbar_kws={"label": "Loading", "shrink": 0.6}, ax=ax)
    for i in range(mat.shape[0]):
        for j in range(mat.shape[1]):
            if abs(mat[i, j]) >= LOAD_CUT:
                ax.add_patch(plt.Rectangle((j, i), 1, 1, fill=False, edgecolor="black", lw=1.4))
    ax.tick_params(axis="x", labelsize=8, labelrotation=0)
    ax.tick_params(axis="y", labelsize=8)
    ax.set_title(f"{res['title']}: {which} loadings, standardized run\n"
                 f"(n = {res['n']:,}; outlined |loading| >= {LOAD_CUT}; "
                 f"names are suggestions)", fontsize=10)
    plt.tight_layout()
    fig.savefig(OUT / f"loadings_{which}_{res['id']}.png", dpi=150)
    plt.close(fig)


def save_tables(res):
    rid, k, vars_ = res["id"], res["k"], res["vars"]
    p = res["p"]
    for tag in ("prim", "rank"):
        run = res[tag]
        pd.DataFrame({"component": [f"PC{i + 1}" for i in range(p)],
                      "eigenvalue": run["vals"],
                      "pct_variance": 100 * run["vals"] / p,
                      "cum_pct_variance": 100 * np.cumsum(run["vals"]) / p,
                      "pa_mean": res["pa_mean"], "pa_95th": res["pa95"]}) \
            .to_csv(OUT / f"eigenvalues_{rid}_{tag}.csv", index=False)
        pd.DataFrame(run["load"], index=vars_, columns=[f"PC{i + 1}" for i in range(p)]) \
            .to_csv(OUT / f"loadings_unrotated_{rid}_{tag}.csv")
        rot = pd.DataFrame(run["rot"], index=vars_, columns=[f"RC{i + 1}" for i in range(k)])
        rot["communality"] = run["communality"]
        rot.to_csv(OUT / f"loadings_varimax_{rid}_{tag}.csv")
    pd.DataFrame({"variable": vars_, "kmo_standardized": res["kmo"][1],
                  "kmo_rank": res["kmo_rank"][1]}) \
        .to_csv(OUT / f"kmo_{rid}.csv", index=False)


def scores_frame(df, res, prefix):
    out = pd.DataFrame(index=df.index)
    out[f"{prefix}in_sample"] = df.index.isin(res["index"])
    k = res["k"]
    blocks = {"PC": res["prim"]["pc_scores"], "RC": res["prim"]["rc_scores"],
              "rankRC": res["rank"]["rc_scores"]}
    for stem, arr in blocks.items():
        for i in range(k):
            col = pd.Series(np.nan, index=df.index)
            col.loc[res["index"]] = arr[:, i]
            out[f"{prefix}{stem}{i + 1}"] = col
    return out


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------

def md_table(df):
    cols = list(df.columns)
    lines = ["| " + " | ".join(map(str, cols)) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(lines)


def f2(v):
    return f"{v:+.2f}"


def lbl(res, v):
    return res["varmap"][v][0]


def section_run(res, grain):
    rid, k, p, vars_ = res["id"], res["k"], res["p"], res["vars"]
    prim, rank = res["prim"], res["rank"]
    names = SUGGESTED_NAMES.get(rid, {})
    L = []
    L.append(f"### Sample\n")
    L.append(f"- Variables: **{p}**. Complete cases: **n = {res['n']:,}** of "
             f"{res['n_total']:,} units ({res['n_total'] - res['n']:,} excluded for a "
             f"missing value in at least one variable; nothing imputed).")
    miss = res["missing"][res["missing"] > 0].sort_values(ascending=False)
    if len(miss):
        L.append("- Units missing each variable (before listwise exclusion): " + ", ".join(
            f"{lbl(res, v)} {int(c):,}" for v, c in miss.items()) + ".")
    L.append("")

    L.append("### Suitability\n")
    b, br = res["bart"], res["bart_rank"]
    L.append(md_table(pd.DataFrame([
        {"run": "standardized (primary)", "overall KMO": f"{res['kmo'][0]:.3f}",
         "Bartlett chi-square": f"{b[0]:,.1f}", "df": int(b[1]), "p": f"{b[2]:.2g}"},
        {"run": "rank (sensitivity)", "overall KMO": f"{res['kmo_rank'][0]:.3f}",
         "Bartlett chi-square": f"{br[0]:,.1f}", "df": int(br[1]), "p": f"{br[2]:.2g}"}])))
    L.append("")
    kv = pd.DataFrame({"variable": [lbl(res, v) for v in vars_],
                       "code": [f"`{v}`" for v in vars_],
                       "KMO standardized": [f"{x:.3f}" for x in res["kmo"][1]],
                       "KMO rank": [f"{x:.3f}" for x in res["kmo_rank"][1]],
                       "flag (< 0.5)": ["**yes**" if (a < KMO_FLAG or c < KMO_FLAG) else ""
                                        for a, c in zip(res["kmo"][1], res["kmo_rank"][1])]})
    L.append(md_table(kv))
    flagged = [lbl(res, v) for v, a, c in zip(vars_, res["kmo"][1], res["kmo_rank"][1])
               if a < KMO_FLAG or c < KMO_FLAG]
    L.append("\nPer-variable KMO below 0.5: " + (", ".join(flagged) if flagged else "none") + ".\n")

    L.append("### Eigenvalues and retention criteria\n")
    ev = pd.DataFrame({
        "component": [f"PC{i + 1}" for i in range(p)],
        "eigenvalue": [f"{v:.3f}" for v in prim["vals"]],
        "% variance": [f"{100 * v / p:.1f}" for v in prim["vals"]],
        "cumulative %": [f"{100 * c / p:.1f}" for c in np.cumsum(prim["vals"])],
        "PA 95th pct": [f"{v:.3f}" for v in res["pa95"]],
        "> 1": ["yes" if v > 1 else "" for v in prim["vals"]],
        "> PA": ["yes" if i < res["crit"]["pa"] else "" for i in range(p)],
        "rank-run eigenvalue": [f"{v:.3f}" for v in rank["vals"]],
    })
    L.append(md_table(ev))
    c = res["crit"]
    scree_txt = (f"{c['scree']}" if c["scree"] is not None else "not yet read")
    L.append("")
    L.append(md_table(pd.DataFrame([
        {"criterion": "Eigenvalue > 1 (Kaiser)", "standardized": c["kaiser"], "rank": c["kaiser_rank"]},
        {"criterion": "Scree plot (elbow, read visually)", "standardized": scree_txt, "rank": "same plot"},
        {"criterion": f"Parallel analysis (Horn, {PA_PCTL}th pct, {PA_ITER} draws)",
         "standardized": c["pa"], "rank": c["pa_rank"]}])))
    L.append(f"\nScree plot: `output/pca/scree_{rid}.png`.\n")
    L.append(f"**Proposed number of components: {k}** (pending your confirmation). {res['k_why']}\n")

    L.append(f"### Loadings, retained components (k = {k})\n")
    un = pd.DataFrame({"variable": [lbl(res, v) for v in vars_]})
    for i in range(k):
        un[f"PC{i + 1}"] = [f2(x) for x in prim["load"][:, i]]
    for i in range(k):
        un[f"RC{i + 1}"] = [f"**{f2(x)}**" if abs(x) >= LOAD_CUT else f2(x) for x in prim["rot"][:, i]]
    un["communality"] = [f"{h:.2f}" + (" **low**" if h < COMMUNALITY_FLAG else "")
                         for h in prim["communality"]]
    L.append("PC = unrotated, RC = varimax-rotated (Kaiser-normalised). Bold: |loading| >= 0.5. "
             "Each component is oriented so its largest loading is positive; the sign of a "
             "whole component is arbitrary.\n")
    L.append(md_table(un))
    rv = 100 * (prim["rot"] ** 2).sum(axis=0) / p
    L.append("\nVariance carried after rotation: " + ", ".join(
        f"RC{i + 1} {rv[i]:.1f}%" for i in range(k)) +
        f" (total {rv.sum():.1f}%, same as the first {k} unrotated components).\n")

    L.append("### Components: salient variables and suggested names\n")
    L.append("Names are **suggestions only**, based on the variables loading at |0.5| or more.\n")
    for i in range(k):
        col = prim["rot"][:, i]
        order = np.argsort(-np.abs(col))
        sal = [f"{lbl(res, vars_[j])} ({f2(col[j])})" for j in order if abs(col[j]) >= LOAD_CUT]
        nm = names.get(f"RC{i + 1}", "(no name suggested yet)")
        L.append(f"- **RC{i + 1}**, suggested name: *{nm}*. " +
                 ("Loading at |0.5| or more: " + "; ".join(sal) if sal else
                  "No variable loads at |0.5| or more.") + ".")
    none_sal = [lbl(res, v) for j, v in enumerate(vars_) if (np.abs(prim["rot"][j]) < LOAD_CUT).all()]
    L.append("\nVariables with no loading at |0.5| or more on any retained component: " +
             (", ".join(none_sal) if none_sal else "none") + ".\n")
    low_h = [f"{lbl(res, v)} ({h:.2f})" for v, h in zip(vars_, prim["communality"])
             if h < COMMUNALITY_FLAG]
    L.append(f"**Communality below {COMMUNALITY_FLAG}** (less than half the variable's variance "
             f"explained by the {k} retained components): " +
             (", ".join(low_h) if low_h else "none") + ".\n")

    L.append("### Sensitivity: rank-transformed PCA\n")
    L.append(f"Same complete cases, each variable replaced by its average rank then standardized; "
             f"same k = {k}, same rotation. Components matched by maximum |Tucker congruence|.\n")
    m = pd.DataFrame(res["match"])
    L.append(md_table(pd.DataFrame({
        "primary component": m.primary, "matched rank component": m["rank"],
        "congruence (phi)": [f"{v:+.3f}" for v in m.phi],
        "correlation of scores": [f"{v:+.3f}" for v in m.score_corr],
        "reading": ["equal (>= 0.95)" if abs(v) >= 0.95 else
                    "fair similarity (0.85 to 0.95)" if abs(v) >= 0.85 else
                    "**different (< 0.85)**" for v in m.phi]})))
    same = all(abs(v) >= 0.95 for v in m.phi)
    fair = all(abs(v) >= 0.85 for v in m.phi)
    L.append("")
    L.append("**Verdict: " + ("materially the same" if same else
             "broadly similar but not identical" if fair else
             "materially different for at least one component") +
             f".** Unrotated congruence, PC1 to PC{k}: " +
             ", ".join(f"{v:+.3f}" for v in res["phi_unrot"]) + ". "
             f"Criteria on the rank run: eigenvalue > 1 gives {c['kaiser_rank']}, parallel "
             f"analysis gives {c['pa_rank']} (standardized run: {c['kaiser']} and {c['pa']}).\n")
    moved = []
    for mm in res["match"]:
        a = int(mm["primary"][2:]) - 1
        b = int(mm["rank"][2:]) - 1
        s = np.sign(mm["phi"]) or 1
        pa_ = set(v for v, x in zip(vars_, prim["rot"][:, a]) if abs(x) >= LOAD_CUT)
        rb_ = set(v for v, x in zip(vars_, s * rank["rot"][:, b]) if abs(x) >= LOAD_CUT)
        if pa_ != rb_:
            moved.append(f"{mm['primary']}: " +
                         (("gains " + ", ".join(lbl(res, v) for v in sorted(rb_ - pa_))) if rb_ - pa_ else "") +
                         ("; " if (rb_ - pa_ and pa_ - rb_) else "") +
                         (("loses " + ", ".join(lbl(res, v) for v in sorted(pa_ - rb_))) if pa_ - rb_ else ""))
    L.append("Changes in the salient (|0.5|) variable set under ranks: " +
             ("; ".join(moved) if moved else "none") + ".\n")
    return "\n".join(L)


def section_headline(res, grain, extra_note=""):
    prim, vars_, k = res["prim"], res["vars"], res["k"]
    heads = [v for v in HEADLINE[grain] if v in vars_]
    names = SUGGESTED_NAMES.get(res["id"], {})
    rows = []
    home = {}
    for v in heads:
        j = vars_.index(v)
        row = {"variable": lbl(res, v), "code": f"`{v}`"}
        for i in range(k):
            x = prim["rot"][j, i]
            row[f"RC{i + 1}"] = f"**{f2(x)}**" if abs(x) >= LOAD_CUT else f2(x)
        top = int(np.abs(prim["rot"][j]).argmax())
        home[v] = top
        row["highest loading on"] = f"RC{top + 1}"
        row["communality"] = f"{prim['communality'][j]:.2f}"
        rows.append(row)
    L = [md_table(pd.DataFrame(rows)), ""]
    z = res["prim"]["z"]
    sp = z[heads].rank().corr()
    pairs = [(a, b) for i, a in enumerate(heads) for b in heads[i + 1:]]
    L.append("Spearman rho among these variables on the PCA sample: " + "; ".join(
        f"{lbl(res, a)} vs {lbl(res, b)} {sp.loc[a, b]:+.3f}" for a, b in pairs) + ".\n")
    minority = "EP_MINRTY" if grain == "tract" else "PEOPCOLORPCT"
    access = [v for v in heads if v != minority]
    mh = home[minority]
    same = [v for v in access if home[v] == mh]
    diff = [v for v in access if home[v] != mh]
    def nm(i):
        return f"RC{i + 1}" + (f" ({names[f'RC{i + 1}']})" if f"RC{i + 1}" in names else "")
    txt = (f"{lbl(res, minority)} loads highest on {nm(mh)}. " +
           "; ".join(f"{lbl(res, v)} loads highest on {nm(home[v])}" for v in access) + ". ")
    if not same:
        txt += "**The PCA separates minority composition from every access variable.**"
    elif not diff:
        txt += "**The PCA merges minority composition with the access variables on one component.**"
    else:
        txt += ("**Partly merged:** minority composition shares its main component with " +
                ", ".join(lbl(res, v) for v in same) + ", and is separated from " +
                ", ".join(lbl(res, v) for v in diff) + ".")
    # signs and secondary loadings, so "shared" is not read as "same direction"
    jm = vars_.index(minority)
    for i in range(k):
        xm = prim["rot"][jm, i]
        others = [(v, prim["rot"][vars_.index(v), i]) for v in access
                  if abs(prim["rot"][vars_.index(v), i]) >= LOAD_CUT]
        if abs(xm) >= LOAD_CUT and others:
            txt += (f" On RC{i + 1}, {lbl(res, minority)} loads {f2(xm)} and " +
                    ", ".join(f"{lbl(res, v)} {f2(x)}" for v, x in others) +
                    (" (opposite signs)." if all(np.sign(x) != np.sign(xm) for _, x in others)
                     else " (same sign)." if all(np.sign(x) == np.sign(xm) for _, x in others)
                     else "."))
    L.append(txt + " " + extra_note + "\n")
    return "\n".join(L)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)
    tract = pd.read_csv(BASE / "tract_analysis.csv", dtype={"GEOID": str}).set_index("GEOID")
    bg = pd.read_csv(BASE / "blockgroup_analysis.csv", dtype={"GEOID": str}).set_index("GEOID")

    problems = []
    if len(tract) != 698:
        problems.append(f"tract rows {len(tract)} != 698")
    if len(bg) != 1843:
        problems.append(f"block-group rows {len(bg)} != 1843")
    for name, lst, df in [("tract", PCA_TRACT_VARS, tract), ("bg", PCA_BG_VARS, bg)]:
        gone = [v for v in lst if v not in df.columns]
        if gone:
            problems.append(f"{name} PCA variables absent: {gone}")
    if len(PCA_TRACT_VARS) != 19 or len(PCA_BG_VARS) != 24:
        problems.append("PCA variable-list sizes are not 19 / 24")
    if problems:
        raise SystemExit("STOP:\n  " + "\n  ".join(problems))

    runs = {}
    runs["tract"] = analyse(tract, PCA_TRACT_VARS, TRACT_VARS, "tract",
                            "Tract, 19 variables", rng)
    runs["bg24"] = analyse(bg, PCA_BG_VARS, BG_VARS, "bg24",
                           "Block group, all 24 variables", rng)
    run_reduced = runs["bg24"]["n"] < LOW_N
    if run_reduced:
        runs["bg21"] = analyse(bg, PCA_BG_VARS_REDUCED, BG_VARS, "bg21",
                               "Block group, 21 variables (3 over 20% missing excluded)", rng)

    for res in runs.values():
        scree_plot(res)
        loading_heatmap(res, "varimax")
        loading_heatmap(res, "unrotated")
        save_tables(res)
        print(f"{res['id']}: n={res['n']} p={res['p']} kaiser={res['crit']['kaiser']} "
              f"pa={res['crit']['pa']} k={res['k']} KMO={res['kmo'][0]:.3f}")
        print("   eig:", np.round(res["prim"]["vals"][:8], 3))
        print("   pa95:", np.round(res["pa95"][:8], 3))

    s_t = scores_frame(tract, runs["tract"], "")
    s_t.index.name = "GEOID"
    s_t.reset_index().to_csv(OUT / "pca_scores_tract.csv", index=False)
    s_b = scores_frame(bg, runs["bg24"], "bg24_")
    if run_reduced:
        s_b = s_b.join(scores_frame(bg, runs["bg21"], "bg21_"))
    s_b.index.name = "GEOID"
    s_b.reset_index().to_csv(OUT / "pca_scores_blockgroup.csv", index=False)

    write_report(runs, run_reduced)
    print(f"report: {REPORT}\noutputs: {OUT}")


def write_report(runs, run_reduced):
    t, b24 = runs["tract"], runs["bg24"]
    H = [f"""# Principal component analysis of the vulnerability indicators

Tract and block group are analysed separately and never mixed. Inputs are the
variable lists recorded in DATA_PROCESSING.md Sec 7 ("Variable reduction before
PCA"): 19 tract variables and 24 block-group social variables. The 13 EJScreen
environmental measures are excluded (provisional, pending the professor). No
hazard or investment variable enters any PCA, nothing is modelled, and nothing
is imputed.

**Nothing here is final.** The number of components and every component name
are proposals for you to confirm. Component scores are saved in
`output/pca/pca_scores_tract.csv` and `output/pca/pca_scores_blockgroup.csv`
(GEOID as string) and are not used anywhere.

**Method.**
- Primary run: each variable standardized (mean 0, SD 1), PCA on the
  correlation matrix. Sensitivity run: each variable replaced by its average
  rank, then standardized (consistent with the Spearman screen).
- Complete cases only, n reported per run.
- Suitability: Kaiser-Meyer-Olkin, overall and per variable (flag below 0.5),
  and Bartlett's test of sphericity.
- Retention criteria side by side: eigenvalue above 1, scree plot, and Horn's
  parallel analysis ({PA_ITER} random normal data sets of the same n and p;
  a component is retained while its eigenvalue exceeds the {PA_PCTL}th
  percentile of the random eigenvalues).
- Loadings are correlations between variable and component. Rotation is
  varimax with Kaiser normalisation (the SoVI convention). Communality is the
  share of a variable's variance reproduced by the retained components;
  flagged below {COMMUNALITY_FLAG}.
- Primary and rank runs are compared by Tucker's congruence coefficient on
  matched rotated components: 0.95 or above is treated as the same
  component, 0.85 to 0.95 as fair similarity, below 0.85 as different
  (Lorenzo-Seva and ten Berge 2006).

Script: `scripts/pca_analysis.py`. Figures and tables: `output/pca/`.
"""]
    H.append("## Proposals for you to confirm\n")
    rows = []
    for res in runs.values():
        c = res["crit"]
        rows.append({"run": res["title"], "n": f"{res['n']:,}",
                     "eigenvalue > 1": c["kaiser"],
                     "scree": c["scree"] if c["scree"] is not None else "not read",
                     "parallel analysis": c["pa"], "proposed k": f"**{res['k']}**",
                     "variance explained": f"{100 * res['prim']['vals'][:res['k']].sum() / res['p']:.1f}%"})
    H.append(md_table(pd.DataFrame(rows)) + "\n")
    for res in runs.values():
        names = SUGGESTED_NAMES.get(res["id"], {})
        if names:
            H.append(f"- {res['title']}: " + "; ".join(f"{c} *{n}*" for c, n in names.items()))
    H.append("")

    H.append("---\n\n## Tract\n")
    H.append(section_run(t, "tract"))
    H.append("### Relevance to earlier findings\n")
    H.append("Headline access variables (households with no vehicle, multi-unit housing, "
             "no internet access) and minority population share, on the varimax components "
             "of the standardized run. The ACS versions of no vehicle and no broadband were "
             "dropped at the screen, so only the SVI versions appear.\n")
    tract_df = pd.read_csv(BASE / "tract_analysis.csv", dtype={"GEOID": str})
    rho_bb = tract_df[["EP_MINRTY", "no_broadband"]].corr(method="spearman").iloc[0, 1]
    H.append(section_headline(t, "tract", extra_note=(
        f"On the 0.38 to 0.45 figures from the earlier analysis: minority share correlates "
        f"{rho_bb:+.3f} with no broadband subscription (dropped at the screen) and, as above, "
        f"with no internet access. Its correlation with the vehicle and multi-unit measures is "
        f"much weaker, so the 0.38 to 0.45 overlap is specific to connectivity.")))

    H.append("---\n\n## Block group\n")
    if run_reduced:
        H.append(f"With all 24 variables, complete cases are **{b24['n']:,}** of 1,843, below "
                 f"the roughly {LOW_N:,} threshold. So two versions are reported and **you choose "
                 f"between them**:\n\n"
                 f"- **24 variables, n = {b24['n']:,}.** Every social indicator, on the block groups "
                 f"that report all of them.\n"
                 f"- **21 variables, n = {runs['bg21']['n']:,}.** Excludes the three variables above "
                 f"20% missing: " + ", ".join(f"{BG_VARS[v][0]} (`{v}`)" for v in PCA_BG_HIGH_MISSING) +
                 ". Median family income (18.8%) and median home value (16.7%) are under the "
                 "20% line and stay in.\n\n"
                 "The complete-case block groups are not a random subset: a block group drops "
                 "out when a median is suppressed (small sample) or income disparity is undefined "
                 "(zero households in a bracket), so the smaller sample leans toward larger, "
                 "more populous block groups.\n")
    H.append(f"### Block group, version A: all 24 variables\n")
    H.append(section_run(b24, "bg").replace("\n### ", "\n#### "))
    if run_reduced:
        H.append(f"### Block group, version B: 21 variables\n")
        H.append(section_run(runs["bg21"], "bg").replace("\n### ", "\n#### "))
        b21 = runs["bg21"]
        common = [v for v in b24["vars"] if v in b21["vars"]]
        i24 = [b24["vars"].index(v) for v in common]
        i21 = [b21["vars"].index(v) for v in common]
        phi = congruence(b24["prim"]["rot"][i24], b21["prim"]["rot"][i21])
        ri, ci = linear_sum_assignment(-np.abs(phi))
        H.append("### Version A against version B\n")
        H.append("Rotated components matched by |congruence| on the 21 shared variables:\n")
        H.append(md_table(pd.DataFrame({
            "24-variable component": [f"RC{a + 1}" for a in ri],
            "21-variable component": [f"RC{b + 1}" for b in ci],
            "congruence": [f"{phi[a, b]:+.3f}" for a, b in zip(ri, ci)]})) + "\n")
        if b24["k"] != b21["k"]:
            H.append(f"The versions retain different numbers of components ({b24['k']} and "
                     f"{b21['k']}), so some components are unmatched.\n")
    H.append("### Relevance to earlier findings (block group)\n")
    H.append("Block group has no multi-unit housing, no internet-access or second no-vehicle "
             "measure. The access variables are households with no vehicle and no broadband "
             "subscription, and the minority-composition measure is people of colour share "
             "(same definition as minority share).\n")
    for rid in ["bg24", "bg21"] if run_reduced else ["bg24"]:
        H.append(f"**{runs[rid]['title']}**\n")
        H.append(section_headline(runs[rid], "bg"))

    H.append("---\n\n## Files\n")
    H.append("- `output/pca/scree_<run>.png`, `loadings_varimax_<run>.png`, "
             "`loadings_unrotated_<run>.png` (plain-language labels)\n"
             "- `output/pca/eigenvalues_<run>_<prim|rank>.csv`, "
             "`loadings_unrotated_<run>_<prim|rank>.csv`, "
             "`loadings_varimax_<run>_<prim|rank>.csv` (with communality), `kmo_<run>.csv`\n"
             "- `output/pca/pca_scores_tract.csv`: GEOID, `in_sample`, unrotated `PC*`, "
             "varimax `RC*`, rank-run varimax `rankRC*` (unit variance; blank outside the sample)\n"
             "- `output/pca/pca_scores_blockgroup.csv`: same, prefixed `bg24_` "
             + ("and `bg21_` for the two versions" if run_reduced else "") + "\n"
             "- Run ids: `tract`, `bg24`" + (", `bg21`" if run_reduced else "") + "\n")
    text = "\n".join(H)
    assert "\u2014" not in text, "em dash in report"
    REPORT.write_text(text)


if __name__ == "__main__":
    main()
