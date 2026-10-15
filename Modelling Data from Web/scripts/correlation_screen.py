"""Pre-PCA correlation screen of the vulnerability indicators, tract and block
group analysed separately (never mixed). Screen only: nothing is dropped,
imputed, modelled or recommended. The professor's rule is |Spearman rho| >
0.75 between two indicators -> one of them goes; this script lays out the
evidence, the user makes every drop decision by hand.

Method
  - Spearman rank correlation, pairwise-complete observations, n reported
    for every pair. Computed pair by pair (scipy) so each pair is ranked on
    exactly its own complete rows.
  - |rho| compared against the threshold unrounded; the sign is reported.
  - "Above the line" = |rho| >= 0.75. Near miss = 0.70 <= |rho| < 0.75.
  - Clusters = connected components of the graph whose edges are the
    above-line pairs. For each cluster, every minimum vertex cover (smallest
    set of drops leaving no above-line pair) is enumerated - information,
    not a recommendation.

Scope
  - Tract: the 27 indicators in professor_labels.TRACT_VARS. The seven SVI
    race/ethnicity adjunct columns are excluded even if still present in
    tract_analysis.csv (reported, not silently ignored).
  - Block group: all 37 indicators in professor_labels.BG_VARS, with the 13
    EJScreen environmental measures reported as a separate group.
  - No investment, hazard-loss, sea level, surge or flood columns are read.

Usage:   python scripts/correlation_screen.py
Outputs: output/correlation_screen/*  and  correlation_screen.md
"""
import itertools
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.patches import Rectangle
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent))
from professor_labels import (  # noqa: E402
    BG_VARS, CONSTRUCT_ORDER, TRACT_VARS, ordered_vars,
)
from scaler_projects import BASE, OUTPUT_DIR  # noqa: E402
from vulnerability_loaders import EJ_ENV  # noqa: E402

OUT = OUTPUT_DIR / "correlation_screen"
REPORT = BASE / "correlation_screen.md"

THRESH = 0.75
NEAR_LO = 0.70
LOW_N_BG = 1200          # flag block-group pairs resting on about this many units or fewer
MAX_COVER_NODES = 22     # brute-force guard for the minimum-drop enumeration

EXPECTED_TRACT_ROWS, EXPECTED_TRACT_VARS = 698, 27
EXPECTED_BG_ROWS, EXPECTED_BG_VARS, EXPECTED_BG_ENV = 1843, 37, 13

RACE_ADJUNCTS = {
    "EP_HISP": "Hispanic population share",
    "EP_AFAM": "Black population share",
    "EP_ASIAN": "Asian population share",
    "EP_TWOMORE": "Two or more races share",
    "EP_OTHERRACE": "Other race share",
    "EP_AIAN": "American Indian / Alaska Native share",
    "EP_NHPI": "Native Hawaiian / Pacific Islander share",
}

# Access indicators behind the gray / green composition result
# (FINDINGS_FOR_PROFESSOR.md, gray_decomposition.md). At block group the
# minority-share measure is EJScreen's PEOPCOLORPCT (same definition: all
# persons except non-Hispanic white); marked as the counterpart, not equated.
HEADLINE = {
    "tract": {"EP_NOVEH": "yes", "no_vehicle": "yes", "EP_MUNIT": "yes",
              "EP_NOINT": "yes", "no_broadband": "yes", "EP_MINRTY": "yes"},
    "bg": {"no_vehicle": "yes", "no_broadband": "yes",
           "PEOPCOLORPCT": "yes (block-group counterpart of minority share)"},
}

# Status. DATA_PROCESSING.md Sec 1 grades only the ten tract ACS variables;
# every other status comes from the variable table in
# FINDINGS_FOR_PROFESSOR.md Sec 2, which extends it. The source is carried
# in its own column so the two are never confused.
DP = "DATA_PROCESSING.md Sec 1"
FP = "FINDINGS_FOR_PROFESSOR.md Sec 2 (not graded in DATA_PROCESSING.md)"
TRACT_STATUS = {
    "poverty_under125": ("threshold approximation", DP, "1.25 vs CRE 1.30"),
    "crowding_over100": ("threshold approximation", DP, ">1.00 vs CRE 0.75 per room"),
    "no_broadband": ("proxy", DP, "Total minus broadband of any type"),
    "no_fulltime_worker_hh": ("proxy (loose)", DP, "zero workers, not zero full-time"),
    "no_diploma_pop25": ("proxy", DP, "person-level for a household concept"),
    "age65plus": ("clean", DP, ""), "uninsured": ("clean", DP, ""),
    "disability": ("clean", DP, ""), "no_vehicle": ("clean", DP, ""),
    "limited_english_hh": ("clean", DP, ""),
}
BG_STATUS = {
    "pct_crowding_over100": ("threshold approximation", FP, ">1.00 vs ADI 0.75 per room"),
    "no_broadband": ("proxy", FP, "same complement method as tract; added late"),
    "no_vehicle": ("clean", FP, "added late"),
    "income_disparity": ("clean", FP,
                         "undefined (not missing) where a bracket is zero; "
                         "$10k/$50k cutoffs not inflation-adjusted (DATA_PROCESSING.md Sec 3)"),
    "median_family_income": ("clean", FP, "block-group median suppression"),
    "median_home_value": ("clean", FP, "block-group median suppression"),
    "median_gross_rent": ("clean", FP, "block-group median suppression"),
    "median_monthly_mortgage": ("clean", FP, "block-group median suppression"),
    "poverty_pct_families": ("clean", FP, "small family counts, large MOE (DATA_PROCESSING.md Sec 3)"),
    "pct_single_parent_children": ("clean", FP, "small family counts, large MOE (DATA_PROCESSING.md Sec 3)"),
}


def status_of(code, grain):
    table = TRACT_STATUS if grain == "tract" else BG_STATUS
    return table.get(code, ("clean", FP, ""))


# --------------------------------------------------------------------------
# scope checks
# --------------------------------------------------------------------------

def scope_tract(df):
    present = [c for c in RACE_ADJUNCTS if c in df.columns]
    varlist = ordered_vars(TRACT_VARS)
    missing_cols = [c for c in varlist if c not in df.columns]
    problems = []
    if len(df) != EXPECTED_TRACT_ROWS:
        problems.append(f"tract rows = {len(df)}, expected {EXPECTED_TRACT_ROWS}")
    if len(varlist) != EXPECTED_TRACT_VARS:
        problems.append(f"tract indicator list has {len(varlist)}, expected {EXPECTED_TRACT_VARS}")
    if missing_cols:
        problems.append(f"tract indicators absent from tract_analysis.csv: {missing_cols}")
    if set(varlist) & set(RACE_ADJUNCTS):
        problems.append("a race adjunct is in the tract indicator list")
    if "EP_MINRTY" not in varlist or "EP_NOINT" not in varlist:
        problems.append("EP_MINRTY or EP_NOINT missing from the tract indicator list")
    return varlist, present, problems


def scope_bg(df):
    varlist = ordered_vars(BG_VARS)
    env = [c for c in varlist if BG_VARS[c][1] == "Environmental exposure"]
    missing_cols = [c for c in varlist if c not in df.columns]
    problems = []
    if len(df) != EXPECTED_BG_ROWS:
        problems.append(f"block-group rows = {len(df)}, expected {EXPECTED_BG_ROWS}")
    if len(varlist) != EXPECTED_BG_VARS:
        problems.append(f"block-group indicator list has {len(varlist)}, expected {EXPECTED_BG_VARS}")
    if len(env) != EXPECTED_BG_ENV or set(env) != set(EJ_ENV):
        problems.append(f"environmental group is {len(env)} variables, expected the {EXPECTED_BG_ENV} EJ_ENV")
    if missing_cols:
        problems.append(f"block-group indicators absent from blockgroup_analysis.csv: {missing_cols}")
    return varlist, env, problems


# --------------------------------------------------------------------------
# correlation
# --------------------------------------------------------------------------

def pairwise_spearman(df, varlist):
    """Every pair on its own complete rows. Returns long table + rho/n matrices."""
    rho = pd.DataFrame(np.eye(len(varlist)), index=varlist, columns=varlist)
    nmat = pd.DataFrame(0, index=varlist, columns=varlist)
    rows = []
    for a, b in itertools.combinations(varlist, 2):
        ok = df[a].notna() & df[b].notna()
        n = int(ok.sum())
        r = spearmanr(df.loc[ok, a], df.loc[ok, b]).statistic if n > 2 else np.nan
        rho.loc[a, b] = rho.loc[b, a] = r
        nmat.loc[a, b] = nmat.loc[b, a] = n
        rows.append({"var_a": a, "var_b": b, "rho": r, "abs_rho": abs(r), "n": n})
    for v in varlist:
        nmat.loc[v, v] = int(df[v].notna().sum())
    # cross-check against pandas' pairwise Spearman
    chk = df[varlist].corr(method="spearman")
    diff = float(np.nanmax(np.abs(chk.values - rho.values)))
    if diff > 1e-9:
        raise SystemExit(f"scipy / pandas Spearman disagree by {diff}")
    return pd.DataFrame(rows), rho, nmat


def clusters_from(pairs):
    """Connected components of the above-line graph, largest first."""
    adj = {}
    for a, b in zip(pairs.var_a, pairs.var_b):
        adj.setdefault(a, set()).add(b)
        adj.setdefault(b, set()).add(a)
    seen, comps = set(), []
    for start in adj:
        if start in seen:
            continue
        stack, comp = [start], set()
        while stack:
            v = stack.pop()
            if v in comp:
                continue
            comp.add(v)
            stack.extend(adj[v] - comp)
        seen |= comp
        comps.append(comp)
    return comps


def minimum_drop_sets(members, edges):
    """All minimum vertex covers of one cluster, by increasing-size search."""
    members = sorted(members)
    if len(members) > MAX_COVER_NODES:
        return None
    for k in range(1, len(members) + 1):
        hits = [set(c) for c in itertools.combinations(members, k)
                if all(a in c or b in c for a, b in edges)]
        if hits:
            return hits
    return []


# --------------------------------------------------------------------------
# figures and tables
# --------------------------------------------------------------------------

def heatmap(rho, varlist, varmap, title, path):
    labels = [varmap[v][0] for v in varlist]
    size = max(10, len(varlist) * 0.42)
    fig, ax = plt.subplots(figsize=(size + 2, size))
    sns.heatmap(rho.loc[varlist, varlist], cmap="RdBu_r", center=0, vmin=-1, vmax=1,
                square=True, linewidths=0.3, linecolor="white", ax=ax,
                xticklabels=labels, yticklabels=labels,
                cbar_kws={"label": "Spearman rho", "shrink": 0.6, "pad": 0.2})
    # outline every off-diagonal cell at or above the line
    for i, a in enumerate(varlist):
        for j, b in enumerate(varlist):
            if i != j and abs(rho.loc[a, b]) >= THRESH:
                ax.add_patch(Rectangle((j, i), 1, 1, fill=False, edgecolor="black", lw=1.6))
    # construct separators and names
    constructs = [varmap[v][1] for v in varlist]
    edges = [i for i in range(1, len(varlist)) if constructs[i] != constructs[i - 1]]
    for e in edges:
        ax.axhline(e, color="#333333", lw=1.2)
        ax.axvline(e, color="#333333", lw=1.2)
    starts = [0] + edges
    ends = edges + [len(varlist)]
    for s, e in zip(starts, ends):
        ax.text(len(varlist) + 0.3, (s + e) / 2, constructs[s], va="center",
                fontsize=9, color="#333333", fontweight="bold")
    ax.tick_params(axis="x", labelrotation=90, labelsize=8)
    ax.tick_params(axis="y", labelsize=8)
    ax.set_title(f"{title}\nSpearman rank correlation, pairwise-complete. "
                 f"Outlined cells: |rho| >= {THRESH}", fontsize=11)
    plt.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def fmt_rho(r):
    return f"{r:+.3f}"


def label(code, varmap):
    return varmap[code][0]


def md_table(df):
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# one grain
# --------------------------------------------------------------------------

def screen(df, varlist, varmap, grain, title, env=None):
    tag = "tract" if grain == "tract" else "blockgroup"
    env = env or []
    long, rho, nmat = pairwise_spearman(df, varlist)
    rho.to_csv(OUT / f"{tag}_spearman_matrix.csv")
    nmat.to_csv(OUT / f"{tag}_pairwise_n_matrix.csv")
    heatmap(rho, varlist, varmap, title, OUT / f"{tag}_spearman_heatmap.png")

    def group_of(v):
        return "environmental" if v in env else "vulnerability"

    long["name_a"] = long.var_a.map(lambda v: label(v, varmap))
    long["name_b"] = long.var_b.map(lambda v: label(v, varmap))
    if env:
        long["group"] = [f"{group_of(a)} x {group_of(b)}" for a, b in zip(long.var_a, long.var_b)]
    long["low_n_flag"] = (long.n <= LOW_N_BG) if grain == "bg" else False

    above = long[long.abs_rho >= THRESH].sort_values("abs_rho", ascending=False).reset_index(drop=True)
    near = long[(long.abs_rho >= NEAR_LO) & (long.abs_rho < THRESH)] \
        .sort_values("abs_rho", ascending=False).reset_index(drop=True)
    above.to_csv(OUT / f"{tag}_pairs_at_or_above_075.csv", index=False)
    near.to_csv(OUT / f"{tag}_near_misses_070_075.csv", index=False)

    comps = clusters_from(above)
    comps.sort(key=lambda c: (-len(c), -above[above.var_a.isin(c)].abs_rho.max()))
    clusters = []
    for i, comp in enumerate(comps, 1):
        cid = f"{'T' if grain == 'tract' else 'B'}{i}"
        links = above[above.var_a.isin(comp) & above.var_b.isin(comp)]
        drops = minimum_drop_sets(comp, list(zip(links.var_a, links.var_b)))
        clusters.append({"id": cid, "members": [v for v in varlist if v in comp],
                         "links": links, "drops": drops})
    cluster_of = {v: c["id"] for c in clusters for v in c["members"]}

    # decision support, one row per variable in any above-line pair
    in_pairs = [v for v in varlist if v in cluster_of]
    abs_rho = rho.abs()
    vuln = [v for v in varlist if v not in env]
    ds_rows = []
    for v in in_pairs:
        others = [o for o in varlist if o != v]
        st, st_src, st_note = status_of(v, grain)
        row = {
            "cluster": cluster_of[v], "code": v, "name": label(v, varmap),
            "source": varmap[v][2], "construct": varmap[v][1],
            "status": st, "status_note": st_note, "status_source": st_src,
            "pct_missing": round(100 * df[v].isna().mean(), 1),
            "n_partners_ge_075": int((abs_rho.loc[v, others] >= THRESH).sum()),
            "mean_abs_rho_all_others": round(float(abs_rho.loc[v, others].mean()), 3),
        }
        if env:
            row["group"] = group_of(v)
            vo = [o for o in vuln if o != v]
            row["mean_abs_rho_vulnerability_24_only"] = round(float(abs_rho.loc[v, vo].mean()), 3)
        row["headline_finding"] = HEADLINE[grain].get(v, "no")
        ds_rows.append(row)
    ds = pd.DataFrame(ds_rows)
    ds["_c"] = ds.cluster.str[1:].astype(int)
    ds = ds.sort_values("_c", kind="stable").drop(columns="_c").reset_index(drop=True)
    ds.to_csv(OUT / f"{tag}_decision_support.csv", index=False)

    sheet = pd.DataFrame({"cluster_id": ds.cluster, "variable": ds.code,
                          "plain_language_name": ds.name, "decision": "", "reason": ""})
    sheet.to_csv(OUT / f"correlation_decisions_{tag}.csv", index=False)

    cl_rows = []
    for c in clusters:
        for _, r in c["links"].iterrows():
            cl_rows.append({"cluster": c["id"], "var_a": r.var_a, "var_b": r.var_b,
                            "rho": r.rho, "n": r.n})
    pd.DataFrame(cl_rows).to_csv(OUT / f"{tag}_cluster_links.csv", index=False)
    pd.DataFrame([{"cluster": c["id"], "members": "; ".join(c["members"]),
                   "min_drops": (len(next(iter(c["drops"]))) if c["drops"] else ""),
                   "all_minimum_drop_sets": (" | ".join("{" + ", ".join(sorted(s)) + "}"
                                                        for s in c["drops"])
                                             if c["drops"] is not None else "not enumerated")}
                  for c in clusters]).to_csv(OUT / f"{tag}_clusters.csv", index=False)

    return {"long": long, "above": above, "near": near, "clusters": clusters,
            "ds": ds, "n_vars": len(varlist), "n_pairs_total": len(long)}


# --------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------

def pair_table(pairs, varmap, grain, show_group):
    rows = []
    for i, r in enumerate(pairs.itertuples(), 1):
        row = {"#": i,
               "variable A": f"{r.name_a} (`{r.var_a}`)",
               "variable B": f"{r.name_b} (`{r.var_b}`)",
               "rho": fmt_rho(r.rho), "n": f"{r.n:,}"}
        if show_group:
            row["group"] = r.group
        if grain == "bg":
            row["n <= 1,200?"] = "**yes**" if r.low_n_flag else ""
        rows.append(row)
    return md_table(pd.DataFrame(rows)) if rows else "_None._"


def cluster_section(res, varmap, grain):
    out = []
    for c in res["clusters"]:
        out.append(f"#### Cluster {c['id']} ({len(c['members'])} variables, "
                   f"{len(c['links'])} links)\n")
        out.append("Members: " + "; ".join(f"{label(v, varmap)} (`{v}`)" for v in c["members"]) + "\n")
        links = c["links"].sort_values("abs_rho", ascending=False)
        out.append(pair_table(links, varmap, grain, show_group=False) + "\n")
        if c["drops"] is None:
            out.append(f"Minimum drop sets: not enumerated (cluster larger than "
                       f"{MAX_COVER_NODES} variables).\n")
        else:
            k = len(c["drops"][0])
            out.append(f"Smallest number of drops that leaves no pair in this cluster at or "
                       f"above {THRESH}: **{k}**. There {'is' if len(c['drops']) == 1 else 'are'} "
                       f"{len(c['drops'])} such set{'s' if len(c['drops']) != 1 else ''} "
                       f"(information only, not a recommendation):\n")
            for s in c["drops"]:
                out.append("- " + ", ".join(f"{label(v, varmap)} (`{v}`)"
                                            for v in c["members"] if v in s))
            out.append("")
    return "\n".join(out) if out else "_No clusters._"


def ds_table(ds, env):
    cols = {"cluster": "cluster", "name": "variable", "code": "code", "source": "source",
            "status": "status", "pct_missing": "% missing",
            "n_partners_ge_075": "partners >= 0.75",
            "mean_abs_rho_all_others": "mean abs rho (all others)"}
    if env:
        cols["mean_abs_rho_vulnerability_24_only"] = "mean abs rho (24 non-environmental)"
    cols["headline_finding"] = "in headline finding"
    t = ds.rename(columns=cols)[list(cols.values())].copy()
    t["code"] = t["code"].map(lambda c: f"`{c}`")
    t["% missing"] = t["% missing"].map(lambda p: f"{p:.1f}")
    for c in [c for c in t.columns if c.startswith("mean abs rho")]:
        t[c] = t[c].map(lambda r: f"{r:.3f}")
    notes = ds[ds.status_note != ""][["code", "status_note", "status_source"]]
    body = md_table(t)
    if len(notes):
        body += "\n\nStatus notes:\n\n" + "\n".join(
            f"- `{r.code}`: {r.status_note}" for r in notes.itertuples())
    return body


def grain_report(res, varmap, grain, heading, scope_md, env):
    above, near = res["above"], res["near"]
    low_n = int(above.low_n_flag.sum()) if grain == "bg" else 0
    tag = "tract" if grain == "tract" else "blockgroup"
    lines = [f"## {heading}\n", "### Scope checks\n", scope_md, "",
             "### Counts\n",
             f"- Indicators screened: **{res['n_vars']}** "
             f"({res['n_pairs_total']:,} distinct pairs)",
             f"- Pairs with |rho| >= {THRESH}: **{len(above)}**",
             f"- Clusters: **{len(res['clusters'])}**, covering "
             f"**{len(res['ds'])}** variables",
             f"- Near misses (0.70 <= |rho| < 0.75): **{len(near)}**"]
    if grain == "bg":
        lines.append(f"- Listed pairs (>= 0.75) resting on 1,200 block groups or fewer: **{low_n}**")
        by_group = above.group.value_counts()
        lines.append("- Pairs >= 0.75 by group: " + ", ".join(
            f"{g}: {n}" for g, n in by_group.items()))
    lines += ["",
              f"Files: `output/correlation_screen/{tag}_spearman_matrix.csv`, "
              f"`{tag}_pairwise_n_matrix.csv`, `{tag}_spearman_heatmap.png`, "
              f"`{tag}_pairs_at_or_above_075.csv`, `{tag}_near_misses_070_075.csv`, "
              f"`{tag}_clusters.csv`, `{tag}_cluster_links.csv`, "
              f"`{tag}_decision_support.csv`, `correlation_decisions_{tag}.csv`.\n",
              f"### Every pair at or above {THRESH}, ranked by |rho|\n",
              pair_table(above, varmap, grain, show_group=bool(env)), "",
              "### Clusters\n",
              cluster_section(res, varmap, grain), "",
              "### Near misses, 0.70 to 0.75 (not covered by the rule)\n",
              pair_table(near, varmap, grain, show_group=bool(env)), "",
              "### Decision support, every variable in an above-line pair\n",
              ds_table(res["ds"], env), ""]
    return "\n".join(lines)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tract = pd.read_csv(BASE / "tract_analysis.csv", dtype={"GEOID": str})
    bg = pd.read_csv(BASE / "blockgroup_analysis.csv", dtype={"GEOID": str})

    t_vars, race_present, t_prob = scope_tract(tract)
    b_vars, b_env, b_prob = scope_bg(bg)
    if t_prob or b_prob:
        # data contradicts the specification: stop, do not improvise
        raise SystemExit("STOP, scope check failed:\n  " + "\n  ".join(t_prob + b_prob))

    t = screen(tract, t_vars, TRACT_VARS, "tract",
               f"Tract ({len(tract)} tracts, {len(t_vars)} vulnerability indicators)")
    b = screen(bg, b_vars, BG_VARS, "bg",
               f"Block group ({len(bg)} block groups, {len(b_vars)} indicators, "
               f"{len(b_env)} environmental)", env=b_env)

    if race_present:
        race_md = (f"- **Race / ethnicity adjuncts: {len(race_present)} of 7 are still present "
                   f"in `tract_analysis.csv`**: " + ", ".join(
                       f"{RACE_ADJUNCTS[c]} (`{c}`)" for c in race_present) +
                   ". The table itself has not been updated. They are **excluded from this "
                   "screen**. (`scripts/analysis_variables.py` `TRACT_VULN_VARS` also "
                   "still lists all 34.)")
    else:
        race_md = "- Race / ethnicity adjuncts: none of the seven is present in `tract_analysis.csv`."
    t_scope = "\n".join([
        race_md,
        "- Minority population share (`EP_MINRTY`) is retained. No internet access "
        "(`EP_NOINT`) is retained.",
        f"- Indicators screened: {len(t_vars)} (expected 27). Rows: {len(tract)} "
        f"(expected 698).",
        "- Not read: investment outcomes, FEMA hazard losses, sea level rise, storm "
        "surge, flood."])
    b_scope = "\n".join([
        f"- Indicators screened: {len(b_vars)} (expected 37). Rows: {len(bg)} (expected 1,843).",
        f"- **Environmental exposure group ({len(b_env)} EJScreen measures), reported "
        "separately below:** " + ", ".join(f"{BG_VARS[c][0]} (`{c}`)" for c in b_env) + ".",
        "- The other 24 are the block-group vulnerability indicators. Every pair table "
        "carries a `group` column (vulnerability x vulnerability, vulnerability x "
        "environmental, environmental x environmental), and the decision-support table "
        "gives mean |rho| both against all 36 others and against the 24 "
        "non-environmental indicators only, so the effect of the inclusion decision is visible.",
        "- Not read: investment outcomes, FEMA hazard losses, sea level rise, storm "
        "surge, flood."])

    header = f"""# Correlation screen before PCA: vulnerability indicators

Screen only. Nothing has been dropped, imputed or modelled, and no PCA has been run.
The rule being applied is the professor's: if two indicators correlate above
{THRESH}, one is dropped. Which one is dropped is **not** recommended here.

**Method.** Spearman rank correlation, pairwise-complete observations, with n
reported for every listed pair. The absolute value is compared against {THRESH}
unrounded (the listed values are rounded to three decimals for display only);
the sign is reported. A pair is listed if |rho| >= {THRESH}. Near misses are
0.70 <= |rho| < 0.75. A **cluster** is any set of indicators connected through
one or more above-line links. The **minimum drop sets** are every smallest set
of indicators whose removal leaves no above-line pair inside the cluster
(minimum vertex covers, enumerated exhaustively). Tract and block group are
screened separately and never mixed.

**Status column.** DATA_PROCESSING.md grades only the ten tract ACS variables
(clean / threshold approximation / proxy). For every other variable the status
is taken from the variable table in FINDINGS_FOR_PROFESSOR.md Sec 2, which
extends it; `*_decision_support.csv` records which source each status came from.

**Headline-finding column.** "yes" marks the access indicators behind the gray
and green composition result: households with no vehicle (both versions),
multi-unit housing, no internet access, no broadband subscription and minority
population share. At block group, no multi-unit housing, no internet access or
second no-vehicle measure exists; the block-group composition result used
EJScreen's people of colour share (`PEOPCOLORPCT`), which has the same
definition as minority share, so it is marked as the block-group counterpart.

Script: `scripts/correlation_screen.py`. Outputs: `output/correlation_screen/`.
Decision sheets to fill in: `output/correlation_screen/correlation_decisions_tract.csv`
and `output/correlation_screen/correlation_decisions_blockgroup.csv`.

![Tract heatmap](output/correlation_screen/tract_spearman_heatmap.png)

![Block group heatmap](output/correlation_screen/blockgroup_spearman_heatmap.png)
"""
    body = [header,
            grain_report(t, TRACT_VARS, "tract", "Tract (698 tracts)", t_scope, None),
            grain_report(b, BG_VARS, "bg", "Block group (1,843 block groups)", b_scope, b_env)]
    REPORT.write_text("\n".join(body))

    for name, r in [("tract", t), ("block group", b)]:
        print(f"{name}: {r['n_vars']} vars, {len(r['above'])} pairs >= {THRESH}, "
              f"{len(r['clusters'])} clusters, {len(r['near'])} near misses")
    if race_present:
        print(f"race adjuncts still in tract_analysis.csv (excluded): {race_present}")
    print(f"report: {REPORT}\noutputs: {OUT}")


if __name__ == "__main__":
    main()
