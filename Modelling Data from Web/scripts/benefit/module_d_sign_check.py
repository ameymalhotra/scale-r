"""Why the flood coefficient is positive: OLS checks (spec D3 and limitation "waterfront appeal can mask
the flood discount"; D-183).

    /Users/.../Climate-Resilience---Miami-Dade/.venv/bin/python -I scripts/benefit/module_d_sign_check.py

Main-sample training sales (same hold-out as module_d_fit.py). For each segment, the flood coefficient
(% per $1,000 of expected yearly damage, standard errors clustered by tract) under:
  A. the specification's variables (as module_d_fit.py);
  B. A + tract fixed effects (compare homes in the same tract);
  C. A + block group fixed effects;
  D. A without the 0.2%-storm tail in the flood variable (frequent storms only);
  E. A, homes more than 1 km from open water only;
  F. A, sales inside the FEMA 1% zone only.
Writes outputs/benefit/module_d/sign_check.json.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
from module_d_fit import XV, load  # noqa: E402


def fit(d, xs, fe=None):
    X = d[xs].astype(float)
    if fe is not None:
        X = pd.concat([X, pd.get_dummies(d[fe], prefix="fe", drop_first=True, dtype=float)], axis=1)
    X = sm.add_constant(X)
    m = sm.OLS(d.log_price.to_numpy(), X).fit(cov_type="cluster", cov_kwds={"groups": pd.factorize(d.GEOID_tract)[0]})
    b, se = m.params["FLOOD"], m.bse["FLOOD"]
    return {"n": int(len(d)), "pct_per_1000": round(float((np.exp(b) - 1) * 100), 2), "t": round(float(b / se), 2),
            "ci95": [round(float((np.exp(b - 1.96 * se) - 1) * 100), 2), round(float((np.exp(b + 1.96 * se) - 1) * 100), 2)]}


def main():
    zones = pd.read_parquet(paths.FEMA2027_ZONES_PARQUET, columns=["fd_id", "zone27"])
    R = {}
    for seg in ["single_family", "condo"]:
        s = load(seg)
        t = s[(s.sample_name == "main") & ~s.holdout].copy()
        xs = XV[seg]
        t["GEOID_bg"] = t.GEOID_tract + "x"   # placeholder replaced below
        import geopandas as gpd
        bg = gpd.read_file(f"zip://{paths.BOUNDARY_DIR / 'tl_2024_12_bg.zip'}")
        bg = bg[bg.COUNTYFP == "086"].to_crs(32617)[["GEOID", "geometry"]]
        j = gpd.sjoin(gpd.GeoDataFrame(geometry=gpd.points_from_xy(t.x, t.y), crs=32617, index=t.index), bg,
                      predicate="within", how="left")
        t["GEOID_bg"] = j[~j.index.duplicated()].GEOID
        t["FLOOD"] = t.flood_k
        t = t.dropna(subset=xs + ["log_price"])
        r = {"A_spec": fit(t, xs), "B_tract_fe": fit(t, xs, "GEOID_tract"), "C_block_group_fe": fit(t, xs, "GEOID_bg")}
        t2 = t.copy()
        t2["FLOOD"] = t2.flood_freq_k
        r["D_frequent_storms"] = fit(t2, xs)
        r["E_over_1km_from_water"] = fit(t[t.dist_water_m > 1000], xs)
        r["F_in_1pct_zone"] = fit(t[t.flood_k > 0], xs)
        r["flood_positive_share"] = round(float((t.flood_k > 0).mean()), 3)
        r["corr_flood_waterfront"] = round(float(t[["flood_k", "waterfront"]].corr().iloc[0, 1]), 3)
        r["corr_flood_log_dist_water"] = round(float(t[["flood_k", "log_dist_water"]].corr().iloc[0, 1]), 3)
        R[seg] = r
    (paths.OUT_BENEFIT / "module_d" / "sign_check.json").write_text(json.dumps(R, indent=2))
    print(json.dumps(R, indent=1))


if __name__ == "__main__" and len(sys.argv) == 1:
    main()


def ratio_check():
    """Test: flood risk as expected yearly damage per $100,000 of structure value (damage rate), which removes
    the mechanical link between dollar damage and the home's own value."""
    b = pd.read_parquet(paths.BUILDINGS_PARQUET, columns=["fd_id", "parcel_geo_id", "val_struct"])
    B = pd.read_parquet(paths.MODULE_B_PARQUET, columns=["fd_id", "eyd_mid", "eyd_tail_mid"])
    b["eyd"] = (B.eyd_mid + B.eyd_tail_mid).to_numpy()
    g = b.groupby("parcel_geo_id")[["eyd", "val_struct"]].sum()
    rate = (g.eyd / g.val_struct.replace(0, np.nan) * 1e5 / 100).rename("rate")   # per $100 a year per $100,000
    R = json.loads((paths.OUT_BENEFIT / "module_d" / "sign_check.json").read_text())
    for seg in ["single_family", "condo"]:
        s = load(seg)
        t = s[(s.sample_name == "main") & ~s.holdout].copy()
        t["FLOOD"] = t.parcel_geo_id.map(rate)
        t = t.dropna(subset=XV[seg] + ["log_price"])
        r = fit(t, XV[seg])
        r["unit"] = "% price change per $100 of yearly damage per $100,000 of structure value (0.1% a year)"
        r["fe_tract"] = fit(t, XV[seg], "GEOID_tract")
        r["corr_dollar_eyd_with_log_living_area"] = round(float(np.corrcoef(t.flood_k, t.log_living_area)[0, 1]), 3)
        R[seg]["G_damage_rate"] = r
    (paths.OUT_BENEFIT / "module_d" / "sign_check.json").write_text(json.dumps(R, indent=2))
    print(json.dumps({k: v["G_damage_rate"] for k, v in R.items()}, indent=1))


if __name__ == "__main__" and len(sys.argv) > 1:
    ratio_check()
