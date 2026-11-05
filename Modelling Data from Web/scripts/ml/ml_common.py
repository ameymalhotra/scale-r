"""Shared setup for the ML scenario module (Stage 2 onward).

Feature lists, the modelling table, folds and model factories. Feature
choices follow DECISIONS.md D-073, D-074 and D-080.
"""
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import paths  # noqa: E402
from analysis_variables import PCA_TRACT_VARS  # noqa: E402
from professor_labels import TRACT_VARS  # noqa: E402

SEED = 12086
STAGE1 = paths.OUT_ML / "stage1"
STAGE2 = paths.OUT_ML / "stage2"
DASH = paths.OUT_ML / "dashboard"

SOCIAL = list(PCA_TRACT_VARS)
HAZ_MAIN = ["slr_3ft_pop_share", "surge_cat3_any_pop_share", "heat_lst_popwt_mean_f"]
HAZ_SENS_EXTRA = ["heat_p95_pop_share", "surge_cat3_over3ft_pop_share", "surge_cat4_any_pop_share"]
HAZ_LAND = ["slr_3ft_land_share", "surge_cat3_any_land_share", "heat_land_mean_f"]
NRI = ["nri_eal_per_person", "nri_ealb_per_building_value"]
CONTEXT = ["pop_density", "dist_coast_km", "in_municipality"]
FLOOD_ZONE_SLOT = []      # FEMA flood zones, pending a file with geometry (D-032)
MAIN = SOCIAL + HAZ_MAIN + NRI + CONTEXT + FLOOD_ZONE_SLOT
SENS = SOCIAL + HAZ_MAIN + HAZ_SENS_EXTRA + NRI + CONTEXT
LAND = SOCIAL + HAZ_LAND + NRI + CONTEXT
# the family each scenario feature belongs to
FAMILY = {"slr_3ft_pop_share": "sea level rise", "surge_cat3_any_pop_share": "storm surge",
          "heat_lst_popwt_mean_f": "surface heat"}

PLAIN = {
    "slr_3ft_pop_share": "residents on land flooded by 3 ft of sea level rise",
    "surge_cat3_any_pop_share": "residents on land reached by Category 3 storm surge",
    "surge_cat4_any_pop_share": "residents on land reached by Category 4 storm surge",
    "surge_cat3_over3ft_pop_share": "residents on land with more than 3 ft of Category 3 surge",
    "heat_lst_popwt_mean_f": "how hot residents' land gets in summer",
    "heat_p95_pop_share": "residents on the hottest land (top 5%)",
    "slr_3ft_land_share": "land flooded by 3 ft of sea level rise",
    "surge_cat3_any_land_share": "land reached by Category 3 storm surge",
    "heat_land_mean_f": "how hot the land gets in summer",
    "nri_eal_per_person": "FEMA expected yearly loss per resident",
    "nri_ealb_per_building_value": "FEMA expected yearly building loss per dollar of buildings",
    "pop_density": "population density",
    "dist_coast_km": "distance from the bay or ocean",
    "in_municipality": "being in a city rather than unincorporated Miami-Dade",
}


def plain(name):
    if name in PLAIN:
        return PLAIN[name]
    if name in TRACT_VARS:
        return TRACT_VARS[name][0].lower()
    if name.startswith("scale_"):
        return f"project scale: {name[6:].lower()}"
    if name.startswith("focus_"):
        return f"hazard focus: {name[6:]}"
    return name


def load_table():
    t = pd.read_csv(STAGE1 / "model_table_tract.csv", dtype={"GEOID": str})
    f = pd.read_csv(STAGE1 / "spatial_fold_assignment.csv", dtype={"GEOID": str})
    t = t.merge(f, on="GEOID", how="left")
    ex = pd.read_csv(paths.EXPOSURE_DIR / "exposure_tract.csv", dtype={"GEOID": str})
    scen_cols = ([f"slr_{k}ft_pop_share" for k in (1, 2, 3, 6)]
                 + [f"surge_cat{c}_any_pop_share" for c in (1, 2, 3, 4)] + ["surge_cat5max_any_pop_share"]
                 + ["slr_3ft_pop_exposed", "surge_cat3_any_pop_exposed", "heat_p95_pop_exposed",
                    "surge_cat4_any_pop_exposed"])
    t = t.merge(ex[["GEOID"] + [c for c in scen_cols if c not in t]], on="GEOID", how="left")
    return t


def train_mask(t):
    return (t.low_pop_flag == 0).to_numpy()


def tabpfn_available():
    return bool(os.environ.get("TABPFN_TOKEN"))


def monotone_vector(features):
    return [1 if f in HAZ_MAIN else 0 for f in features]
