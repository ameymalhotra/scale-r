"""Stage A6 of prompt 21: describe the population exposure layers. No model.

Reads exposure_tract.csv, exposure_blockgroup.csv and the block-level
checkpoints written by build_exposure_layers.py. Writes tables to
output/exposure_layers/ and prints everything to stdout (tee to
output/exposure_describe_log.txt).

Usage: ../.venv/bin/python scripts/describe_exposure_layers.py
"""
import sys
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
from vulnerability_loaders import EJSCREEN_PATH, MD_PREFIX  # noqa: E402

BASE = paths.ROOT
CK = paths.OUT_EXPOSURE_CK
OUT = paths.OUT_EXPOSURE_A / "exposure_layers"
NRI = paths.NRI_CSV
NRI_COLS = ["HWAV_EALT", "CFLD_EALT", "CFLD_EALB", "IFLD_EALT", "IFLD_EALB", "HRCN_EALT", "HRCN_EALB"]
PRIMARY = ["slr_3ft", "surge_cat3_any", "surge_cat4_any", "heat_p75", "heat_p95"]
ALL = (["slr_1ft", "slr_2ft", "slr_3ft", "slr_6ft", "low_3ft"]
       + [f"surge_{v}_{t}" for v in ("cat1", "cat2", "cat3", "cat4", "cat5", "cat5max")
          for t in ("any", "over3ft")]
       + ["heat_p75", "heat_p95", "heat_100f", "heat_105f", "heat_110f"])
RHO = 0.75
pd.set_option("display.width", 200)


def sec(t):
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78, flush=True)


def load():
    tr = pd.read_csv(paths.EXPOSURE_DIR / "exposure_tract.csv", dtype={"GEOID": str}).set_index("GEOID")
    bg = pd.read_csv(paths.EXPOSURE_DIR / "exposure_blockgroup.csv", dtype={"GEOID": str}).set_index("GEOID")
    return tr, bg


def county(tr):
    sec("1. COUNTY RESIDENTS EXPOSED")
    t = pd.read_csv(paths.OUT_EXPOSURE_A / "exposure_county_totals.csv")
    print(t[["scenario", "residents_fractional", "share_fractional"]].to_string(
        index=False, float_format=lambda v: f"{v:.4f}"))


def land_vs_pop(tr, bg):
    sec("2. LAND SHARE VERSUS POPULATION SHARE")
    rows = []
    for k in ALL:
        for grain, df in (("tract", tr), ("bg", bg)):
            d = df[df.population > 0][[f"{k}_land_share", f"{k}_pop_share"]].dropna()
            rows.append({"scenario": k, "grain": grain, "n": len(d),
                         "spearman": d.corr(method="spearman").iloc[0, 1]})
    t = pd.DataFrame(rows).pivot(index="scenario", columns="grain", values="spearman").reindex(ALL)
    print(t.to_string(float_format=lambda v: f"{v:+.3f}"))
    t.to_csv(OUT / "land_vs_pop_spearman.csv")

    keep = tr[(tr.population >= 100)]
    for k in PRIMARY:
        L, P = f"{k}_land_share", f"{k}_pop_share"
        d = keep[[L, P, f"{k}_pop_exposed", "population", "jurisdiction", "ALAND"]].dropna(subset=[L, P]).copy()
        d["km2"] = d.ALAND / 1e6
        top_l = d.sort_values(L, ascending=False).head(10)
        top_p = d.sort_values(P, ascending=False).head(10)
        print(f"\n--- {k}: top 10 tracts by LAND share (tracts with >= 100 residents) ---")
        print(top_l[[L, P, f"{k}_pop_exposed", "population", "km2", "jurisdiction"]].to_string(
            float_format=lambda v: f"{v:,.3f}"))
        print(f"--- {k}: top 10 tracts by POPULATION share ---")
        print(top_p[[L, P, f"{k}_pop_exposed", "population", "km2", "jurisdiction"]].to_string(
            float_format=lambda v: f"{v:,.3f}"))
        print(f"overlap of the two top-10 lists: {len(set(top_l.index) & set(top_p.index))}/10")
        d["rank_land"] = d[L].rank(ascending=False)
        d["rank_pop"] = d[P].rank(ascending=False)
        d["gap"] = d.rank_land - d.rank_pop
        print(f"--- {k}: largest disagreements (rank by land minus rank by population) ---")
        cols = [L, P, "rank_land", "rank_pop", "population", "km2", "jurisdiction"]
        print("land ranks much higher than population (land-heavy, few people on wet land):")
        print(d.sort_values("gap").head(5)[cols].to_string(float_format=lambda v: f"{v:,.3f}"))
        print("population ranks much higher than land (people sit on the exposed part):")
        print(d.sort_values("gap", ascending=False).head(5)[cols].to_string(float_format=lambda v: f"{v:,.3f}"))
        top_l.to_csv(OUT / f"top10_land_{k}.csv")
        top_p.to_csv(OUT / f"top10_pop_{k}.csv")


def concentration(tr):
    sec("3. CONCENTRATION: share of exposed residents in the top 10% of tracts")
    d = tr[tr.population > 0]
    n10 = int(round(len(d) * 0.10))
    rows = []
    for k in ALL:
        e = d[f"{k}_pop_exposed"].sort_values(ascending=False)
        tot = e.sum()
        rows.append({"scenario": k, "exposed": tot, "tracts_with_any": int((e > 0.5).sum()),
                     f"top{n10}_share": e.head(n10).sum() / tot if tot else np.nan,
                     "tracts_for_half": int((e.cumsum() < tot / 2).sum() + 1) if tot else np.nan})
    t = pd.DataFrame(rows)
    print(f"populated tracts: {len(d)}, top 10% = {n10} tracts")
    print(t.to_string(index=False, float_format=lambda v: f"{v:,.3f}"))
    t.to_csv(OUT / "concentration.csv", index=False)


def jurisdictions(tr, bg):
    sec("4. JURISDICTIONS HOLDING THE MOST EXPOSED RESIDENTS (block-group assignment, 35 jurisdictions)")
    g = bg.groupby("jurisdiction")
    pop = g.population.sum()
    rows = []
    for k in PRIMARY:
        e = g[f"{k}_pop_exposed"].sum()
        t = pd.DataFrame({"exposed": e, "share_of_county_exposed": e / e.sum(),
                          "share_of_jurisdiction_pop": e / pop, "population": pop})
        t = t.sort_values("exposed", ascending=False)
        print(f"\n--- {k} ---")
        print(t.head(8).to_string(float_format=lambda v: f"{v:,.3f}"))
        t.insert(0, "scenario", k)
        rows.append(t.reset_index())
    pd.concat(rows).to_csv(OUT / "jurisdictions.csv", index=False)
    tj = tr.groupby("jurisdiction")["slr_3ft_pop_exposed"].sum().sort_values(ascending=False)
    print(f"\n(tract assignment gives {tr.jurisdiction.nunique()} jurisdictions; slr_3ft top 3: "
          f"{', '.join(f'{j} {v:,.0f}' for j, v in tj.head(3).items())})")


def block_fracs():
    b = pd.read_csv(CK / "slr_slr_3ft.csv", dtype={"GEOID20": str})[["GEOID20"]]
    import geopandas as gpd
    people = gpd.read_file(CK / "blocks.gpkg", ignore_geometry=True).set_index("GEOID20")["people"]
    b["people"] = b.GEOID20.map(people)
    b["slr_3ft"] = pd.read_csv(CK / "slr_slr_3ft.csv")["frac"]
    for cat in (3, 4):
        b[f"surge_cat{cat}_any"] = pd.read_csv(CK / f"surge_cat{cat}.csv")["any_frac"]
    h = pd.read_csv(CK / "heat.csv")
    thr = pd.read_json(CK / "heat_thresholds.json", typ="series")
    b["heat_p75"] = h[f"ge_{thr['p75']:.4f}_frac"]
    b["heat_p95"] = h[f"ge_{thr['p95']:.4f}_frac"]
    return b


def overlap():
    sec("5. DO THE HAZARDS EXPOSE THE SAME PEOPLE? (block level, summed)")
    b = block_fracs()
    p = b.people.to_numpy()
    rows = []
    for a, c in combinations(PRIMARY, 2):
        x, y = b[a].to_numpy(), b[c].to_numpy()
        ok = np.isfinite(x) & np.isfinite(y)
        x, y, w = x[ok], y[ok], p[ok]
        ea, ec = (w * x).sum(), (w * y).sum()
        lo = (w * np.maximum(0, x + y - 1)).sum()
        ind = (w * x * y).sum()
        hi = (w * np.minimum(x, y)).sum()
        both_blocks = (w * ((x > 0) & (y > 0))).sum()
        rows.append({"pair": f"{a} & {c}", "exposed_a": ea, "exposed_b": ec,
                     "joint_min": lo, "joint_if_independent_in_block": ind, "joint_max": hi,
                     "max_as_share_of_smaller": hi / min(ea, ec),
                     "independent_as_share_of_smaller": ind / min(ea, ec),
                     "residents_in_blocks_touched_by_both": both_blocks})
    t = pd.DataFrame(rows)
    print(t.to_string(index=False, float_format=lambda v: f"{v:,.3f}"))
    t.to_csv(OUT / "hazard_overlap.csv", index=False)


def screen(tr, bg):
    sec(f"6. HAZARD CORRELATION SCREEN (Spearman, pairwise complete, |rho| >= {RHO})")
    nri = pd.read_csv(NRI, dtype={"TRACTFIPS": str}, usecols=["TRACTFIPS"] + NRI_COLS).set_index("TRACTFIPS")
    print(f"NRI tracts: {len(nri)}; exposure tracts missing from NRI: "
          f"{sorted(set(tr.index) - set(nri.index))}")
    for grain, df in (("tract", tr), ("bg", bg)):
        d = df[df.population > 0]
        cols = ([f"{k}_pop_share" for k in ALL] + ["heat_lst_popwt_mean_f"]
                + [f"{k}_land_share" for k in ALL])
        x = d[cols].copy()
        if grain == "tract":
            x = x.join(nri[NRI_COLS])
        m = x.corr(method="spearman")
        m.to_csv(OUT / f"spearman_matrix_{grain}.csv")
        pairs = []
        for i, j in combinations(m.columns, 2):
            r = m.loc[i, j]
            if abs(r) >= RHO:
                n = int(x[[i, j]].dropna().shape[0])
                pairs.append({"a": i, "b": j, "rho": r, "n": n})
        p = pd.DataFrame(pairs).sort_values("rho", key=abs, ascending=False)
        p.to_csv(OUT / f"screen_pairs_{grain}.csv", index=False)
        print(f"\n--- {grain}: {len(cols) + (len(NRI_COLS) if grain == 'tract' else 0)} variables, "
              f"{len(p)} pairs at |rho| >= {RHO} (n = {len(d)} populated units) ---")
        print(p.to_string(index=False, float_format=lambda v: f"{v:+.3f}"))
        if grain == "tract":
            sub = m.loc[[f"{k}_pop_share" for k in PRIMARY] + ["heat_lst_popwt_mean_f"], NRI_COLS]
            print("\nprimary population shares against the NRI loss columns:")
            print(sub.to_string(float_format=lambda v: f"{v:+.3f}"))


def heat_density(tr, bg):
    sec("7. SURFACE HEAT VERSUS HOUSING DENSITY (Spearman)")
    ej = pd.read_csv(EJSCREEN_PATH, dtype=str, usecols=["ID", "ACSTOTHU"], low_memory=False)
    ej["GEOID"] = ej["ID"].astype(str).str.zfill(12)
    ej = ej[ej.GEOID.str.startswith(MD_PREFIX)].set_index("GEOID")
    hu = pd.to_numeric(ej.ACSTOTHU, errors="coerce")
    out = []
    for grain, df in (("tract", tr), ("bg", bg)):
        d = df[df.population > 0].copy()
        if grain == "bg":
            d["housing_units"] = hu.reindex(d.index)
        else:
            d["housing_units"] = hu.groupby(hu.index.str[:11]).sum(min_count=1).reindex(d.index)
        km2 = (d.ALAND / 1e6).where(d.ALAND > 0)
        d["housing_density"] = d.housing_units / km2
        d["pop_density"] = d.population / km2
        for v in ["heat_p75_pop_share", "heat_p95_pop_share", "heat_lst_popwt_mean_f",
                  "heat_p75_land_share", "heat_p95_land_share"]:
            for dens in ("housing_density", "pop_density"):
                s = d[[v, dens]].dropna()
                out.append({"grain": grain, "heat": v, "density": dens, "n": len(s),
                            "spearman": s.corr(method="spearman").iloc[0, 1]})
    t = pd.DataFrame(out)
    print(t.to_string(index=False, float_format=lambda v: f"{v:+.3f}"))
    t.to_csv(OUT / "heat_vs_density.csv", index=False)
    print("tract housing units = sum of EJScreen ACSTOTHU over the tract's block groups")


def describe_vars(tr, bg):
    sec("0. DISTRIBUTIONS OF POPULATION SHARES (populated units)")
    rows = []
    for grain, df in (("tract", tr), ("bg", bg)):
        d = df[df.population > 0]
        for k in ALL + ["heat_lst_popwt_mean"]:
            c = f"{k}_pop_share" if k != "heat_lst_popwt_mean" else "heat_lst_popwt_mean_f"
            s = d[c].dropna()
            rows.append({"grain": grain, "var": c, "n": len(s), "zero": int((s == 0).sum()),
                         "mean": s.mean(), "p25": s.quantile(.25), "median": s.median(),
                         "p75": s.quantile(.75), "max": s.max()})
    t = pd.DataFrame(rows)
    print(t.to_string(index=False, float_format=lambda v: f"{v:,.3f}"))
    t.to_csv(OUT / "distributions.csv", index=False)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tr, bg = load()
    describe_vars(tr, bg)
    county(tr)
    land_vs_pop(tr, bg)
    concentration(tr)
    jurisdictions(tr, bg)
    overlap()
    screen(tr, bg)
    heat_density(tr, bg)


if __name__ == "__main__":
    main()
