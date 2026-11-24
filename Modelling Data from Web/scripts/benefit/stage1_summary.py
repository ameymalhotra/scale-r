"""Coverage, missing values and join rates for the Stage 1 report (prompt 27).

    .venv/bin/python -I "Modelling Data from Web/scripts/benefit/stage1_summary.py"

Reads the building table, the tax roll, the policies file (if finished) and the
FHFA extract; writes outputs/benefit/stage1/summary.json and a few CSV tables.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import paths  # noqa: E402

CK = paths.OUT_BENEFIT / "stage1"


def load_buildings():
    if paths.BUILDINGS_PARQUET.exists():
        return pd.read_parquet(paths.BUILDINGS_PARQUET)
    return pd.read_csv(paths.BENEFIT_DIR / "buildings.csv.gz", dtype={"parcel_geo_id": str, "GEOID_bg": str,
                                                                     "GEOID_tract": str, "cbfips": str})


def main():
    S = {}
    b = load_buildings()
    S["buildings"] = len(b)
    S["columns"] = list(b.columns)
    S["missing_share"] = b.isna().mean().round(4)[lambda s: s > 0].to_dict()
    S["value_totals_billion"] = {
        "nsi_structure": round(b.val_struct.sum() / 1e9, 2), "nsi_contents": round(b.val_cont.sum() / 1e9, 2),
        "tax_roll_jv_alloc": round(b.jv_alloc.sum() / 1e9, 2)}
    S["residents"] = {"night": int(b.residents_night.sum()), "day": int(b.residents_day.sum())}
    S["parcel_match"] = b.parcel_match.value_counts().to_dict()
    S["parcel_dist_ft"] = b.parcel_dist_ft.describe().round(1).to_dict()
    S["buildings_with_tax_roll"] = int(b.jv_parcel.notna().sum())
    S["occtype_group"] = b.occtype.str.split("-").str[0].value_counts().to_dict()
    S["st_damcat"] = b.st_damcat.value_counts().to_dict()
    S["found_type"] = b.found_type.value_counts().to_dict()
    S["basement_recoded"] = int(b.basement_recoded.sum())
    S["found_type_orig"] = b.nsi_found_type_orig.value_counts().to_dict()
    S["found_ht"] = b.found_ht.describe().round(2).to_dict()
    S["fema_zone"] = b.fema_zone.fillna("none").value_counts().to_dict()
    S["fema_sfha"] = b.fema_sfha.fillna("none").value_counts().to_dict()
    S["fema_bfe_present"] = int(b.fema_bfe_ft.notna().sum())
    S["fema_bfe"] = b.fema_bfe_ft.describe().round(1).to_dict()
    S["nsi_firmzone_vs_nfhl"] = pd.crosstab(b.firmzone.fillna("none"), b.fema_zone.fillna("none")).to_dict()
    for c in range(1, 6):
        S[f"surge_cat{c}"] = {"wet": int((b[f"surge_cat{c}_class"] > 0).sum()),
                              "median_depth_wet_ft": float(b.loc[b[f"surge_cat{c}_class"] > 0, f"surge_cat{c}_depth_ft"].median())}
    for c in ["slr_1ft", "slr_2ft", "slr_3ft", "slr_6ft", "slr_low_3ft"]:
        S[c] = int(b[c].sum())
    S["dem"] = b.ground_elev_ft_navd88.describe().round(2).to_dict()
    S["dem_missing"] = int(b.ground_elev_ft_navd88.isna().sum())
    d = (b.ground_elev_ft_navd88 - b.nsi_ground_elev_ft)
    S["dem_minus_nsi_ft"] = d.describe().round(2).to_dict()
    S["nsi_cbfips_bg_matches"] = float(b.nsi_cbfips_bg_matches.mean().round(4))
    S["tracts"] = int(b.GEOID_tract.nunique())
    S["bgs"] = int(b.GEOID_bg.nunique())
    S["year_built"] = {"nsi_med_yr_blt_zero": int((b.med_yr_blt <= 0).sum()),
                       "tax_roll_act_yr_blt_missing": int(b.act_yr_blt.isna().sum())}

    # tract table of building counts and values (for later stages)
    t = b.groupby("GEOID_tract").agg(buildings=("fd_id", "size"), val_struct=("val_struct", "sum"),
                                     val_cont=("val_cont", "sum"), jv_alloc=("jv_alloc", "sum"),
                                     residents_night=("residents_night", "sum"),
                                     sfha_buildings=("fema_sfha", lambda s: int((s == "T").sum())))
    t.to_csv(CK / "tract_building_summary.csv")

    # tax roll by use (whole roll)
    nal = pd.read_csv(paths.DOR_DIR / "extract" / "NAL23F202601.csv",
                      usecols=["PARCEL_ID", "DOR_UC", "JV", "QUAL_CD1", "QUAL_CD2", "SALE_YR1", "SALE_YR2", "VI_CD1"],
                      dtype=str)
    nal["JV"] = pd.to_numeric(nal.JV)
    S["nal"] = {"records": len(nal), "jv_billion": round(nal.JV.sum() / 1e9, 2),
                "dor_uc_top": nal.DOR_UC.value_counts().head(12).to_dict(),
                "qual_cd1": nal.QUAL_CD1.value_counts().to_dict(),
                "qual_cd2": nal.QUAL_CD2.value_counts().to_dict(),
                "sale_yr1": nal.SALE_YR1.value_counts().to_dict(),
                "sale_yr2": nal.SALE_YR2.value_counts().to_dict(),
                "qualified_01_02_sale1": int(nal.QUAL_CD1.isin(["01", "02"]).sum()),
                "qualified_01_02_sale2": int(nal.QUAL_CD2.isin(["01", "02"]).sum()),
                "qualified_01_02_improved_sale1": int((nal.QUAL_CD1.isin(["01", "02"]) & (nal.VI_CD1 == "I")).sum())}
    m = pd.read_csv(CK / "nal_to_parcel.csv.gz", dtype=str)
    S["nal_placement"] = m.placed_by.value_counts().to_dict()

    # policies, if the download has finished
    if paths.NFIP_POLICIES_CSV.exists():
        p = pd.read_csv(paths.NFIP_POLICIES_CSV, dtype=str)
        eff = pd.to_datetime(p.policyEffectiveDate, errors="coerce")
        S["policies"] = {"rows": len(p), "years": eff.dt.year.value_counts().sort_index().to_dict(),
                         "missing_share": p.isna().mean().round(4)[lambda s: s > 0].to_dict(),
                         "tracts": int(p.censusGeoid.str[:11].nunique())}
    fh = pd.read_csv(paths.FHFA_DIR / "hpi_at_tract_miami_dade.csv", dtype={"tract": str})
    S["fhfa"] = {"rows": len(fh), "tracts": int(fh.tract.nunique()), "years": [int(fh.year.min()), int(fh.year.max())],
                 "tracts_with_2025": int(fh[(fh.year == 2025) & fh.hpi.notna()].tract.nunique()),
                 "tracts_with_2010": int(fh[(fh.year == 2010) & fh.hpi.notna()].tract.nunique()),
                 "missing_share": fh.isna().mean().round(3).to_dict()}
    (CK / "summary.json").write_text(json.dumps(S, indent=2, default=lambda o: o.item() if hasattr(o, "item") else str(o)))
    print(json.dumps({k: v for k, v in S.items() if k not in ("columns", "nsi_firmzone_vs_nfhl")}, indent=1,
                     default=lambda o: o.item() if hasattr(o, "item") else str(o))[:6000])


if __name__ == "__main__":
    main()
