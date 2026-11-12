"""Which tax roll (NAL 2026) fields give homestead status, exemptions, assessed and taxable value
(prompt 28 Part 1). Aggregate counts only; no owner names or addresses are read.

    /Users/.../Climate-Resilience---Miami-Dade/.venv/bin/python -I scripts/benefit/tax_fields_summary.py

Writes outputs/benefit/spec_alignment/tax_fields_summary.json.
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import paths  # noqa: E402

OUT = paths.OUT_BENEFIT / "spec_alignment"
VALUE = ["JV", "AV_SD", "AV_NSD", "TV_SD", "TV_NSD", "JV_HMSTD", "AV_HMSTD", "JV_NON_HMSTD_RESD",
         "AV_NON_HMSTD_RESD", "JV_RESD_NON_RESD", "AV_RESD_NON_RESD", "SPEC_FEAT_VAL", "LND_VAL"]
EXEMPT = ["EXMPT_01", "EXMPT_02", "EXMPT_03", "EXMPT_05", "EXMPT_10", "EXMPT_11", "EXMPT_15", "EXMPT_16",
          "EXMPT_17", "EXMPT_38", "EXMPT_81", "EXMPT_82"]
CODES = ["DOR_UC", "SPASS_CD", "TAX_AUTH_CD", "ASS_TRNSFR_FG", "YR_VAL_TRNSF"]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    f = paths.DOR_DIR / "extract" / "NAL23F202601.csv"
    d = pd.read_csv(f, usecols=["PARCEL_ID"] + VALUE + EXEMPT + CODES, dtype={"DOR_UC": str, "TAX_AUTH_CD": str},
                    low_memory=False)
    n = len(d)
    res = d.DOR_UC.str.zfill(3).str[:2].isin(["00", "01", "02", "03", "04", "05", "06", "07", "08", "09"])
    hm = d.JV_HMSTD.fillna(0) > 0
    R = {"file": f.name, "parcels": n,
         "nonzero_share": {c: round(float((d[c].fillna(0) > 0).mean()), 4) for c in VALUE + EXEMPT},
         "totals_billion": {c: round(float(d[c].fillna(0).sum()) / 1e9, 2) for c in VALUE},
         "homestead_parcels": int(hm.sum()),
         "homestead_share_of_residential": round(float(hm[res].mean()), 3),
         "homestead_vs_exempt01": int(((d.EXMPT_01.fillna(0) > 0) & hm).sum()),
         "spass_cd": d.SPASS_CD.fillna("blank").astype(str).value_counts().to_dict(),
         "tax_authority_codes": int(d.TAX_AUTH_CD.nunique()),
         "portability_flag": d.ASS_TRNSFR_FG.fillna("blank").astype(str).value_counts().head(5).to_dict(),
         # Save Our Homes gap: just value minus assessed value on homestead parcels
         "homestead_soh_gap_median_share": round(float(((d.JV - d.AV_SD) / d.JV)[hm & (d.JV > 0)].median()), 3),
         "nonhomestead_res_cap_gap_median_share": round(float(((d.JV - d.AV_SD) / d.JV)[~hm & res & (d.JV > 0)].median()), 3)}
    (OUT / "tax_fields_summary.json").write_text(json.dumps(R, indent=2, default=str))
    print(json.dumps(R, indent=1, default=str))


if __name__ == "__main__":
    main()
