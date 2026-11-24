"""Stage B of prompt 21 (as amended by prompt 23): population exposure against investment.

Descriptive and correlational only. No model, no imputation. The analysis
tables are read, never modified; exposure columns are joined by GEOID in memory.

Frames
  tract  tract_analysis.csv, 698 tracts (completed, funded, ongoing projects)
  bg     blockgroup_analysis.csv, binaries and type shares only (no per capita)

Exposure measures, one per hazard family at the primary scenarios
  sea level rise  slr_3ft
  storm surge     surge_cat3_any, surge_cat4_any
  surface heat    heat_lst_popwt_mean_f (population-weighted mean), heat_p95
For each: population share (main), residents exposed (count, totals only),
land share (comparison). Other scenarios are sensitivity; Category 5 uses the
corrected cat5max only; the heat 75th percentile is not used.

Pairing rule (caution 12): shares go with per-person, per-area, binary and
type share outcomes. Counts go with total investment only, as a partial
Spearman controlling for population, and shown raw with a note.

P-values are Benjamini-Hochberg FDR adjusted within each family of tests and
are NOT adjusted for spatial dependence. Moran's I permutations are seeded
(12086, as in parts 5 and 6b), so reruns are identical.

Usage: ../.venv/bin/python scripts/exposure_vs_investment.py
Outputs: output/exposure/*.csv, log output/exposure/stage_b_log.txt (tee)
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from esda.moran import Moran
from scipy import stats
from statsmodels.stats.multitest import multipletests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
paths.use("05_analysis")
from analysis_variables import add_type_scale_measures, load_bg, load_tract  # noqa: E402
from part5_diagnostics import build_knn_weights  # noqa: E402

BASE = paths.ROOT
OUT = paths.OUT_EXPOSURE_B
warnings.filterwarnings("ignore", category=RuntimeWarning)
RNG = np.random.default_rng(20261105)
N_BOOT = 2000
LOW_POP = 100
MORAN_SEED = 12086  # permutation seed used by every Moran's I in this project

# (key, label, has land share, has count)
PRIMARY = [
    ("slr_3ft", "Sea level rise 3 ft", True, True),
    ("surge_cat3_any", "Surge Category 3", True, True),
    ("surge_cat4_any", "Surge Category 4", True, True),
    ("heat_popwt", "Heat, population-weighted mean", False, False),
    ("heat_p95", "Heat, at or above p95 (113.27 F)", True, True),
]
SENSITIVITY = ["slr_1ft", "slr_2ft", "slr_6ft", "low_3ft", "surge_cat1_any", "surge_cat2_any",
               "surge_cat5max_any", "surge_cat3_over3ft", "surge_cat4_over3ft",
               "heat_100f", "heat_105f", "heat_110f"]

RATE_OUTCOMES_TRACT = ["investment_per_capita", "investment_per_area",
                       "investment_any_excl_county", "investment_any_single_unit",
                       "type_gray_share", "type_green_share", "type_blue_share",
                       "type_hybrid_share", "gray_drainage_stormwater_share"]
RATE_OUTCOMES_BG = ["investment_any_excl_county", "investment_any_single_unit",
                    "type_gray_share", "type_green_share", "type_blue_share",
                    "type_hybrid_share", "gray_drainage_stormwater_share"]
SPARSE = {"type_blue_share": "Blue: 28 projects, 19 single-unit units (sparse)"}


def sec(t):
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78, flush=True)


def share_col(key):
    return "heat_lst_popwt_mean_f" if key == "heat_popwt" else f"{key}_pop_share"


def fmt(df):
    return df.to_string(index=False, float_format=lambda v: f"{v:,.4g}")


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------

def load_frames():
    tr = add_type_scale_measures(load_tract())
    bg = add_type_scale_measures(load_bg(), per_capita=False)
    sub_t = pd.read_csv(paths.OUT_CORRELATION / "part7_gray/2b_tract_with_subcat_shares.csv", dtype={"GEOID": str})
    sub_b = pd.read_csv(paths.OUT_CORRELATION / "part7_gray/2b_bg_with_subcat_shares.csv", dtype={"GEOID": str})
    tr = tr.merge(sub_t[["GEOID", "gray_drainage_stormwater_share"]], on="GEOID", how="left", validate="1:1")
    bg = bg.merge(sub_b[["GEOID", "gray_drainage_stormwater_share"]], on="GEOID", how="left", validate="1:1")
    tr["single_unit_per_capita"] = tr["path_single_unit_amt"] / tr["population"].where(tr["population"] > 0)
    tr["single_unit_total"] = tr["path_single_unit_amt"]
    ex_t = pd.read_csv(paths.EXPOSURE_DIR / "exposure_tract.csv", dtype={"GEOID": str})
    ex_b = pd.read_csv(paths.EXPOSURE_DIR / "exposure_blockgroup.csv", dtype={"GEOID": str})
    keep = lambda d: d.drop(columns=["population", "ALAND"]).rename(columns={"jurisdiction": "jurisdiction_centroid"})  # noqa: E731
    n0 = len(tr)
    tr = tr.merge(keep(ex_t), on="GEOID", how="left", validate="1:1")
    bg = bg.merge(keep(ex_b), on="GEOID", how="left", validate="1:1")
    assert len(tr) == n0 == 698 and tr["slr_3ft_pop_share"].notna().all()
    print(f"tract frame {len(tr)}, exposure joined for all; bg frame {len(bg)}, "
          f"{int(bg.slr_3ft_pop_share.notna().sum())} with residents")
    print(f"tract population check vs exposure table: max diff "
          f"{(tr.population - tr.acs_tract_population).abs().max():.0f}")
    return tr, bg


# --------------------------------------------------------------------------
# statistics
# --------------------------------------------------------------------------

def spearman(x, y):
    d = pd.concat([x, y], axis=1).dropna()
    if len(d) < 10 or d.iloc[:, 0].nunique() < 2 or d.iloc[:, 1].nunique() < 2:
        return np.nan, np.nan, len(d)
    r, p = stats.spearmanr(d.iloc[:, 0], d.iloc[:, 1])
    return r, p, len(d)


def partial_spearman(x, y, z):
    d = pd.concat([x, y, z], axis=1).dropna()
    rk = d.rank()
    def resid(a, b):
        b1 = np.column_stack([np.ones(len(b)), b])
        return a - b1 @ np.linalg.lstsq(b1, a, rcond=None)[0]
    rx, ry = resid(rk.iloc[:, 0].values, rk.iloc[:, 2].values), resid(rk.iloc[:, 1].values, rk.iloc[:, 2].values)
    r = np.corrcoef(rx, ry)[0, 1]
    n = len(d)
    t = r * np.sqrt((n - 3) / max(1e-12, 1 - r ** 2))
    return r, 2 * stats.t.sf(abs(t), n - 3), n


def boot_diff(df, a, b, y):
    """Bootstrap 95% interval for rho(a, y) - rho(b, y) on the same units."""
    d = df[[a, b, y]].dropna()
    if len(d) < 30:
        return np.nan, np.nan
    rk = d.rank().to_numpy()
    n = len(d)
    out = np.empty(N_BOOT)
    for i in range(N_BOOT):
        s = rk[RNG.integers(0, n, n)]
        c = np.corrcoef(s.T)
        out[i] = c[0, 2] - c[1, 2]
    return np.nanpercentile(out, 2.5), np.nanpercentile(out, 97.5)


def add_fdr(t, family_col="family"):
    t = t.copy()
    t["p_fdr"] = np.nan
    for _, idx in t.groupby(family_col).groups.items():
        p = t.loc[idx, "p"]
        ok = p.notna()
        if ok.any():
            t.loc[p[ok].index, "p_fdr"] = multipletests(p[ok], method="fdr_bh")[1]
    return t


# --------------------------------------------------------------------------
# 1 and 2: correlations, population versus land
# --------------------------------------------------------------------------

def correlations(df, grain, keys, outcomes, family, measures=("pop", "land")):
    rows = []
    for key in keys:
        for m in measures:
            col = share_col(key) if m == "pop" else f"{key}_land_share"
            if col not in df:
                continue
            for y in outcomes:
                r, p, n = spearman(df[col], df[y])
                rows.append({"family": family, "grain": grain, "exposure": key, "measure": m,
                             "outcome": y, "rho": r, "p": p, "n": n,
                             "sparse_note": SPARSE.get(y, "")})
    return rows


def count_tests(df, keys, total_col, family):
    rows = []
    for key in keys:
        c = f"{key}_pop_exposed"
        if c not in df:
            continue
        r0, p0, n0 = spearman(df[c], df[total_col])
        r1, p1, n1 = partial_spearman(df[c], df[total_col], df["population"])
        rows.append({"family": family, "grain": "tract", "exposure": key, "measure": "count_raw",
                     "outcome": total_col, "rho": r0, "p": p0, "n": n0,
                     "sparse_note": "count with count: size drives both, shown for reference only"})
        rows.append({"family": family, "grain": "tract", "exposure": key, "measure": "count_partial_pop",
                     "outcome": total_col, "rho": r1, "p": p1, "n": n1, "sparse_note": ""})
    return rows


def pop_vs_land(df, grain, outcomes, label):
    rows = []
    for key, name, has_land, _ in PRIMARY:
        if not has_land:
            continue
        for y in outcomes:
            rp, _, n = spearman(df[share_col(key)], df[y])
            rl, _, _ = spearman(df[f"{key}_land_share"], df[y])
            lo, hi = boot_diff(df, share_col(key), f"{key}_land_share", y)
            rows.append({"grain": label, "exposure": key, "outcome": y, "n": n, "rho_pop": rp,
                         "rho_land": rl, "diff_pop_minus_land": rp - rl, "boot95_lo": lo, "boot95_hi": hi,
                         "interval_excludes_0": bool(lo > 0 or hi < 0) if np.isfinite(lo) else False})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# 3 and 4: coverage gap, investment per exposed resident
# --------------------------------------------------------------------------

def coverage_gap(tr):
    sec("3. COVERAGE GAP: high population exposure and no sited project")
    rows, lists = [], []
    d = tr[tr.population >= LOW_POP]
    for key, name, _, has_count in PRIMARY:
        if not has_count:
            continue
        e = f"{key}_pop_exposed"
        tot = tr[e].sum()
        none = tr[tr.investment_any_single_unit == 0]
        rows.append({"exposure": key, "county_exposed": tot, "exposed_in_tracts_no_sited_project": none[e].sum(),
                     "share": none[e].sum() / tot, "tracts_no_sited_project": len(none),
                     "tracts_no_sited_project_with_any_exposed": int((none[e] > 0.5).sum())})
        top = (d[d.investment_any_single_unit == 0].sort_values(e, ascending=False).head(20)
               [["GEOID", "jurisdiction_centroid", "population", e, share_col(key),
                 "investment_total", "investment_per_capita", "investment_any_excl_county"]])
        top.insert(0, "exposure", key)
        lists.append(top)
        print(f"\n--- {name}: top 20 tracts with no sited project (>= {LOW_POP} residents) ---")
        print(fmt(top.drop(columns="exposure")))
    t = pd.DataFrame(rows)
    print("\nexposed residents living in tracts with no sited project:")
    print(fmt(t))
    t.to_csv(OUT / "coverage_gap_summary.csv", index=False)
    pd.concat(lists).to_csv(OUT / "coverage_gap_top20.csv", index=False)
    # heat mean: hottest tracts without a sited project
    h = d[d.investment_any_single_unit == 0].sort_values("heat_lst_popwt_mean_f", ascending=False).head(20)
    print("\n--- heat population-weighted mean: hottest 20 tracts with no sited project ---")
    print(fmt(h[["GEOID", "jurisdiction_centroid", "population", "heat_lst_popwt_mean_f",
                 "investment_total", "investment_per_capita"]]))
    h.assign(exposure="heat_popwt")[["exposure", "GEOID", "jurisdiction_centroid", "population",
                                     "heat_lst_popwt_mean_f", "investment_total", "investment_per_capita"]] \
        .to_csv(OUT / "coverage_gap_top20_heat_popwt.csv", index=False)


def per_exposed_resident(tr):
    sec("4. INVESTMENT PER EXPOSED RESIDENT, BY EXPOSURE TERCILE")
    rows = []
    for key, name, _, has_count in PRIMARY:
        s = tr[share_col(key)]
        if key == "heat_popwt":
            grp = pd.qcut(s.rank(method="first"), 3, labels=["T1 coolest", "T2", "T3 hottest"])
        else:
            pos = s > 0
            grp = pd.Series("0 none exposed", index=tr.index, dtype=object)
            if pos.sum() >= 3:
                grp[pos] = pd.qcut(s[pos].rank(method="first"), 3, labels=["T1 low", "T2 mid", "T3 high"]).astype(str)
        for g, d in tr.groupby(grp, observed=True):
            r = {"exposure": key, "group": str(g), "tracts": len(d),
                 "share_range": f"{d[share_col(key)].min():.3g} to {d[share_col(key)].max():.3g}",
                 "residents": d.population.sum(), "investment_total": d.investment_total.sum(),
                 "per_resident": d.investment_total.sum() / d.population.sum(),
                 "single_unit_per_resident": d.path_single_unit_amt.sum() / d.population.sum(),
                 "median_tract_per_capita": d.investment_per_capita.median(),
                 "share_with_sited_project": d.investment_any_single_unit.mean()}
            if has_count:
                ex = d[f"{key}_pop_exposed"].sum()
                r["exposed_residents"] = ex
                r["per_exposed_resident"] = d.investment_total.sum() / ex if ex > 0 else np.nan
                r["single_unit_per_exposed_resident"] = d.path_single_unit_amt.sum() / ex if ex > 0 else np.nan
            rows.append(r)
    t = pd.DataFrame(rows)
    print(fmt(t))
    t.to_csv(OUT / "per_exposed_resident_terciles.csv", index=False)


# --------------------------------------------------------------------------
# 5: Moran's I
# --------------------------------------------------------------------------

def morans(tr, bg):
    sec("5. MORAN'S I ON POPULATION EXPOSURE (k = 6 nearest neighbours, rank-transformed, 999 permutations)")
    rows = []
    for grain, df in (("tract", tr), ("bg", bg[bg.population > 0])):
        for key, name, _, _ in PRIMARY:
            col = share_col(key)
            d = df[["GEOID", col]].dropna()
            w = build_knn_weights(d["GEOID"].tolist(), grain)
            # same seed as part5_diagnostics.py and part6b_moran_transforms.py, set per
            # call so each p_sim / z_sim is reproducible whatever the call order
            np.random.seed(MORAN_SEED)
            m = Moran(stats.rankdata(d[col].values), w, permutations=999)
            rows.append({"grain": grain, "exposure": col, "n": len(d), "I": m.I,
                         "p_perm": m.p_sim, "z": m.z_sim})
    t = pd.DataFrame(rows)
    print(fmt(t))
    t.to_csv(OUT / "morans_i.csv", index=False)


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tr, bg = load_frames()
    pk = [k for k, *_ in PRIMARY]

    sec("1. SPEARMAN: exposure against investment (tract, 698)")
    rows = correlations(tr, "tract", pk, RATE_OUTCOMES_TRACT, "tract primary")
    rows += count_tests(tr, pk, "investment_total", "tract primary")
    # single-unit sited investment only
    rows += correlations(tr, "tract", pk, ["single_unit_per_capita", "investment_any_single_unit"],
                         "tract single-unit")
    rows += count_tests(tr, pk, "single_unit_total", "tract single-unit")
    # sensitivity scenarios, population share only
    rows += correlations(tr, "tract", SENSITIVITY,
                         ["investment_per_capita", "investment_any_excl_county",
                          "investment_any_single_unit", "type_gray_share", "gray_drainage_stormwater_share"],
                         "tract sensitivity", measures=("pop",))
    t = add_fdr(pd.DataFrame(rows))
    t.to_csv(OUT / "spearman_tract.csv", index=False)
    for fam in ["tract primary", "tract single-unit", "tract sensitivity"]:
        x = t[t.family == fam]
        print(f"\n--- {fam} ---")
        print(fmt(x.drop(columns=["family", "grain"])))

    sec("2. POPULATION VERSUS LAND (tract): rho(pop share) minus rho(land share), bootstrap 95% interval")
    pl = pop_vs_land(tr, "tract", RATE_OUTCOMES_TRACT + ["single_unit_per_capita"], "tract")
    print(fmt(pl))
    pl.to_csv(OUT / "pop_vs_land_tract.csv", index=False)

    coverage_gap(tr)
    per_exposed_resident(tr)
    morans(tr, bg)

    sec("6. BLOCK GROUP: binaries and type shares, all populated vs excluding low-reliability")
    b_all = bg[bg.population > 0]
    b_rel = b_all[b_all.bg_low_reliability != 1]
    print(f"populated block groups {len(b_all)}, excluding {len(b_all) - len(b_rel)} low-reliability -> {len(b_rel)}")
    rows = correlations(b_all, "bg all", pk, RATE_OUTCOMES_BG, "bg all")
    rows += correlations(b_rel, "bg reliable", pk, RATE_OUTCOMES_BG, "bg reliable")
    rows += correlations(b_all, "bg all", SENSITIVITY, ["investment_any_excl_county", "investment_any_single_unit"],
                         "bg sensitivity", measures=("pop",))
    tb = add_fdr(pd.DataFrame(rows))
    tb.to_csv(OUT / "spearman_bg.csv", index=False)
    for fam in ["bg all", "bg reliable", "bg sensitivity"]:
        print(f"\n--- {fam} ---")
        print(fmt(tb[tb.family == fam].drop(columns=["family"])))
    plb = pd.concat([pop_vs_land(b_all, "bg all", RATE_OUTCOMES_BG, "bg all"),
                     pop_vs_land(b_rel, "bg reliable", RATE_OUTCOMES_BG, "bg reliable")])
    print("\npopulation versus land, block group:")
    print(fmt(plb))
    plb.to_csv(OUT / "pop_vs_land_bg.csv", index=False)


if __name__ == "__main__":
    main()
