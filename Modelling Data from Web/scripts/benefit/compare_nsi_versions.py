"""Compare NSI 2022 and NSI 2026 for Miami-Dade (prompt 27 Stage 1, D-130).

    .venv/bin/python -I "Modelling Data from Web/scripts/benefit/compare_nsi_versions.py"

Reads the NSI 2022 Miami-Dade rows from the 2022 GeoPackage and the NSI 2026 API
extract, before any recoding. Writes outputs/benefit/stage1/nsi_2022_vs_2026.json
and a tract-level count comparison CSV.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyogrio

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import paths  # noqa: E402

OUT = paths.OUT_BENEFIT / "stage1"
COLS = ["fd_id", "cbfips", "occtype", "st_damcat", "found_type", "found_ht", "sqft", "num_story", "val_struct",
        "val_cont", "pop2amu65", "pop2amo65", "pop2pmu65", "pop2pmo65", "med_yr_blt", "source"]


def summarise(d):
    return {
        "structures": len(d),
        "structure_value_billion": round(d.val_struct.sum() / 1e9, 1),
        "contents_value_billion": round(d.val_cont.sum() / 1e9, 1),
        "residents_night": int((d.pop2amu65 + d.pop2amo65).sum()),
        "residents_day": int((d.pop2pmu65 + d.pop2pmo65).sum()),
        "floor_area_million_sqft": round(d.sqft.sum() / 1e6, 1),
        "damage_category": d.st_damcat.value_counts().to_dict(),
        "foundation_type": d.found_type.value_counts().to_dict(),
        "with_basement_occtype": int(d.occtype.str.contains("WB", na=False).sum()),
        "found_ht_median_ft": float(d.found_ht.median()),
        "found_ht_mean_ft": round(float(d.found_ht.mean()), 2),
        "occupancy_group": d.occtype.str.split("-").str[0].str[:4].value_counts().head(10).to_dict(),
        "median_structure_value_res1": round(float(d.loc[d.occtype.str.startswith("RES1"), "val_struct"].median())),
        "source": d.source.value_counts().to_dict(),
    }


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    gpkg = paths.NSI_DIR / "extract" / "nsi_2022_12.gpkg"
    n22 = pyogrio.read_dataframe(gpkg, where="cbfips LIKE '12086%'", columns=COLS, read_geometry=False)
    n26 = pyogrio.read_dataframe(paths.NSI_2026_GEOJSON, columns=COLS, read_geometry=False)
    n26 = n26[n26.cbfips.str.startswith("12086")]
    res = {"nsi_2022": summarise(n22), "nsi_2026": summarise(n26)}
    res["shared_fd_id"] = int(len(set(n22.fd_id) & set(n26.fd_id)))
    # NSI 2022 cbfips are 2010 blocks and NSI 2026 cbfips are 2020 blocks, so tracts are
    # compared through our own point-in-polygon join to 2020 block groups (build_buildings.py)
    res["cbfips_tracts"] = {"2022": int(n22.cbfips.str[:11].nunique()), "2026": int(n26.cbfips.str[:11].nunique())}
    g22 = pd.read_csv(paths.OUT_BENEFIT / "stage1_nsi2022" / "bld_bg.csv.gz", dtype={"GEOID_tract": str})
    g26 = pd.read_csv(OUT / "bld_bg.csv.gz", dtype={"GEOID_tract": str})
    v22 = pd.merge(g22, n22[["fd_id", "val_struct"]], on="fd_id").groupby("GEOID_tract").agg(n=("fd_id", "size"), v=("val_struct", "sum"))
    v26 = pd.merge(g26, n26[["fd_id", "val_struct"]], on="fd_id").groupby("GEOID_tract").agg(n=("fd_id", "size"), v=("val_struct", "sum"))
    t = v22.join(v26, lsuffix="2022", rsuffix="2026", how="outer").fillna(0)
    res["tract_spearman_2020_tracts"] = {"structures": round(float(t.n2022.corr(t.n2026, method="spearman")), 3),
                                         "structure_value": round(float(t.v2022.corr(t.v2026, method="spearman")), 3)}
    res["tracts_2020"] = {"2022": int((t.n2022 > 0).sum()), "2026": int((t.n2026 > 0).sum())}
    t.to_csv(OUT / "nsi_2022_vs_2026_tract_counts.csv")
    # Where the structure value increase comes from (log decomposition, D-135):
    # total value = structures x floor area per structure x value per square foot
    def parts(d):
        return len(d), d.sqft.sum() / len(d), d.val_struct.sum() / d.sqft.sum()
    dec = {}
    for name, f in {"all": lambda d: d, "RES1": lambda d: d[d.occtype.str.startswith("RES1")]}.items():
        (n0, a0, v0), (n1, a1, v1) = parts(f(n22)), parts(f(n26))
        lt = np.log((n1 * a1 * v1) / (n0 * a0 * v0))
        comp = {"more_structures": np.log(n1 / n0), "larger_floor_area_per_structure": np.log(a1 / a0),
                "higher_value_per_sqft": np.log(v1 / v0)}
        dec[name] = {"value_2022_billion": round(n0 * a0 * v0 / 1e9, 1), "value_2026_billion": round(n1 * a1 * v1 / 1e9, 1),
                     "ratio": round(float(np.exp(lt)), 3),
                     "structures": [n0, n1], "sqft_per_structure": [round(a0), round(a1)],
                     "value_per_sqft": [round(v0, 2), round(v1, 2)],
                     "share_of_log_increase": {k: round(float(v / lt), 3) for k, v in comp.items()},
                     "value_per_structure": [round(n0 and a0 * v0), round(a1 * v1)]}
    res["value_increase_decomposition"] = dec
    res["value_basis"] = {
        "nsi_2022": "depreciated replacement value; 2021 price levels; 1% a year depreciation for 20 years, then held at 80% (NSI 2022 technical documentation)",
        "nsi_2026": "val_struct = depreciated replacement value, fullrep = replacement cost new; August 2025 price levels; county construction wage adjustment; tract-based depreciation curves (NSI 2026 technical documentation)",
        "contents": "NSI 2026 contents = depreciated structure value x occupancy ratio; RES1 ratio 0.5, while USACE EGM 04-01 assumes 1.0 for EGM curves (NSI 2026 technical documentation)"}
    (OUT / "nsi_2022_vs_2026.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
