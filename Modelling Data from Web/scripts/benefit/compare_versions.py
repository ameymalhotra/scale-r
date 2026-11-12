"""Compare three versions of expected yearly damage against NFIP claims (prompt 28 follow-up, D-174).

    /Users/.../Climate-Resilience---Miami-Dade/.venv/bin/python -I scripts/benefit/compare_versions.py

Versions (structure and contents, including the part beyond the rarest storm,
displacement excluded so all three count the same things):
- stage2: Stage 2 (2009 maps, FEMA 1% and 0.2% only, NOAA ground; D-137, D-143);
- transect: Part 2 method (2027 levels, nearest-transect still water, D-170);
- anchored: coastal levels anchored to the 2027 mapped 1% elevation (D-173).
Claims: recency-weighted annual paid claims in 2025 dollars (D-140, D-144).
Tracts: those with at least 50 occupied homes (ACS), as Stage 2.
Nothing is scaled to claims. Writes outputs/benefit/spec_alignment/version_comparison.json and .csv.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
from baseline_risk import boot_spearman, observed_claims, occupied_units  # noqa: E402

OUT = paths.OUT_BENEFIT / "spec_alignment"


def main():
    B = pd.read_parquet(paths.MODULE_B_PARQUET)
    S2 = pd.read_parquet(paths.EAD_BUILDINGS_PARQUET, columns=["fd_id", "GEOID_tract", "residential", "ead_mid_slr0",
                                                                "ead_disp_slr0"])
    S2 = S2.set_index("fd_id").reindex(B.fd_id)
    V = pd.DataFrame({"GEOID_tract": B.GEOID_tract.to_numpy(), "residential": B.residential.to_numpy(),
                      "stage2": (S2.ead_mid_slr0 - S2.ead_disp_slr0).fillna(0).to_numpy(),
                      "transect": (B.eyd_mid_coastal_transect + B.eyd_tail_mid_coastal_transect).to_numpy(),
                      "anchored": (B.eyd_mid + B.eyd_tail_mid).to_numpy()})
    obs, _ = observed_claims()
    units = occupied_units()
    claims = obs.claims_weighted_annual_2025
    R = {"claims_county_million": round(float(claims.sum()) / 1e6, 1)}
    rows = []
    for v in ["stage2", "transect", "anchored"]:
        r = {"version": v, "county_million": round(float(V[v].sum()) / 1e6, 1),
             "residential_million": round(float(V.loc[V.residential, v].sum()) / 1e6, 1)}
        for lab, m in [("all", np.ones(len(V), bool)), ("res", V.residential.to_numpy())]:
            t = V[m].groupby("GEOID_tract")[v].sum().to_frame("model").join(claims.rename("claims")) \
                .join(units.rename("units")).fillna(0)
            t = t[t.units >= 50]
            mp, cp = t.model / t.units, t.claims / t.units
            r[f"ratio_{lab}"] = round(float(t.model.sum() / t.claims.sum()), 2)
            r[f"spearman_{lab}"] = round(float(spearmanr(mp, cp).statistic), 3)
            r[f"spearman_{lab}_ci95"] = boot_spearman(mp, cp)
            if lab == "all":
                r["tracts"] = int(len(t))
                r["tracts_zero_model_with_claims"] = int(((t.model == 0) & (t.claims > 0)).sum())
                r["claims_share_in_zero_model_tracts"] = round(float(t.claims[t.model == 0].sum() / t.claims.sum()), 3)
                # one-sided bias check: model share vs claims share by model decile
                d = pd.qcut(mp.rank(method="first"), 10, labels=False)
                g = pd.DataFrame({"d": d, "m": t.model, "c": t.claims}).groupby("d").sum()
                r["decile_model_share"] = (g.m / g.m.sum()).round(3).tolist()
                r["decile_claims_share"] = (g.c / g.c.sum()).round(3).tolist()
                r["top_decile_ratio"] = round(float(g.m.iloc[-1] / max(g.c.iloc[-1], 1)), 1)
                r["bottom_half_ratio"] = round(float(g.m.iloc[:5].sum() / max(g.c.iloc[:5].sum(), 1)), 2)
        rows.append(r)
    R["versions"] = rows
    pd.DataFrame(rows).drop(columns=["decile_model_share", "decile_claims_share"]).to_csv(OUT / "version_comparison.csv", index=False)
    (OUT / "version_comparison.json").write_text(json.dumps(R, indent=2, default=str))
    print(json.dumps(R, indent=1, default=str))


if __name__ == "__main__" and len(sys.argv) == 1:
    main()


def frequent_part():
    """Check added for the report: only the part of the anchored EYD from storms between 10% and 2%,
    the range the 1978 to 2025 claims record mostly samples."""
    from module_b_eyd import EVENTS, P
    B = pd.read_parquet(paths.MODULE_B_PARQUET)
    L = np.maximum.accumulate(B[[f"loss_{e}_mid" for e in EVENTS]].to_numpy(), axis=1)
    part = (0.5 * (L[:, :-1] + L[:, 1:]) * (P[:-1] - P[1:]))[:, :2].sum(1)      # 10%-4% and 4%-2%
    obs, _ = observed_claims()
    units = occupied_units()
    t = pd.Series(part).groupby(B.GEOID_tract.to_numpy()).sum().to_frame("model") \
        .join(obs.claims_weighted_annual_2025.rename("claims")).join(units.rename("units")).fillna(0)
    t = t[t.units >= 50]
    r = {"county_million": round(float(part.sum()) / 1e6, 1), "ratio_all": round(float(t.model.sum() / t.claims.sum()), 2),
         "spearman_all": round(float(spearmanr(t.model / t.units, t.claims / t.units).statistic), 3)}
    j = json.loads((OUT / "version_comparison.json").read_text())
    j["anchored_frequent_storms_only"] = r
    (OUT / "version_comparison.json").write_text(json.dumps(j, indent=2, default=str))
    print(r)


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "frequent":
    frequent_part()
