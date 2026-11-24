"""Module D, step 3: store coefficients on every building, value change and tax change (spec D4, D5, D7; D-182).

    /Users/.../Climate-Resilience---Miami-Dade/.venv/bin/python -I scripts/benefit/module_d_value_tax.py

D4. Coefficients on every building: the MGWR local flood coefficient and its
    standard error are carried from the 5,000 calibration sales to every
    single-family and condo building with the same bisquare kernel and the
    flood variable's own bandwidth (spec route 2). Single-family buildings:
    parcels whose main tax roll use is 001; condo buildings: 004. Other
    buildings get no coefficient (value change "not estimated").
D5. value_change = value x (exp(beta_flood x delta_EYD) - 1), with delta_EYD
    in $1,000s per property, beta in log price per $1,000; low and high with
    beta - 2 SE and beta + 2 SE (whichever gives the smaller / larger change).
    value = 2026 just value allocated to the building (tax roll, Stage 1).
    Condos: the building's damage change is split equally across its units,
    and each unit's change applies to its share of the building value.
D7. Tax revenue: assessed value follows Florida's caps over 10 years.
    Homesteads: Save Our Homes, the lower of 3% or CPI (2.9%, BLS CPI-U 2025)
    on all levies. Non-homestead: 10% cap on non-school levies; school levies
    on just value. Exemptions stay at their 2026 dollar amounts. Taxable
    value times the 2026 millage of the parcel's taxing district (school part
    on school taxable value). Market values grow 3% a year in both the
    baseline and the project case (assumption). Year 1 and year 10 change
    reported. No sale during the 10 years (a sale resets the cap; this
    understates the gain).
Test scenarios: the Module C examples (seawall 8 ft, North Miami; elevation
3 ft, Princeton), with the main (anchored) and the frequent-storm coefficients.
Update (D-184, D-187): the main model's flood variable is the damage rate
($100 a year per $100,000 of building value). delta = change in the
building's yearly damage / its NSI structure value x 1,000 (same unit); no
unit split for condos (the rate is the same for every unit). Variants:
main (rate), frequent (rate, storms 10% to 2%), dollar (the specification's
variable, for comparison); fe: one coefficient per segment from the block
group fixed-effects model (D-191); published_miami, published_meta,
published_slr: scenarios with a fixed coefficient from a published price
discount (D-187), labelled as assumptions, not estimates.
MODULE_D_RUN=n10000 reads the 10,000-sale MGWR runs (D-189); large holds the
full single-family main model.
Writes data/processed/benefit/module_d_coefficients.parquet and
outputs/benefit/module_d/value_tax_examples.json.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
from module_d_fit import smooth_to  # noqa: E402
from progress import Progress  # noqa: E402

import os
OUT = paths.OUT_BENEFIT / "module_d"
RUN = OUT / os.environ.get("MODULE_D_RUN", "")
VARIANTS = ("main", "frequent", "dollar")
SOURCES = {}
P = None   # progress reporting (D-192), set in main()
SEGS = {"001": "single_family", "004": "condo"}
YEARS = 10
GROWTH = 0.03
SOH = 0.029            # lower of 3% and CPI-U 2025 change (BLS, D-144)
NONHOMESTEAD_CAP = 0.10


def store_coefficients(variants=VARIANTS):
    b = pd.read_parquet(paths.BUILDINGS_PARQUET, columns=["fd_id", "lon", "lat", "dor_uc_mode", "jv_alloc", "condo_units",
                                                          "buildings_on_parcel", "parcel_geo_id", "val_struct"])
    b["segment"] = b.dor_uc_mode.astype(str).str.zfill(3).map(SEGS)
    x, y = Transformer.from_crs(4326, 32617, always_xy=True).transform(b.lon.to_numpy(), b.lat.to_numpy())
    out = b[["fd_id", "segment", "jv_alloc", "parcel_geo_id", "val_struct"]].copy()
    out["units"] = np.where(b.segment.eq("condo"),
                            np.maximum(1, np.round(b.condo_units.fillna(0) / b.buildings_on_parcel.clip(lower=1))), 1)
    for v in variants:
        out[f"beta_{v}"] = np.nan
        out[f"se_{v}"] = np.nan
        for seg in ["single_family", "condo"]:
            # full-size run first; the dollar comparison is kept at 5,000 sales (D-188)
            src = next((r for r in (RUN, OUT / "n10000", OUT / "n5000") if (r / f"{seg}_{v}_local.parquet").exists()), None)
            if src is None:
                continue
            SOURCES[f"{seg}_{v}"] = str(src.relative_to(OUT)) or "."
            loc = pd.read_parquet(src / f"{seg}_{v}_local.parquet")
            bw = json.loads((src / f"{seg}_{v}.json").read_text())["mgwr"]["bandwidths"]["FLOOD"]
            m = (out.segment == seg).to_numpy()
            P.log(f"carrying {seg} {v} coefficients (flood bandwidth {bw:.0f}) to {m.sum()} buildings")
            est = smooth_to(loc[["x", "y"]].to_numpy(), loc[["b_FLOOD", "se_FLOOD"]].to_numpy(), [bw, bw],
                            np.c_[x[m], y[m]], progress=P)
            out.loc[m, f"beta_{v}"] = est[:, 0]
            out.loc[m, f"se_{v}"] = est[:, 1]
    for v, (b_, se_) in fixed_coefficients().items():
        out[f"beta_{v}"], out[f"se_{v}"] = out.segment.map(b_), out.segment.map(se_)
    out.to_parquet(paths.MODULE_D_COEF_PARQUET, index=False)
    return out


PUBLISHED = {
    "miami": {"discount": 0.03, "source": "Fu and Nijman (2021), The Professional Geographer 73(1), doi 10.1080/00330124.2020.1818586: "
              "spatial hedonic model of 58,264 Miami-Dade single-family sales within 5,000 ft of the coast, 2004 to 2019; "
              "location in the FEMA 100-year floodplain carries about a 3% discount (coefficient -0.03, p < 0.001)"},
    "meta": {"discount": 0.046, "source": "Beltran, Maddison and Elliott (2018), Ecological Economics 146: 668-685: meta-analysis "
             "of 37 studies (364 estimates); 4.6% discount for the 100-year floodplain (inland flooding), their suggested rule "
             "of thumb for flood relief benefits"},
    "slr": {"discount": 0.07, "source": "Bernstein, Gustafson and Lewis (2019), Journal of Financial Economics 134(2): 253-272: "
            "US coastal homes exposed to sea level rise sell about 7% below comparable unexposed homes the same distance "
            "from the beach (Florida included; exposure to sea level rise, not the FEMA zone)"}}
FE_JSON = OUT / "fe_block_group.json"


def published_coefficients():
    """Fixed coefficient per segment (D-187, assumption): the published discount is applied to the difference in mean
    damage rate between buildings inside and outside the FEMA 2027 1% zone in our data, so beta = ln(1 - d) / gap."""
    b = pd.read_parquet(paths.BUILDINGS_PARQUET, columns=["fd_id", "dor_uc_mode", "val_struct"])
    B = pd.read_parquet(paths.MODULE_B_PARQUET, columns=["fd_id", "eyd_mid", "eyd_tail_mid"]).set_index("fd_id")
    z = pd.read_parquet(paths.FEMA2027_ZONES_PARQUET, columns=["fd_id", "zone27"]).set_index("fd_id").zone27
    b["seg"] = b.dor_uc_mode.astype(str).str.zfill(3).map(SEGS)
    b["rate"] = (B.eyd_mid + B.eyd_tail_mid).reindex(b.fd_id).to_numpy() / b.val_struct.where(b.val_struct > 0) * 1000
    b["sfha"] = b.fd_id.map(z).fillna("X").astype(str).str.match(r"^(A|V)").to_numpy()
    out = {}
    for seg, g in b.dropna(subset=["seg", "rate"]).groupby("seg"):
        gap = g.loc[g.sfha, "rate"].mean() - g.loc[~g.sfha, "rate"].mean()
        out[seg] = {"rate_gap": float(gap), "inside_mean": float(g.loc[g.sfha, "rate"].mean()),
                    "outside_mean": float(g.loc[~g.sfha, "rate"].mean()),
                    **{f"beta_{k}": float(np.log(1 - p["discount"]) / gap) for k, p in PUBLISHED.items()}}
    return out


def fixed_coefficients():
    """One coefficient per segment: block group fixed effects (D-191; standard error from its 95% range) and the
    published scenarios (D-187; assumptions, no standard error)."""
    out = {}
    fe = json.loads(FE_JSON.read_text())
    b, se = {}, {}
    for seg in ("single_family", "condo"):
        c = fe[seg]["main"]["cluster_block_group"]
        b[seg] = float(np.log1p(c["pct_per_unit"] / 100))
        se[seg] = float((np.log1p(c["ci95"][1] / 100) - np.log1p(c["ci95"][0] / 100)) / 3.92)
    out["fe"] = (b, se)
    pub = published_coefficients()
    for k in PUBLISHED:
        out[f"published_{k}"] = ({seg: v[f"beta_{k}"] for seg, v in pub.items()}, {seg: 0.0 for seg in pub})
    return out


FIXED = ("fe",) + tuple(f"published_{k}" for k in PUBLISHED)


def value_change(per, C, v):
    """per: Module C per-building table (fd_id, before/after EYD). Returns per-building value change (mid, low, high)."""
    d = per.merge(C, on="fd_id", how="left")
    dfreq = d.eyd_freq_after - d.eyd_freq_before
    dall = (d.eyd_mid_after + d.eyd_tail_after) - (d.eyd_mid_before + d.eyd_tail_before)
    vs = d.val_struct.where(d.val_struct > 0)
    if v == "dollar":        # the specification's variable: $1,000s per property
        dE = dall / 1000.0 / d.units
    elif v == "frequent":    # damage rate, storms 10% to 2%
        dE = dfreq / vs * 1000
    else:                    # main, fixed effects and published: damage rate, $100 a year per $100,000 of building value
        dE = dall / vs * 1000
    beta, se = d[f"beta_{v}"], d[f"se_{v}"]
    V = d.jv_alloc.fillna(0)
    ch = lambda bb: V * (np.exp(bb * dE) - 1)
    a, b2 = ch(beta - 2 * se), ch(beta + 2 * se)
    d["dEYD_k_per_property"] = dE
    d["value_change_mid"] = ch(beta)
    d["value_change_low"] = np.fmin(a, b2)
    d["value_change_high"] = np.fmax(a, b2)
    return d


_NAL = None   # tax roll joined to parcels, read once per run


def tax_roll():
    global _NAL
    if _NAL is None:
        nal = pd.read_csv(paths.DOR_DIR / "extract" / "NAL23F202601.csv",
                          usecols=["PARCEL_ID", "JV", "JV_HMSTD", "AV_SD", "AV_NSD", "TV_SD", "TV_NSD", "TAX_AUTH_CD"],
                          dtype={"PARCEL_ID": str})
        m = pd.read_csv(paths.OUT_BENEFIT / "stage1" / "nal_to_parcel.csv.gz", dtype=str)[["PARCEL_ID", "parcel_geo_id"]]
        _NAL = nal.merge(m, on="PARCEL_ID")
    return _NAL


def tax_change(d):
    """Year 1 and year 10 tax revenue change for the parcels of the buildings in d (value change mid)."""
    nal = tax_roll()
    nal = nal[nal.parcel_geo_id.isin(set(d.parcel_geo_id.dropna()))].copy()
    # each building's value change goes to the tax roll records on its parcel, by just value share
    bchg = d.groupby("parcel_geo_id").value_change_mid.sum()
    nal["dV"] = nal.parcel_geo_id.map(bchg).fillna(0) * nal.JV / nal.groupby("parcel_geo_id").JV.transform("sum").replace(0, np.nan)
    nal["dV"] = nal.dV.fillna(0)
    mill = pd.read_csv(paths.MILLAGE_2026_CSV, dtype={"code": str}).set_index("code")
    code = nal.TAX_AUTH_CD.astype(str).str.zfill(4)
    ms, mn = code.map(mill.school_total).fillna(0).to_numpy() / 1000, code.map(mill.nonschool_total).fillna(0).to_numpy() / 1000
    hm = (nal.JV_HMSTD.fillna(0) > 0).to_numpy()
    Es, En = (nal.AV_SD - nal.TV_SD).clip(lower=0).to_numpy(), (nal.AV_NSD - nal.TV_NSD).clip(lower=0).to_numpy()

    def path(dV):
        jv = nal.JV.to_numpy(float) + dV
        avs, avn = nal.AV_SD.to_numpy(float), nal.AV_NSD.to_numpy(float)
        taxes = []
        for t in range(1, YEARS + 1):
            jv = jv * (1 + GROWTH) if t > 1 else jv
            avs = np.where(hm, np.minimum(jv, avs * (1 + SOH)), jv)
            avn = np.where(hm, np.minimum(jv, avn * (1 + SOH)), np.minimum(jv, avn * (1 + NONHOMESTEAD_CAP)))
            taxes.append(ms * np.clip(avs - Es, 0, None) + mn * np.clip(avn - En, 0, None))
        return np.array(taxes)

    base, proj = path(np.zeros(len(nal))), path(nal.dV.to_numpy())
    diff = proj - base
    return {"tax_records": int(len(nal)), "homestead_share": round(float(hm.mean()), 3),
            "value_change_on_roll_million": round(float(nal.dV.sum()) / 1e6, 2),
            "tax_change_year1": round(float(diff[0].sum())), "tax_change_year10": round(float(diff[-1].sum())),
            "tax_change_year1_homestead": round(float(diff[0][hm].sum())), "tax_change_year10_homestead": round(float(diff[-1][hm].sum()))}


def main():
    global P
    import module_c_projects as mc
    P = Progress("module D value and tax")
    C = store_coefficients()
    R = {"run": os.environ.get("MODULE_D_RUN", "5000"), "published": {"sources": PUBLISHED, "by_segment": published_coefficients()},
         "coefficients": {}, "model_runs": SOURCES}
    for v in VARIANTS + FIXED:
        for seg in ("single_family", "condo"):
            s = C[(C.segment == seg)][f"beta_{v}"]
            if s.notna().any():
                R["coefficients"][f"{seg}_{v}"] = {"buildings": int(s.notna().sum()),
                                                   "unit": "per $1,000 per property" if v == "dollar" else "per $100 per $100,000",
                                                   "pct_per_unit_median": round(float((np.exp(s.median()) - 1) * 100), 2),
                                                   "pct_per_unit_p10_p90": [round(float((np.exp(s.quantile(.1)) - 1) * 100), 2),
                                                                            round(float((np.exp(s.quantile(.9)) - 1) * 100), 2)],
                                                   "share_negative": round(float((s < 0).mean()), 3)}
    P.start("test projects: value and tax")
    M = mc.Model()
    ex1, ex2 = mc.pick_examples(M)
    scen = {"seawall_8ft_north_miami": M.seawall(ex1["line"], 8.0), "elevate_3ft_princeton": M.elevate(ex2["fd_ids"], 3.0)}
    for name, (r, per) in scen.items():
        R[name] = {"losses_avoided_mid": round(r["losses_avoided_per_year"]["mid"])}
        for v in VARIANTS + FIXED:
            d = value_change(per, C, v)
            est = d[d[f"beta_{v}"].notna() & d.val_struct.gt(0)]
            R[name][v] = {"buildings_with_coefficient": int(len(est)), "buildings_without": int(len(d) - len(est)),
                          "value_change_million": {k: round(float(est[f"value_change_{k}"].sum()) / 1e6, 2) for k in ("low", "mid", "high")},
                          "value_change_by_segment_million": est.groupby("segment").value_change_mid.sum().div(1e6).round(2).to_dict(),
                          "median_pct_change": round(float((est.value_change_mid / est.jv_alloc.replace(0, np.nan)).median() * 100), 2),
                          "tax": tax_change(est) if v in ("main",) + FIXED else None}
        a, b = R[name]["main"]["value_change_million"]["mid"], R[name]["frequent"]["value_change_million"]["mid"]
        R[name]["frequent_vs_main_ratio"] = round(b / a, 2) if a else None
    (OUT / "value_tax_examples.json").write_text(json.dumps(R, indent=2, default=str))
    P.end()
    print(json.dumps(R, indent=1, default=str))
    P.finish()


if __name__ == "__main__":
    main()
