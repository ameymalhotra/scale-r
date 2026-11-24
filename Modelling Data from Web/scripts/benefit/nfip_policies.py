"""NFIP policies for Miami-Dade and the claims check per insured building (prompt 28 follow-up, D-181).

    /Users/.../Climate-Resilience---Miami-Dade/.venv/bin/python -I scripts/benefit/nfip_policies.py

Source: OpenFEMA NfipPoliciesV3.parquet (74,739,461 records, refreshed
9 Sep 2026), downloaded whole and checked: size 3,713,009,365 bytes and MD5
275e07e99258e4ff7684cf4505f91406 both match FEMA's server (Content-Range
and ETag). The dataset is already redacted; only the fields below are kept,
filtered to censusGeoid starting with 12086.
1. Policies in force by tract and year: policy-years = days in force / 365,
   using each policy's effective and termination dates (2009 onwards).
2. Take-up: residential policy-years per year (2015 to 2025 average) divided
   by occupied homes (ACS), by tract and county.
3. Claims check per insured building: modelled insured loss by tract =
   residential expected yearly damage (anchored, D-174) x tract take-up x the
   paid-to-damage ratio from claims (D-146). Compared with claims (2025
   dollars, recency weighted), totals and tract ranking; Stage 2 the same way.
   Also claims per policy-year against modelled damage per home.
4. Floor heights from elevation certificate fields, summarised by block
   group only (median lowest floor minus lowest adjacent grade), never as
   single records.
Writes data/processed/benefit/nfip_policies_miami_dade.parquet (gitignored)
and outputs/benefit/module_d/nfip_policies_check.json.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.dataset as ds
import pyarrow.compute as pc
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
from baseline_risk import boot_spearman, observed_claims, occupied_units  # noqa: E402

KEEP = ["censusGeoid", "policyEffectiveDate", "policyTerminationDate", "policyCount", "occupancyType",
        "ratedFloodZone", "floodZoneCurrent", "totalBuildingInsuranceCoverage", "totalContentsInsuranceCoverage",
        "buildingReplacementCost", "elevationCertificateIndicator", "elevationDifference", "lowestFloorElevation",
        "lowestAdjacentGrade", "baseFloodElevation", "originalConstructionDate", "numberOfFloorsInInsuredBuilding",
        "postFIRMConstructionIndicator", "primaryResidenceIndicator", "buildingDeductibleCode"]
RES_OCC = {1, 2, 3, 11, 12, 13, 14, 15, 16}
YEARS = range(2015, 2026)


def extract():
    d = ds.dataset(paths.NFIP_POLICIES_PARQUET_FULL)
    flt = (ds.field("propertyState") == "FL") & pc.starts_with(ds.field("censusGeoid"), "12086")
    t = d.to_table(columns=KEEP, filter=flt)
    p = t.to_pandas()
    for c in ["lowestFloorElevation", "lowestAdjacentGrade", "baseFloodElevation"]:
        p[c] = pd.to_numeric(p[c], errors="coerce").astype(float)
    p.to_parquet(paths.NFIP_POLICIES_MD_PARQUET, index=False)
    return p


def main():
    p = pd.read_parquet(paths.NFIP_POLICIES_MD_PARQUET) if paths.NFIP_POLICIES_MD_PARQUET.exists() else extract()
    p["tract"] = p.censusGeoid.str[:11]
    p["bg"] = p.censusGeoid.str[:12]
    eff = pd.to_datetime(p.policyEffectiveDate)
    term = pd.to_datetime(p.policyTerminationDate)
    cnt = p.policyCount.fillna(1).clip(lower=1).to_numpy()
    res = p.occupancyType.isin(RES_OCC).to_numpy()
    R = {"records": len(p), "geoid_length_counts": p.censusGeoid.str.len().value_counts().to_dict(),
         "effective_years": [int(eff.dt.year.min()), int(eff.dt.year.max())]}
    py = {}
    for y in YEARS:
        a, b = pd.Timestamp(f"{y}-01-01"), pd.Timestamp(f"{y + 1}-01-01")
        days = (np.minimum(term, b) - np.maximum(eff, a)).dt.days.clip(lower=0).to_numpy()
        py[y] = pd.Series(days / 365.0 * cnt * res).groupby(p.tract.to_numpy()).sum()
    PY = pd.DataFrame(py).fillna(0)
    R["county_residential_policy_years"] = {int(y): int(round(PY[y].sum())) for y in YEARS}
    units = occupied_units()
    take = (PY.mean(axis=1) / units.reindex(PY.index)).replace([np.inf], np.nan)
    R["county_takeup_2015_2025"] = round(float(PY.mean(axis=1).sum() / units.sum()), 3)
    R["tract_takeup_quantiles"] = take.describe(percentiles=[.1, .5, .9]).round(3).to_dict()

    # modelled insured loss by tract
    B = pd.read_parquet(paths.MODULE_B_PARQUET, columns=["fd_id", "GEOID_tract", "residential", "eyd_mid", "eyd_tail_mid"])
    S2 = pd.read_parquet(paths.EAD_BUILDINGS_PARQUET, columns=["fd_id", "residential", "ead_mid_slr0", "ead_disp_slr0", "GEOID_tract"])
    stage2_pay = json.loads((paths.OUT_BENEFIT / "stage2" / "summary.json").read_text())
    pay_ratio = next(s["pay_ratio"] for s in stage2_pay["gap_decomposition"]["steps"] if "pay_ratio" in s)
    obs, _ = observed_claims()
    claims = obs.claims_weighted_annual_2025
    models = {"anchored": B[B.residential].assign(v=B.eyd_mid + B.eyd_tail_mid).groupby("GEOID_tract").v.sum(),
              "stage2": S2[S2.residential].assign(v=S2.ead_mid_slr0 - S2.ead_disp_slr0).groupby("GEOID_tract").v.sum()}
    T = pd.DataFrame({"takeup": take, "units": units, "claims": claims, "policy_years": PY.mean(axis=1)})
    for k, v in models.items():
        T[k] = v
    T = T.fillna(0)
    T = T[T.units >= 50]
    T["takeup_c"] = T.takeup.clip(0, 1)
    R["pay_ratio_used"] = pay_ratio
    R["comparison"] = {}
    for k in models:
        ins = T[k] * T.takeup_c * pay_ratio
        R["comparison"][k] = {
            "model_residential_million": round(float(T[k].sum()) / 1e6, 1),
            "model_insured_million": round(float(ins.sum()) / 1e6, 1),
            "claims_million": round(float(T.claims.sum()) / 1e6, 1),
            "ratio_insured_model_to_claims": round(float(ins.sum() / T.claims.sum()), 2),
            "spearman_insured_totals": round(float(spearmanr(ins, T.claims).statistic), 3),
            "spearman_insured_totals_ci95": boot_spearman(ins, T.claims, n=500),
            "spearman_per_policy_year": round(float(spearmanr((ins / T.policy_years.replace(0, np.nan)).fillna(0),
                                                               (T.claims / T.policy_years.replace(0, np.nan)).fillna(0)).statistic), 3)}
    # gap step 5 replaced: measured take-up against Stage 2's implied insured share
    R["stage2_implied_insured_share"] = next(s["implied_insured_share"] for s in stage2_pay["gap_decomposition"]["steps"]
                                             if "implied_insured_share" in s)
    # floor heights from elevation certificates, block-group summaries only
    ec = p[p.lowestFloorElevation.notna() & p.lowestAdjacentGrade.notna() & res]
    ec = ec.assign(fh=ec.lowestFloorElevation - ec.lowestAdjacentGrade)
    ec = ec[ec.fh.between(-5, 20)]
    g = ec.groupby("bg").fh.agg(["size", "median"])
    g = g[g["size"] >= 10]
    g.round(2).to_csv(paths.OUT_BENEFIT / "module_d" / "nfip_floor_height_by_bg.csv")
    R["floor_height_from_certificates"] = {"policies_with_fields": int(len(ec)), "block_groups_10plus": int(len(g)),
                                           "median_ft": round(float(ec.fh.median()), 2),
                                           "p25_p75_ft": [round(float(ec.fh.quantile(.25)), 2), round(float(ec.fh.quantile(.75)), 2)],
                                           "ec_indicator_counts": p.elevationCertificateIndicator.fillna("blank").value_counts().head(6).to_dict(),
                                           "elevation_difference_nonnull": int(p.elevationDifference.notna().sum())}
    (paths.OUT_BENEFIT / "module_d" / "nfip_policies_check.json").write_text(json.dumps(R, indent=2, default=str))
    print(json.dumps(R, indent=1, default=str))


if __name__ == "__main__":
    main()
