"""Stage 2: baseline flood risk in dollars for every building (prompt 27, D-136 to D-143).

    ../.venv/bin/python -I scripts/benefit/baseline_risk.py

Steps (plain words):
1. Water depth at each building for each event: storm surge Categories 1 to 5
   (NHC SLOSH maximum-of-maximums), FEMA 1% and 0.2% annual chance floods
   (base flood elevation minus ground), and the same events with 1, 2 and 3 ft
   of sea level rise added. Depth inside the building = depth at the ground
   minus the first-floor height (NSI foundation height).
2. Damage = depth-damage curve x structure value, plus the contents curve x
   contents value (D-138).
3. Expected annual damage (EAD): the events are put on one probability scale
   (hurricane strike rates, D-136; FEMA 1% and 0.2%), the larger damage of
   the two hazard families is kept at each probability so the same flood is
   not counted twice, and the curve is integrated (D-137).
4. Displacement (FEMA standard values, assumption, D-139) and people exposed.
5. Provisional check against NFIP claims per occupied housing unit (ACS)
   by tract (D-140), and a comparison with sited investment per resident.

Outputs: data/processed/benefit/ead_buildings.parquet, ead_tract.csv and
outputs/benefit/stage2/*.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import paths  # noqa: E402

OUT = paths.OUT_BENEFIT / "stage2"
SEED = 20261111
SLR_FT = [0, 1, 2, 3]
FEMA_P = [0.01, 0.002]
STORY_CAP = 60                 # NSI has a few impossible story counts (up to 20,102)
HALF_LIFE_YEARS = 15           # recency weight for claims (D-140)
CLAIM_YEARS = (1978, 2025)     # full years only; 2026 is partial
DAYS_PER_FT, DAYS_CAP_FT = 45.0, 5.0   # FEMA example DDF, 0 to 5 ft (D-139)

COLS = ["bid", "fd_id", "GEOID_tract", "GEOID_bg", "occtype", "found_type", "found_ht", "num_story", "sqft",
        "st_damcat", "val_struct", "val_cont", "fullrep", "residents_night", "pop2amo65", "resunits",
        "fema_zone", "fema_zone_subtype", "fema_bfe_ft_navd88", "ground_elev_ft_navd88", "jv_alloc",
        "slr_1ft", "slr_2ft", "slr_3ft", "slr_6ft"] + [f"surge_cat{k}_depth_ft" for k in range(1, 6)]


# ---------------------------------------------------------------- inputs
def load_buildings():
    b = pd.read_parquet(paths.BUILDINGS_PARQUET, columns=COLS)
    b["stories"] = b.num_story.clip(1, STORY_CAP)
    return b.reset_index(drop=True)


def load_curves():
    c = pd.read_csv(paths.DEPTH_DAMAGE_CSV)
    cur = {}
    for (occ, comp, water), g in c.groupby(["occtype", "component", "water"]):
        g = g.sort_values("depth_ft")
        cur[(occ, comp, water)] = dict(x=g.depth_ft.to_numpy(), mean=g.damage_pct_mean.to_numpy() / 100,
                                       low=g.damage_pct_low.to_numpy() / 100, high=g.damage_pct_high.to_numpy() / 100,
                                       source=g.curve_source.iloc[0])
    return cur


def curve_key(occ, found, water, cur):
    """Curve used for one building: salt curves where USACE has them, pier versions for pier foundations."""
    if water == "salt":
        if found == "P" and (occ + "-PIER", "structure", "salt") in cur:
            return occ + "-PIER", "salt"
        if (occ, "structure", "salt") in cur:
            return occ, "salt"
    return occ, "fresh"


def rates():
    r = pd.read_csv(paths.HURRICANE_RATES_CSV).sort_values("category")
    return r.annual_rate_at_least.to_numpy()      # P(at least Category k) per year


# ---------------------------------------------------------------- damage
def event_depths(b, slr):
    """Water depth above ground (ft) for the 7 events, with `slr` ft of sea level rise added."""
    d = {}
    for k in range(1, 6):
        s = b[f"surge_cat{k}_depth_ft"].to_numpy(float)
        d[f"surge{k}"] = np.where(s > 0, s + slr, 0.0)    # rise added only where the event already floods (D-141)
    bfe = b.fema_bfe_ft_navd88.to_numpy(float)
    g = b.ground_elev_ft_navd88.to_numpy(float)
    f1 = np.where(np.isfinite(bfe) & np.isfinite(g), bfe - g + slr, 0.0)
    f1 = np.clip(f1, 0, None)
    d["fema1"] = f1
    d["fema02"] = f1.copy()          # no 0.2% elevations in the NFHL: 1% depth used, a lower bound (D-137)
    return d


def damage_fractions(b, depth_ground, water_vec, cur, stat):
    """Structure and contents damage fractions for one event."""
    din = depth_ground - b.found_ht.to_numpy(float)
    fs = np.zeros(len(b))
    fc = np.zeros(len(b))
    egm = np.zeros(len(b), bool)
    wet = depth_ground > 0
    keys = pd.Series(list(zip(b.occtype, b.found_type, water_vec)))
    for (occ, found, water), idx in keys[wet].groupby(keys[wet]).groups.items():
        occ2, w2 = curve_key(occ, found, water, cur)
        if (occ2, "structure", w2) not in cur:
            continue
        cs, cc = cur[(occ2, "structure", w2)], cur[(occ2, "contents", w2)]
        ii = np.asarray(idx)
        fs[ii] = np.interp(din[ii], cs["x"], cs[stat])
        fc[ii] = np.interp(din[ii], cc["x"], cc[stat])
        egm[ii] = "EGM" in cc["source"]
    return fs, fc, egm, din


def event_damage(b, depth, water_vec, cur, stat):
    fs, fc, egm, din = damage_fractions(b, depth, water_vec, cur, stat)
    vs = b.val_struct.to_numpy(float)
    contents_base = np.where(egm, vs, b.val_cont.to_numpy(float))   # EGM curves are scaled to structure value (D-138)
    return fs * vs, fc * contents_base, din, fs


# ---------------------------------------------------------------- probability
def ead(surge_vals, fema_vals, p_surge, how):
    """EAD from the two hazard families (D-137). Arrays are (n_buildings, n_events)."""
    grid = np.array(sorted(set(p_surge) | set(FEMA_P), reverse=True))

    def step(vals, ps):
        out = np.zeros((vals.shape[0], len(grid)))
        for j, p in enumerate(grid):
            ok = [i for i, q in enumerate(ps) if q >= p - 1e-12]
            if ok:
                out[:, j] = vals[:, ok[-1]]          # rarest family event at least as frequent as p
        return out

    D = np.maximum(step(surge_vals, list(p_surge)), step(fema_vals, FEMA_P))
    D = np.maximum.accumulate(D, axis=1)               # rarer events never do less damage
    dp = grid[:-1] - grid[1:]
    if how == "low":
        body = (D[:, :-1] * dp).sum(1)
    elif how == "high":
        body = (D[:, 1:] * dp).sum(1)
    else:
        body = (0.5 * (D[:, :-1] + D[:, 1:]) * dp).sum(1)
    return body + D[:, -1] * grid[-1]


# ---------------------------------------------------------------- displacement
def displacement_rates():
    v = pd.read_csv(paths.FEMA_STANDARD_VALUES_CSV)
    rent = v[v.value_id.str.startswith("disp_rent_")].set_index("value_id").value
    once = v[v.value_id.str.startswith("disp_oneoff_")].set_index("value_id").value
    rent.index = rent.index.str.replace("disp_rent_", "", regex=False)
    once.index = once.index.str.replace("disp_oneoff_", "", regex=False)
    assert {"RES1", "RES3a-f", "COM1"} <= set(rent.index)
    return rent, once


def disp_key(occ):
    g = occ.split("-")[0]
    if g == "RES6":
        return "RES1_nursing"         # FEMA's "Nursing Home" row (Hazus RES6)
    if g.startswith("RES3"):
        return "RES3a-f"
    return g


def displacement_cost(b, din, rent, once):
    """FEMA displacement: rent x flooded floor area x days, plus a one-time cost (2021 dollars)."""
    keys = b.occtype.map(disp_key)
    r = keys.map(rent).fillna(0).to_numpy()
    o = keys.map(once).fillna(0).to_numpy()
    area = b.sqft.to_numpy(float) / b.stories.to_numpy(float)   # only the flooded (ground) floor
    days = DAYS_PER_FT * np.clip(din, 0, DAYS_CAP_FT)
    hit = din > 0
    return np.where(hit, r * area * days / (365.25 / 12) + o * area, 0.0), np.where(hit, days, 0.0)


# ---------------------------------------------------------------- claims and ACS
def observed_claims():
    c = pd.read_csv(paths.NFIP_TRACT_YEAR_CSV, dtype={"GEOID": str})
    y0, y1 = CLAIM_YEARS
    c = c[(c.year >= y0) & (c.year <= y1)]
    years = np.arange(y0, y1 + 1)
    w = 0.5 ** ((y1 - years) / HALF_LIFE_YEARS)
    wmap = dict(zip(years, w))
    c["w"] = c.year.map(wmap)
    g = c.assign(wp=c.paid_building_contents * c.w).groupby("GEOID")
    out = pd.DataFrame({
        "claims_weighted_annual_nominal": g.wp.sum() / w.sum(),
        "claims_annual_nominal_all_years": g.paid_building_contents.sum() / len(years),
        "claims_annual_nominal_2000_2025": c[c.year >= 2000].groupby("GEOID").paid_building_contents.sum() / 26,
        "claims_paid_count": g.claims_paid.sum()})
    return out.fillna(0), dict(zip(years.tolist(), np.round(w, 4).tolist()))


def occupied_units():
    f = next((paths.ACS_BG_DIR / "B25003-Tenure").glob("*B25003-Data.csv"))
    a = pd.read_csv(f, skiprows=[1], dtype=str)
    a["GEOID_bg"] = a.GEO_ID.str[-12:]
    a["units"] = pd.to_numeric(a.B25003_001E, errors="coerce")
    a["GEOID"] = a.GEOID_bg.str[:11]
    return a.groupby("GEOID").units.sum()


def boot_spearman(x, y, n=1000):
    rng = np.random.default_rng(SEED)
    x, y = np.asarray(x), np.asarray(y)
    s = []
    for _ in range(n):
        i = rng.integers(0, len(x), len(x))
        s.append(spearmanr(x[i], y[i]).statistic)
    return [round(float(np.percentile(s, 2.5)), 3), round(float(np.percentile(s, 97.5)), 3)]


# ---------------------------------------------------------------- main
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    b = load_buildings()
    cur = load_curves()
    p_surge = rates()
    rent, once = displacement_rates()
    n = len(b)
    S = {"buildings": n, "hurricane_p_at_least": p_surge.round(5).tolist(), "fema_p": FEMA_P}

    salt = np.full(n, "salt", dtype=object)
    fema_water = np.where(b.fema_zone.eq("VE"), "salt", "fresh").astype(object)   # D-138
    res = pd.DataFrame({"bid": b.bid, "fd_id": b.fd_id, "GEOID_tract": b.GEOID_tract, "GEOID_bg": b.GEOID_bg})
    resid = b.residents_night.to_numpy(float)
    floor_share = 1 / b.stories.to_numpy(float)
    res_dmg = b.st_damcat.eq("RES").to_numpy()

    for slr in SLR_FT:
        dep = event_depths(b, slr)
        tag = f"slr{slr}"
        for stat, how in [("low", "low"), ("mean", "mid"), ("high", "high")]:
            if slr and stat != "mean":
                continue
            sv, fv, svs, fvs = [], [], [], []
            disp_s, disp_f, pe_s, pe_f, pd_s, pd_f = [], [], [], [], [], []
            for k in range(1, 6):
                ds, dc, din, _ = event_damage(b, dep[f"surge{k}"], salt, cur, stat)
                sv.append(ds + dc)
                svs.append(ds)
                if stat == "mean":
                    c, _days = displacement_cost(b, din, rent, once)
                    disp_s.append(c)
                    pe_s.append(np.where(dep[f"surge{k}"] > 0, resid, 0))
                    pd_s.append(np.where(din > 0, resid * floor_share, 0))
                    if slr == 0:
                        res[f"dmg_surge{k}"] = ds + dc
            for key in ["fema1", "fema02"]:
                ds, dc, din, _ = event_damage(b, dep[key], fema_water, cur, stat)
                fv.append(ds + dc)
                fvs.append(ds)
                if stat == "mean":
                    c, _days = displacement_cost(b, din, rent, once)
                    disp_f.append(c)
                    pe_f.append(np.where(dep[key] > 0, resid, 0))
                    pd_f.append(np.where(din > 0, resid * floor_share, 0))
                    if slr == 0 and key == "fema1":
                        res["dmg_fema1"] = ds + dc
                        res["depth_fema1_ft"] = dep[key]
            SV, FV = np.column_stack(sv), np.column_stack(fv)
            res[f"ead_{how}_{tag}"] = ead(SV, FV, p_surge, how)
            if stat == "mean":
                zero = np.zeros_like(FV)
                res[f"ead_surge_only_{tag}"] = ead(SV, zero, p_surge, "mid")
                res[f"ead_fema_only_{tag}"] = ead(np.zeros_like(SV), FV, p_surge, "mid")
                res[f"ead_struct_{tag}"] = ead(np.column_stack(svs), np.column_stack(fvs), p_surge, "mid")
                res[f"ead_disp_{tag}"] = ead(np.column_stack(disp_s), np.column_stack(disp_f), p_surge, "mid")
                res[f"res_exposed_annual_{tag}"] = ead(np.column_stack(pe_s), np.column_stack(pe_f), p_surge, "mid")
                res[f"res_displaced_annual_{tag}"] = ead(np.column_stack(pd_s), np.column_stack(pd_f), p_surge, "mid")
        print(f"done sea level rise +{slr} ft", flush=True)

    # full replacement cost variant (structure only rescaled), mid only
    ratio = (b.fullrep / b.val_struct).replace([np.inf, -np.inf], np.nan).fillna(1).to_numpy()
    res["ead_mid_slr0_fullrep"] = res.ead_mid_slr0 + res.ead_struct_slr0 * (ratio - 1)
    for k in [1, 2, 3, 6]:
        res[f"slr_{k}ft_chronic"] = b[f"slr_{k}ft"].to_numpy()
    res["residents_night"] = resid
    res["residents_o65"] = b.pop2amo65.to_numpy(float)
    res["val_struct"] = b.val_struct.to_numpy(float)
    res["val_cont"] = b.val_cont.to_numpy(float)
    res["residential"] = res_dmg
    res["wet_fema1"] = res.depth_fema1_ft > 0
    res["wet_cat3"] = b.surge_cat3_depth_ft.to_numpy() > 0
    res.to_parquet(paths.EAD_BUILDINGS_PARQUET, index=False)

    # ------------------------------------------------------------ county summary
    def tot(c):
        return float(res[c].sum())
    S["ead_county"] = {c: round(tot(c) / 1e6, 1) for c in res.columns if c.startswith("ead_")}
    S["ead_county_unit"] = "million dollars per year (NSI August 2025 prices; displacement 2021 dollars)"
    S["damage_by_event_million"] = {c: round(tot(c) / 1e6, 1) for c in res.columns if c.startswith("dmg_")}
    S["buildings_with_ead"] = int((res.ead_mid_slr0 > 0).sum())
    S["res_exposed_annual"] = {s: round(tot(f"res_exposed_annual_slr{s}")) for s in SLR_FT}
    S["res_displaced_annual"] = {s: round(tot(f"res_displaced_annual_slr{s}")) for s in SLR_FT}
    S["residents_wet_fema1"] = round(float(res.loc[res.wet_fema1, "residents_night"].sum()))
    S["residents_wet_cat3"] = round(float(res.loc[res.wet_cat3, "residents_night"].sum()))
    S["chronic_slr"] = {k: {"buildings": int(res[f"slr_{k}ft_chronic"].sum()),
                            "value_million": round(float(res.loc[res[f"slr_{k}ft_chronic"] == 1, "val_struct"].sum()) / 1e6),
                            "residents": round(float(res.loc[res[f"slr_{k}ft_chronic"] == 1, "residents_night"].sum()))}
                        for k in [1, 2, 3, 6]}
    S["fema_depth_buildings"] = {"wet_1pct": int(res.wet_fema1.sum()),
                                 "zone_A_no_bfe": int(b.fema_zone.eq("A").sum()),
                                 "shaded_x_no_elevation": int(b.fema_zone_subtype.eq("0.2 PCT ANNUAL CHANCE FLOOD HAZARD").sum())}

    # ------------------------------------------------------------ tracts
    agg = {c: "sum" for c in res.columns if c.startswith(("ead_", "res_", "dmg_"))}
    agg.update(residents_night="sum", residents_o65="sum", val_struct="sum", val_cont="sum", bid="size")
    t = res.groupby("GEOID_tract").agg(agg).rename(columns={"bid": "buildings"})
    t["residents_wet_fema1"] = res[res.wet_fema1].groupby("GEOID_tract").residents_night.sum()
    t["residents_wet_cat3"] = res[res.wet_cat3].groupby("GEOID_tract").residents_night.sum()
    t["o65_wet_cat3"] = res[res.wet_cat3].groupby("GEOID_tract").residents_o65.sum()
    t["ead_res_mid_slr0"] = res[res.residential].groupby("GEOID_tract").ead_mid_slr0.sum()
    t = t.fillna({"residents_wet_fema1": 0, "residents_wet_cat3": 0, "o65_wet_cat3": 0, "ead_res_mid_slr0": 0})
    obs, weights = observed_claims()
    units = occupied_units()
    inv = pd.read_csv(paths.INVESTMENT_DIR / "tract_investment.csv", dtype={"GEOID": str}).set_index("GEOID")
    t = t.join(obs, how="left").join(units.rename("occupied_units_acs"), how="left")
    t = t.join(inv[["population", "investment_total", "investment_per_capita"]], how="left")
    t[obs.columns] = t[obs.columns].fillna(0)
    t["ead_per_unit"] = t.ead_mid_slr0 / t.occupied_units_acs
    t["ead_res_per_unit"] = t.ead_res_mid_slr0 / t.occupied_units_acs
    t["claims_per_unit"] = t.claims_weighted_annual_nominal / t.occupied_units_acs
    t["ead_per_resident"] = t.ead_mid_slr0 / t.residents_night.replace(0, np.nan)
    t["rank_dollars"] = t.ead_mid_slr0.rank(ascending=False, method="min").astype(int)
    t["rank_people"] = t.res_exposed_annual_slr0.rank(ascending=False, method="min").astype(int)
    t.index.name = "GEOID_tract"
    t.reset_index().to_csv(paths.EAD_TRACT_CSV, index=False)
    S["claim_weights"] = weights
    S["tracts"] = len(t)
    S["tracts_without_units"] = int((t.occupied_units_acs.fillna(0) <= 0).sum())
    S["tracts_with_claims_in_table_not_in_buildings"] = sorted(set(obs.index) - set(t.index))

    # ------------------------------------------------------------ provisional calibration (D-140)
    ok = t[(t.occupied_units_acs >= 50)]
    cal = {"tracts_used": len(ok), "rule": "tracts with at least 50 occupied housing units (ACS 2020-2024)"}
    for name, m, o in [("all_buildings", "ead_per_unit", "claims_per_unit"),
                       ("residential_only", "ead_res_per_unit", "claims_per_unit")]:
        r = spearmanr(ok[m], ok[o]).statistic
        cal[name] = {"spearman": round(float(r), 3), "spearman_95ci": boot_spearman(ok[m], ok[o])}
    for name, oc in [("weighted", "claims_weighted_annual_nominal"), ("all_years_equal", "claims_annual_nominal_all_years"),
                     ("2000_2025", "claims_annual_nominal_2000_2025")]:
        cal[f"spearman_totals_{name}"] = round(float(spearmanr(ok.ead_mid_slr0, ok[oc]).statistic), 3)
        cal[f"ratio_totals_model_to_claims_{name}"] = round(float(ok.ead_mid_slr0.sum() / ok[oc].sum()), 2)
        cal[f"ratio_totals_residential_model_to_claims_{name}"] = round(float(ok.ead_res_mid_slr0.sum() / ok[oc].sum()), 2)
    cal["ratio_totals_low_high_weighted"] = [round(float(ok.ead_low_slr0.sum() / ok.claims_weighted_annual_nominal.sum()), 2),
                                             round(float(ok.ead_high_slr0.sum() / ok.claims_weighted_annual_nominal.sum()), 2)]
    cal["surge_only_spearman"] = round(float(spearmanr(ok.ead_surge_only_slr0 / ok.occupied_units_acs, ok.claims_per_unit).statistic), 3)
    cal["fema_only_spearman"] = round(float(spearmanr(ok.ead_fema_only_slr0 / ok.occupied_units_acs, ok.claims_per_unit).statistic), 3)
    cal["claims_weighted_annual_county_million"] = round(float(t.claims_weighted_annual_nominal.sum()) / 1e6, 1)
    cal["tracts_zero_claims"] = int((ok.claims_weighted_annual_nominal == 0).sum())
    cal["tracts_zero_ead"] = int((ok.ead_mid_slr0 == 0).sum())
    # agreement by decile of modelled risk
    ok = ok.assign(decile=pd.qcut(ok.ead_per_unit.rank(method="first"), 10, labels=False) + 1)
    dec = ok.groupby("decile").agg(tracts=("ead_per_unit", "size"), ead_per_unit=("ead_per_unit", "median"),
                                   claims_per_unit=("claims_per_unit", "median"),
                                   claims_per_unit_mean=("claims_per_unit", "mean"))
    dec.round(2).to_csv(OUT / "calibration_deciles.csv")
    S["calibration"] = cal

    # ------------------------------------------------------------ investment comparison
    iv = t[(t.residents_night >= 100) & t.investment_per_capita.notna()]
    S["investment_vs_risk"] = {
        "tracts": len(iv),
        "spearman_ead_per_resident_vs_investment_per_resident": round(float(spearmanr(iv.ead_per_resident, iv.investment_per_capita).statistic), 3),
        "spearman_ead_total_vs_investment_total": round(float(spearmanr(iv.ead_mid_slr0, iv.investment_total).statistic), 3)}
    hi_risk = iv.ead_per_resident >= iv.ead_per_resident.quantile(0.75)
    lo_inv = iv.investment_per_capita <= iv.investment_per_capita.median()
    S["investment_vs_risk"]["top_quarter_risk_tracts"] = int(hi_risk.sum())
    S["investment_vs_risk"]["of_which_below_median_investment"] = int((hi_risk & lo_inv).sum())
    gap = iv[hi_risk & lo_inv].sort_values("ead_mid_slr0", ascending=False)
    gap[["ead_mid_slr0", "ead_per_resident", "investment_per_capita", "residents_night", "res_exposed_annual_slr0"]].to_csv(OUT / "high_risk_low_investment_tracts.csv")
    t.sort_values("rank_dollars").head(20)[["ead_low_slr0", "ead_mid_slr0", "ead_high_slr0", "ead_per_resident", "res_exposed_annual_slr0",
                                            "residents_wet_cat3", "claims_weighted_annual_nominal", "investment_per_capita"]].to_csv(OUT / "top20_tracts_dollars.csv")
    t.sort_values("rank_people").head(20)[["res_exposed_annual_slr0", "res_displaced_annual_slr0", "residents_wet_fema1", "residents_wet_cat3",
                                           "o65_wet_cat3", "ead_mid_slr0", "investment_per_capita"]].to_csv(OUT / "top20_tracts_people.csv")
    # concentration
    s = res.ead_mid_slr0.sort_values(ascending=False).cumsum() / res.ead_mid_slr0.sum()
    S["share_of_ead_in_top_1pct_buildings"] = round(float(s.iloc[int(0.01 * n)]), 3)
    S["share_of_ead_in_top_10pct_tracts"] = round(float(t.ead_mid_slr0.sort_values(ascending=False).head(len(t) // 10).sum() / t.ead_mid_slr0.sum()), 3)
    S["ead_by_damcat_million"] = (res.groupby(b.st_damcat).ead_mid_slr0.sum() / 1e6).round(1).to_dict()
    S["ead_by_fema_zone_million"] = (res.groupby(b.fema_zone.fillna("none")).ead_mid_slr0.sum() / 1e6).round(1).to_dict()
    (OUT / "summary.json").write_text(json.dumps(S, indent=2, default=str))
    print(json.dumps(S, indent=1, default=str))


if __name__ == "__main__":
    main()
