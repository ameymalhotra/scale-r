"""Alternative interventions: what a set of proposed projects would cover.

    bash scripts/ml/run_ml.sh scripts/ml/interventions.py --tracts 12086005303,12086000713 --type nature-based

Coverage only. It reports residents, residents exposed to each hazard, and
vulnerable residents in the chosen tracts, and how the gap ranking would
change if those tracts received a sited project. It does NOT estimate damages
avoided: there is no outcome data yet. The next data step for true impact is
NFIP flood insurance claims (OpenFEMA).

"Vulnerable residents" are residents of tracts in the top third of the
vulnerability score (PCA component RC1, general socioeconomic disadvantage).
"Funded" adds an assumed sited amount per resident to each chosen tract
(default: the county median among tracts with a sited project; --dollars-per-resident
to change it). The primary gap (need percentile minus the percentile of actual
sited dollars per resident, D-092) and the high-need-with-no-project flag are
recomputed for every tract. The secondary gap (need versus expected investment)
is recomputed with the funded tracts' predicted likelihood set to 1.
"""
import argparse
import json

import numpy as np
import pandas as pd

import ml_common as C

TYPES = {"gray": "Gray", "nature-based": "Green, Blue or Hybrid"}
HIGH_NEED = 0.75


def historical_mix(kind):
    """Hazard focus of existing sited projects of this type (descriptive)."""
    pj = pd.read_csv(C.STAGE1 / "model_table_projects_T4.csv")
    sub = pj[pj.T4 == (0 if kind == "gray" else 1)]
    return (sub.Hazard_Focus.value_counts(normalize=True).round(3)).to_dict()


def coverage(geoids, kind="gray", table=None, dollars_per_resident=None):
    tp = table if table is not None else pd.read_csv(C.STAGE2 / "tract_predictions.csv", dtype={"GEOID": str})
    tp = tp.copy()
    unknown = sorted(set(geoids) - set(tp.GEOID))
    if unknown:
        raise SystemExit(f"unknown tract GEOIDs: {unknown}")
    sel = tp.GEOID.isin(geoids)
    vul_pct = tp.vulnerability_rc1.rank(pct=True)
    vulnerable = vul_pct >= 2 / 3
    obs = tp.sited_dollars_per_resident_observed
    if dollars_per_resident is None:
        dollars_per_resident = float(obs[obs > 0].median())   # a typical sited project, per resident
    # primary gap: need versus ACTUAL sited investment (D-092). Funding adds the assumed amount.
    after_obs = obs + np.where(sel, dollars_per_resident, 0.0)
    gap_b = tp.need_pct - obs.rank(pct=True)
    gap_a = tp.need_pct - after_obs.rank(pct=True)
    high_b = (tp.need_pct >= HIGH_NEED) & (tp.T1_observed == 0)
    high_a = high_b & ~sel
    # secondary gap: need versus expected investment (predicted likelihood set to 1 if funded)
    exp_b = tp.need_pct - tp.pred_likelihood.rank(pct=True)
    exp_a = tp.need_pct - tp.pred_likelihood.where(~sel, 1.0).rank(pct=True)
    rank_b = gap_b.rank(ascending=False, method="min")
    rank_a = gap_a.rank(ascending=False, method="min")
    k = int(np.ceil(0.1 * gap_b.notna().sum()))
    res = {
        "intervention_type": kind, "tracts": int(sel.sum()),
        "assumed_sited_dollars_per_resident": round(dollars_per_resident, 2),
        "residents": float(tp.population[sel].sum()),
        "residents_exposed": {
            "sea_level_rise_3ft": float(tp.slr_3ft_pop_exposed[sel].sum()),
            "surge_category_3": float(tp.surge_cat3_any_pop_exposed[sel].sum()),
            "surge_category_4": float(tp.surge_cat4_any_pop_exposed[sel].sum()),
            "heat_top5pct_land": float(tp.heat_p95_pop_exposed[sel].sum())},
        "vulnerable_residents": float(tp.population[sel & vulnerable].sum()),
        "share_of_county": {"residents": float(tp.population[sel].sum() / tp.population.sum()),
                            "vulnerable_residents": float(tp.population[sel & vulnerable].sum()
                                                          / tp.population[vulnerable].sum())},
        "high_need_no_sited_project": {"tracts_before": int(high_b.sum()), "tracts_after": int(high_a.sum()),
                                       "residents_before": float(tp.population[high_b].sum()),
                                       "residents_after": float(tp.population[high_a].sum())},
        "gap_top10pct_tracts": int(k), "gap_top10pct_tracts_covered": int(((rank_b <= k) & sel).sum()),
        "original_gap_top10pct_tracts_still_top10pct_after": int(((rank_b <= k) & (rank_a <= k)).sum()),
        "per_tract": [{"GEOID": g, "gap_actual_before": r3(b), "gap_actual_after": r3(a),
                       "gap_rank_before": None if pd.isna(rb) else int(rb), "gap_rank_after": None if pd.isna(ra) else int(ra),
                       "gap_expected_before": r3(eb), "gap_expected_after": r3(ea),
                       "had_sited_project": int(h)}
                      for g, b, a, rb, ra, eb, ea, h in zip(tp.GEOID[sel], gap_b[sel], gap_a[sel], rank_b[sel], rank_a[sel],
                                                            exp_b[sel], exp_a[sel], tp.T1_observed[sel])],
        "historical_hazard_focus_of_this_type": historical_mix(kind),
        "note": "Coverage only. No damages avoided are estimated (no outcome data yet; next step: NFIP claims from OpenFEMA).",
    }
    return res


def r3(v):
    return None if pd.isna(v) else round(float(v), 3)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tracts", required=True, help="comma-separated 11-digit tract GEOIDs")
    ap.add_argument("--type", choices=list(TYPES), default="gray")
    ap.add_argument("--dollars-per-resident", type=float, default=None,
                    help="assumed sited dollars per resident for a funded tract (default: county median among "
                         "tracts with a sited project)")
    a = ap.parse_args()
    print(json.dumps(coverage([g.strip() for g in a.tracts.split(",") if g.strip()], a.type,
                              dollars_per_resident=a.dollars_per_resident), indent=1))


if __name__ == "__main__":
    main()
