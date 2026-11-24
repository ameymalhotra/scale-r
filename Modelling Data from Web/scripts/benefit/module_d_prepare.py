"""Module D, step 1: the sales samples with the specification's variables (prompt 28 follow-up, D-178, D-179).

    /Users/.../Climate-Resilience---Miami-Dade/.venv/bin/python -I scripts/benefit/module_d_prepare.py

Samples:
- main: 2025 and 2026 qualified sales of improved single-family homes and
  condos (Stage 3, D-149: qualification 01/02, improved, 0.5% price trim);
- older: the county house layer's latest sale where it falls in 2021 to
  2024 (no qualification code; D-169). Non-market rule (D-179), all stated
  in advance and not tuned on the model:
  1. price at least $50,000;
  2. price against the 2026 just value, after moving the just value back to
     the sale year with FHFA's Miami-Dade house price index: kept only
     inside the 2.5th to 97.5th percentile range of the same ratio in the
     main (qualified) sample of that segment;
  3. price per square foot of living area, moved to 2025 with the same
     index: kept only inside the 0.5th to 99.5th percentile range of the
     main sample of that segment;
  4. living area and year built present, and the sale not before the year
     built.
Variables (specification D2): log sale price; flood risk = expected yearly
damage in $1,000s (anchored, D-174; and storms 10% to 2% only, sensitivity);
living area, lot size (single-family), age, bedrooms, bathrooms (full + half
x 0.5), pool proxy (single-family: tax roll special features value above 0,
which also counts docks and fences; no pool field is free, D-165),
waterfront (parcel within 10 m of FEMA water areas or open water), distance
to water (coast, bay, canal or lake), ground elevation (3DEP), time (sale
year + month).
Update (D-184): the main flood variable is now the damage rate, expected
yearly damage per $100,000 of building value (NSI structure value of the
buildings on the parcel), in units of $100 a year per $100,000 (0.1% of
value a year). Dollar damage grows with the home's own value, which made the
dollar coefficient partly a size and quality effect (D-183). For condos the
rate is the same for every unit on the parcel, so no split is needed.
flood_rate (anchored, main) and flood_freq_rate (storms 10% to 2%,
sensitivity) are added; the dollar variables are kept for comparison.
Flood risk per sale: the expected yearly damage of the NSI buildings on the
parcel (nearest building if none). For condos it is split across the units on
the parcel by their share of just value.
Writes data/processed/benefit/module_d_sales.parquet and a summary json.
"""
import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
from scipy.spatial import cKDTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
from module_b_eyd import EVENTS, P  # noqa: E402

UTM = 32617
NAL_CSV = paths.DOR_DIR / "extract" / "NAL23F202601.csv"
PARCEL_SHP = paths.DOR_DIR / "extract" / "miamidade_2026Ppar.shp"
SEG = {"001": "single_family", "004": "condo"}
MIN_PRICE = 50_000
RATIO_Q = (0.025, 0.975)
PPSF_Q = (0.005, 0.995)
WATERFRONT_M = 10.0
LOG = {}


def county_hpi():
    h = pd.read_csv(paths.FHFA_DIR / "hpi_at_tract_miami_dade.csv")
    h["annual_change"] = pd.to_numeric(h.annual_change, errors="coerce")
    ch = h.groupby("year").annual_change.median().fillna(0) / 100
    idx = (1 + ch).cumprod()
    return idx / idx.loc[2025]          # 2025 = 1; the 2026 roll's just value is a 1 Jan 2026 value


def building_risk():
    """Expected yearly damage per parcel (anchored, and frequent storms only) and ground elevation."""
    A = pd.read_parquet(paths.MODULE_A_PARQUET, columns=["fd_id", "lon", "lat", "ground_elev_ft_navd88"])
    B = pd.read_parquet(paths.MODULE_B_PARQUET, columns=["fd_id", "eyd_mid", "eyd_tail_mid"] +
                        [f"loss_{e}_mid" for e in EVENTS])
    L = np.maximum.accumulate(B[[f"loss_{e}_mid" for e in EVENTS]].to_numpy(), axis=1)
    freq = (0.5 * (L[:, :-1] + L[:, 1:]) * (P[:-1] - P[1:]))[:, :2].sum(1)
    pg = pd.read_parquet(paths.BUILDINGS_PARQUET, columns=["fd_id", "parcel_geo_id", "val_struct"]).set_index("fd_id").reindex(A.fd_id)
    b = pd.DataFrame({"fd_id": A.fd_id, "lon": A.lon, "lat": A.lat, "ground": A.ground_elev_ft_navd88,
                      "eyd": (B.eyd_mid + B.eyd_tail_mid).to_numpy(), "eyd_freq": freq,
                      "parcel_geo_id": pg.parcel_geo_id.to_numpy(), "val_struct": pg.val_struct.to_numpy()})
    return b


def locate(s, b):
    m = pd.read_csv(paths.OUT_BENEFIT / "stage1" / "nal_to_parcel.csv.gz", dtype=str)
    s = s.merge(m[["PARCEL_ID", "parcel_geo_id"]], on="PARCEL_ID", how="left")
    LOG[f"not_placed_{s.sample_name.iloc[0]}"] = int(s.parcel_geo_id.isna().sum())
    s = s[s.parcel_geo_id.notna()].copy()
    par = pyogrio.read_dataframe(PARCEL_SHP, columns=["PARCEL_ID"])
    par = par[par.PARCEL_ID.isin(set(s.parcel_geo_id))].drop_duplicates("PARCEL_ID").to_crs(UTM).set_index("PARCEL_ID")
    s = s[s.parcel_geo_id.isin(par.index)].copy()
    pt = par.geometry.representative_point().loc[s.parcel_geo_id]
    s["x"], s["y"] = pt.x.to_numpy(), pt.y.to_numpy()
    # waterfront and distance to water: FEMA 2027 water areas and open-water zone
    w = pyogrio.read_dataframe(paths.FIRM_2027_EXTRACT / "S_Wtr_Ar.shp")[["geometry"]].to_crs(UTM)
    ow = pyogrio.read_dataframe(paths.FIRM_2027_EXTRACT / "S_Fld_Haz_Ar.shp", where="FLD_ZONE = 'OPEN WATER'")[["geometry"]].to_crs(UTM)
    water = pd.concat([w, ow], ignore_index=True)
    tree = water.sindex
    polys = par.geometry.loc[s.parcel_geo_id].reset_index(drop=True)
    i_poly, i_w = tree.query(polys.buffer(WATERFRONT_M).values, predicate="intersects")
    wf = np.zeros(len(s), bool)
    wf[np.unique(i_poly)] = True
    s["waterfront"] = wf.astype(int)
    pts = gpd.GeoSeries(gpd.points_from_xy(s.x, s.y), crs=UTM)
    near_i, dist = tree.nearest(pts.values, return_distance=True)
    d = np.full(len(s), np.nan)
    d[near_i[0]] = dist
    s["dist_water_m"] = d
    ll = pts.to_crs(4326)
    s["lon"], s["lat"] = ll.x.to_numpy(), ll.y.to_numpy()
    return s.reset_index(drop=True)


def attach_risk(s, b, nal):
    g = b.dropna(subset=["parcel_geo_id"]).groupby("parcel_geo_id").agg(
        eyd=("eyd", "sum"), eyd_freq=("eyd_freq", "sum"), ground=("ground", "median"), n_bldg=("fd_id", "size"),
        val_struct=("val_struct", "sum"))
    s = s.merge(g, left_on="parcel_geo_id", right_index=True, how="left")
    miss = s.eyd.isna().to_numpy()
    LOG[f"no_building_on_parcel_{s.sample_name.iloc[0]}"] = int(miss.sum())
    if miss.any():
        from pyproj import Transformer
        bx, by = Transformer.from_crs(4326, UTM, always_xy=True).transform(b.lon.to_numpy(), b.lat.to_numpy())
        _, i = cKDTree(np.c_[bx, by]).query(s.loc[miss, ["x", "y"]].to_numpy())
        for c, src in [("eyd", "eyd"), ("eyd_freq", "eyd_freq"), ("ground", "ground"), ("val_struct", "val_struct")]:
            s.loc[miss, c] = b[src].to_numpy()[i]
        s.loc[miss, "n_bldg"] = 1
    # condo units share the parcel's damage by just value
    tot = nal.groupby("parcel_geo_id").JV.sum()
    share = np.where(s.segment.eq("condo"), s.JV / s.parcel_geo_id.map(tot).replace(0, np.nan), 1.0)
    share = np.nan_to_num(share, nan=1.0)
    s["flood_k"] = s.eyd * share / 1000.0
    s["flood_freq_k"] = s.eyd_freq * share / 1000.0
    # damage rate: $100s a year per $100,000 of building value (D-184)
    v = s.val_struct.where(s.val_struct > 0)
    s["flood_rate"] = s.eyd / v * 1e5 / 100.0
    s["flood_freq_rate"] = s.eyd_freq / v * 1e5 / 100.0
    LOG[f"no_building_value_{s.sample_name.iloc[0]}"] = int(v.isna().sum())
    return s


def main():
    hpi = county_hpi()
    nal = pd.read_csv(NAL_CSV, usecols=["PARCEL_ID", "DOR_UC", "JV", "LND_SQFOOT", "ACT_YR_BLT", "TOT_LVG_AREA",
                                        "SPEC_FEAT_VAL", "TAX_AUTH_CD"], dtype={"PARCEL_ID": str, "DOR_UC": str})
    nal["DOR_UC"] = nal.DOR_UC.str.zfill(3)
    m = pd.read_csv(paths.OUT_BENEFIT / "stage1" / "nal_to_parcel.csv.gz", dtype=str)
    nal = nal.merge(m[["PARCEL_ID", "parcel_geo_id"]], on="PARCEL_ID", how="left")
    pa = pd.read_parquet(paths.PA_FEATURES_PARQUET)
    pa["bathrooms"] = pa.bathrooms_full.fillna(0) + 0.5 * pa.bathrooms_half.fillna(0)

    # main sample (Stage 3 qualified 2025-2026 sales)
    s3 = pd.read_parquet(paths.SALES_FEATURES_PARQUET, columns=["PARCEL_ID", "segment", "sale_price", "sale_year",
                                                                "sale_month", "JV", "LND_SQFOOT", "ACT_YR_BLT",
                                                                "TOT_LVG_AREA", "TAX_AUTH_CD", "fold_spatial"])
    main_s = s3.assign(sample_name="main", qual_cd=1)
    # older sample: house layer's latest sale in 2021-2024
    o = pa[pa.sale_date.dt.year.between(2021, 2024)].copy()
    o = o.merge(nal, left_on="parcel_id", right_on="PARCEL_ID", how="inner")
    o = o[o.DOR_UC.isin(SEG)].copy()
    o["segment"] = o.DOR_UC.map(SEG)
    o["sale_year"], o["sale_month"] = o.sale_date.dt.year, o.sale_date.dt.month
    o["TOT_LVG_AREA"] = o.living_area_sqft.where(o.living_area_sqft > 0, o.TOT_LVG_AREA)
    n0 = o.groupby("segment").size().to_dict()
    # non-market rule (D-179)
    ref = main_s.copy()
    ref["ratio"] = ref.sale_price / ref.JV
    ref["ppsf25"] = ref.sale_price / ref.TOT_LVG_AREA / ref.sale_year.map(hpi).fillna(1.0)
    o["jv_at_sale"] = o.JV * o.sale_year.map(hpi)
    o["ratio"] = o.sale_price / o.jv_at_sale
    o["ppsf25"] = o.sale_price / o.TOT_LVG_AREA / o.sale_year.map(hpi)
    keep = []
    rule_log = {}
    for seg, g in o.groupby("segment"):
        r = ref[ref.segment == seg]
        lo, hi = r.ratio.quantile(list(RATIO_Q))
        plo, phi = r.ppsf25.quantile(list(PPSF_Q))
        c1 = g.sale_price >= MIN_PRICE
        c2 = g.ratio.between(lo, hi)
        c3 = g.ppsf25.between(plo, phi)
        c4 = (g.TOT_LVG_AREA > 0) & g.ACT_YR_BLT.between(1800, 2026) & (g.sale_year >= g.ACT_YR_BLT)
        rule_log[seg] = {"start": int(len(g)), "price_below_50k": int((~c1).sum()),
                         "ratio_band": [round(float(lo), 3), round(float(hi), 3)],
                         "outside_ratio_band": int((c1 & ~c2).sum()),
                         "ppsf_band_2025_dollars": [round(float(plo)), round(float(phi))],
                         "outside_ppsf_band": int((c1 & c2 & ~c3).sum()),
                         "missing_area_or_year": int((c1 & c2 & c3 & ~c4).sum()),
                         "kept": int((c1 & c2 & c3 & c4).sum())}
        keep.append(g[c1 & c2 & c3 & c4])
    older = pd.concat(keep).assign(sample_name="older", qual_cd=np.nan, fold_spatial=np.nan)
    LOG["older_rule"] = rule_log
    LOG["older_start_by_segment"] = n0

    cols = ["PARCEL_ID", "segment", "sale_price", "sale_year", "sale_month", "JV", "LND_SQFOOT", "ACT_YR_BLT",
            "TOT_LVG_AREA", "TAX_AUTH_CD", "sample_name", "qual_cd", "fold_spatial"]
    b = building_risk()
    out = []
    for s in (main_s[cols], older[cols]):
        s = locate(s.reset_index(drop=True), b)
        s = attach_risk(s, b, nal)
        out.append(s)
    S = pd.concat(out, ignore_index=True)
    S = S.merge(pa[["parcel_id", "bedrooms", "bathrooms"]], left_on="PARCEL_ID", right_on="parcel_id", how="left").drop(columns="parcel_id")
    S = S.merge(nal[["PARCEL_ID", "SPEC_FEAT_VAL"]], on="PARCEL_ID", how="left")
    S["log_price"] = np.log(S.sale_price)
    S["log_living_area"] = np.log(S.TOT_LVG_AREA.clip(lower=200))
    S["log_lot"] = np.log(S.LND_SQFOOT.clip(lower=500))
    S["age"] = (S.sale_year - S.ACT_YR_BLT).clip(lower=0)
    S["pool_proxy"] = np.where(S.segment.eq("single_family"), (S.SPEC_FEAT_VAL.fillna(0) > 0).astype(int), 0)
    S["log_dist_water"] = np.log(S.dist_water_m.clip(lower=10))
    S["ground_elev_ft"] = S.ground
    S["time"] = S.sale_year + (S.sale_month - 0.5) / 12
    S["TAX_AUTH_CD"] = S.TAX_AUTH_CD.astype(str).str.zfill(4)
    for c in ["bedrooms", "bathrooms"]:
        med = S.groupby("segment")[c].transform("median")
        S[f"{c}_missing"] = (S[c].isna() | (S[c] <= 0)).astype(int)
        S[c] = S[c].where(S[c] > 0, med)
    S.to_parquet(paths.MODULE_D_SALES_PARQUET, index=False)
    LOG["sales"] = S.groupby(["sample_name", "segment"]).size().rename("n").reset_index().to_dict("records")
    LOG["flood_k_share_positive"] = {f"{a}|{b}": round(float((g.flood_k > 0).mean()), 3) for (a, b), g in S.groupby(["sample_name", "segment"])}
    LOG["flood_k_median_positive"] = S[S.flood_k > 0].groupby("segment").flood_k.median().round(3).to_dict()
    LOG["flood_rate_share_positive"] = {f"{a}|{b}": round(float((g.flood_rate > 0).mean()), 3) for (a, b), g in S.groupby(["sample_name", "segment"])}
    LOG["flood_rate_quantiles_positive"] = S[S.flood_rate > 0].groupby("segment").flood_rate.quantile([.5, .9, .99]).round(3).unstack().to_dict("index")
    LOG["corr_flood_with_log_living_area"] = {seg: {"dollar": round(float(g[["flood_k", "log_living_area"]].corr().iloc[0, 1]), 3),
                                                    "rate": round(float(g[["flood_rate", "log_living_area"]].corr().iloc[0, 1]), 3)}
                                              for seg, g in S.groupby("segment")}
    LOG["waterfront_share"] = S.groupby("segment").waterfront.mean().round(3).to_dict()
    LOG["bedrooms_missing_share"] = S.groupby("segment").bedrooms_missing.mean().round(3).to_dict()
    (paths.OUT_BENEFIT / "module_d").mkdir(parents=True, exist_ok=True)
    (paths.OUT_BENEFIT / "module_d" / "prepare_log.json").write_text(json.dumps(LOG, indent=2, default=str))
    print(json.dumps(LOG, indent=1, default=str))


if __name__ == "__main__":
    main()
