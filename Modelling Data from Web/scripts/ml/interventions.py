"""Alternative interventions: what a set of proposed projects would cover.

    bash scripts/ml/run_ml.sh scripts/ml/interventions.py --tracts 12086005303,12086000713 --type nature-based

Coverage only. It reports residents, residents exposed to each hazard, and
vulnerable residents in the chosen tracts, and how the gap ranking would
change if those tracts received a sited project. It does NOT estimate damages
avoided: there is no outcome data yet. The next data step for true impact is
NFIP flood insurance claims (OpenFEMA).

"Vulnerable residents" are residents of tracts in the top third of the
vulnerability score (PCA component RC1, general socioeconomic disadvantage).
"Funded" means the tract's predicted likelihood of a sited project is set to 1,
and the gap (need percentile minus predicted-likelihood percentile) is
recomputed for every tract.
"""
import argparse
import json

import numpy as np
import pandas as pd

import ml_common as C

TYPES = {"gray": "Gray", "nature-based": "Green, Blue or Hybrid"}


def historical_mix(kind):
    """Hazard focus of existing sited projects of this type (descriptive)."""
    pj = pd.read_csv(C.STAGE1 / "model_table_projects_T4.csv")
    sub = pj[pj.T4 == (0 if kind == "gray" else 1)]
    return (sub.Hazard_Focus.value_counts(normalize=True).round(3)).to_dict()


def coverage(geoids, kind="gray", table=None):
    tp = table if table is not None else pd.read_csv(C.STAGE2 / "tract_predictions.csv", dtype={"GEOID": str})
    tp = tp.copy()
    unknown = sorted(set(geoids) - set(tp.GEOID))
    if unknown:
        raise SystemExit(f"unknown tract GEOIDs: {unknown}")
    sel = tp.GEOID.isin(geoids)
    vul_pct = tp.vulnerability_rc1.rank(pct=True)
    vulnerable = vul_pct >= 2 / 3
    before = tp.gap.copy()
    after_pred = tp.pred_likelihood.where(~sel, 1.0)
    after_gap = tp.need_pct - after_pred.rank(pct=True)
    rank_b = before.rank(ascending=False, method="min")
    rank_a = after_gap.rank(ascending=False, method="min")
    k = int(np.ceil(0.1 * tp.gap.notna().sum()))
    res = {
        "intervention_type": kind, "tracts": int(sel.sum()),
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
        "gap_top10pct_tracts_before": int((rank_b <= k).sum()),
        "gap_top10pct_tracts_covered": int(((rank_b <= k) & sel).sum()),
        "original_gap_top10pct_tracts_still_top10pct_after": int(((rank_b <= k) & (rank_a <= k)).sum()),
        "per_tract": [{"GEOID": g, "gap_before": None if pd.isna(b) else round(float(b), 3),
                       "gap_after": None if pd.isna(a) else round(float(a), 3),
                       "gap_rank_before": None if pd.isna(rb) else int(rb), "gap_rank_after": None if pd.isna(ra) else int(ra)}
                      for g, b, a, rb, ra in zip(tp.GEOID[sel], before[sel], after_gap[sel], rank_b[sel], rank_a[sel])],
        "historical_hazard_focus_of_this_type": historical_mix(kind),
        "note": "Coverage only. No damages avoided are estimated (no outcome data yet; next step: NFIP claims from OpenFEMA).",
    }
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tracts", required=True, help="comma-separated 11-digit tract GEOIDs")
    ap.add_argument("--type", choices=list(TYPES), default="gray")
    a = ap.parse_args()
    print(json.dumps(coverage([g.strip() for g in a.tracts.split(",") if g.strip()], a.type), indent=1))


if __name__ == "__main__":
    main()
