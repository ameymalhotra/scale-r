"""DOR sales data file (SDF) to a sales table with non-personal fields only (prompt 28 follow-up, D-176).

    /Users/.../Climate-Resilience---Miami-Dade/.venv/bin/python -I scripts/benefit/build_sdf_sales.py

Only the 2026 final SDF is online in the DOR data portal (folders 2026F and
2026P only); it lists every recorded sale in 2025 and 2026 with its
qualification code. Earlier years (2021 to 2024) must be requested from DOR.
The SDF has no owner names or addresses; only these fields are kept:
parcel ID, use code, qualification code, vacant/improved code, sale year,
month and price, multi-parcel flag and sale ID code. Matched to the tax roll
parcels and to the county house-features layer (latest sale).
Writes data/processed/benefit/sdf_sales.parquet and a summary json.
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import paths  # noqa: E402

KEEP = ["PARCEL_ID", "DOR_UC", "QUAL_CD", "VI_CD", "SALE_YR", "SALE_MO", "SALE_PRC", "MULTI_PAR_SAL", "SALE_ID_CD"]


def main():
    files = sorted((paths.DOR_DIR / "sdf_extract").glob("SDF23F*.csv"))
    s = pd.concat([pd.read_csv(f, usecols=KEEP, dtype={"PARCEL_ID": str, "DOR_UC": str}) for f in files])
    s = s.drop_duplicates()
    s["DOR_UC"] = s.DOR_UC.str.zfill(3)
    s.columns = [c.lower() for c in s.columns]
    s.to_parquet(paths.SDF_SALES_PARQUET, index=False)
    nal = pd.read_csv(paths.DOR_DIR / "extract" / "NAL23F202601.csv", usecols=["PARCEL_ID"], dtype={"PARCEL_ID": str})
    pa = pd.read_parquet(paths.PA_FEATURES_PARQUET, columns=["parcel_id", "sale_date", "sale_price"])
    pa = pa.dropna(subset=["sale_date"])
    pa["yr"], pa["mo"] = pa.sale_date.dt.year, pa.sale_date.dt.month
    m = pa.merge(s, left_on=["parcel_id", "yr", "mo", "sale_price"], right_on=["parcel_id", "sale_yr", "sale_mo", "sale_prc"])
    seg = s.dor_uc.map({"001": "single_family", "004": "condo"})
    q = s.qual_cd.isin([1, 2]) if s.qual_cd.dtype != object else s.qual_cd.astype(str).isin(["01", "02", "1", "2"])
    R = {"files": [f.name for f in files], "sales": len(s), "by_year": s.sale_yr.value_counts().sort_index().to_dict(),
         "parcels_matched_to_tax_roll": round(float(s.parcel_id.isin(nal.PARCEL_ID).mean()), 4),
         "qualified_improved_by_segment": {k: int((q & (s.vi_cd == "I") & (seg == k)).sum()) for k in ["single_family", "condo"]},
         "house_layer_latest_sales_matched": int(len(m)),
         "sales_2021_2024": 0,
         "note": "only 2025 and 2026 sales are in the online file; 2021 to 2024 need a DOR request"}
    (paths.OUT_BENEFIT / "spec_alignment" / "sdf_sales_summary.json").write_text(json.dumps(R, indent=2, default=str))
    print(json.dumps(R, indent=1, default=str))


if __name__ == "__main__":
    main()
