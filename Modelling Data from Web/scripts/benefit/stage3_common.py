"""Shared feature definitions for the Stage 3 property value models (prompt 27).

Used by stage3_models.py (OLS, main .venv) and stage3_xgb.py (XGBoost, .venv-ml),
so both use exactly the same features. Needs only numpy and pandas.
"""
import numpy as np

TYPES = ["gray", "green", "blue", "hybrid"]
BG = ["log_income", "median_family_income_imputed", "LOWINCPCT", "PEOPCOLORPCT", "OVER64PCT", "LESSHSPCT",
      "pct_owner_occupied", "UNEMPPCT", "no_vehicle"]
ACCESS = ["log_dist_coast", "log_dist_downtown", "log_dist_rail", "log_dist_major_park", "log_dist_school"]
HAZARD = ["sfha", "ground_elev_ft", "slr_3ft", "slr_6ft", "surge_cat3_ft", "lst_f", "log_tract_claims"]
PROJ_MAIN = [f"near500_{t}" for t in TYPES] + [f"band1k_{t}" for t in TYPES]
PROJ_CHECK = ([f"log_dist_{t}" for t in TYPES] + [f"n500_{t}" for t in TYPES] + [f"log_usd1k_{t}" for t in TYPES])

def features(s):
    s = s.copy()
    s["age2"] = s.age ** 2 / 100
    s["log_income"] = np.log(s.median_family_income.clip(lower=5000))
    for c, src, lo in [("log_dist_coast", "dist_coast_m", 10), ("log_dist_downtown", "dist_downtown_m", 100),
                       ("log_dist_rail", "dist_rail_m", 50), ("log_dist_major_park", "dist_major_park_m", 10),
                       ("log_dist_school", "dist_school_m", 50)]:
        s[c] = np.log(s[src].clip(lower=lo))
    s["log_tract_claims"] = np.log1p(s.tract_claims_per_unit.fillna(0))
    s["lst_f"] = s.lst_f.fillna(s.lst_f.median())
    for t in TYPES:
        d = s[f"dist_{t}_m"]
        s[f"near500_{t}"] = (d < 500).astype(float)
        s[f"band1k_{t}"] = ((d >= 500) & (d < 1000)).astype(float)
        s[f"log_dist_{t}"] = np.log(d.clip(50, 5000))
        s[f"n500_{t}"] = s[f"n_{t}_500m"].astype(float)
        s[f"log_usd1k_{t}"] = np.log1p(s[f"usd_{t}_1000m"] / 1e6)
    return s


def structure_cols(seg):
    return ["log_living_area", "age", "age2"] + (["log_lot"] if seg == "single_family" else [])
