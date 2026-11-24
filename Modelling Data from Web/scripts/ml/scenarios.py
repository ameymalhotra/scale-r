"""Scenario engine: re-predict every tract under alternative hazard scenarios.

Run after stage2_models.py:
    bash scripts/ml/run_ml.sh scripts/ml/scenarios.py      (from Modelling Data from Web/)

Uses the monotone-constrained scenario model (more hazard can never lower the
predicted likelihood). Each scenario replaces the value of the one feature in
its hazard family (D-080) and keeps the other families at the primary
scenario:
  sea level rise  slr_3ft_pop_share   <- share at 1, 2, 3 or 6 ft
  storm surge     surge_cat3_any_pop_share <- share at Category 1, 2, 3, 4 or
                  the corrected Category 5 (pixel maximum)
  surface heat    heat_lst_popwt_mean_f <- current values, or ILLUSTRATIVE
                  uniform warming of +1, +2, +3 F (no heat scenario layer
                  exists for this measure; D-084). Heat scenarios change need
                  and the gap only; the model is not applied (D-093)
A tract whose new value falls outside the range seen in training is flagged
as extrapolation. Need and gap are recomputed with each scenario's exposure,
ranked against the current (baseline) distribution so that more hazard raises
need. Outputs: outputs/ml/dashboard/scenarios.json, outputs/ml/stage2/scenario_summary.csv
"""
import json

import joblib
import numpy as np
import pandas as pd

import ml_common as C

SCENARIOS = (
    [{"id": f"slr_{k}ft", "family": "sea level rise", "label": f"Sea level rise {k} ft", "feature": "slr_3ft_pop_share",
      "source": f"slr_{k}ft_pop_share", "exposed": f"slr_{k}ft_pop_exposed", "hypothetical": False} for k in (1, 2, 3, 6)]
    + [{"id": f"surge_cat{c}", "family": "storm surge", "label": f"Storm surge Category {c}",
        "feature": "surge_cat3_any_pop_share",
        "source": f"surge_cat{c}_any_pop_share" if c < 5 else "surge_cat5max_any_pop_share",
        "exposed": f"surge_cat{c}_any_pop_exposed" if c < 5 else "surge_cat5max_any_pop_exposed",
        "hypothetical": False} for c in (1, 2, 3, 4, 5)]
    + [{"id": f"heat_plus{d}f" if d else "heat_current", "family": "surface heat",
        "label": f"Surface heat +{d} F (illustrative)" if d else "Surface heat, current",
        "feature": "heat_lst_popwt_mean_f", "shift": float(d), "exposed": "heat_p95_pop_exposed",
        "hypothetical": bool(d)} for d in (0, 1, 2, 3)]
)


def r4(v):
    return None if np.isnan(v) else round(float(v), 4)


def pct_vs(base, x):
    """Percentile of x within the current (baseline) values, average-rank convention.

    For x drawn from base this equals pandas rank(pct=True), the convention used
    for need and the gaps in stage2_models.py, so the current scenario
    reproduces tracts.json exactly.
    """
    b = np.sort(base[~np.isnan(base)])
    lo = np.searchsorted(b, x, side="left")
    hi = np.searchsorted(b, x, side="right")
    out = (lo + hi + 1) / 2 / len(b)
    return np.where(np.isnan(x), np.nan, out)


def main():
    t = C.load_table()
    ex = pd.read_csv(C.paths.EXPOSURE_DIR / "exposure_tract.csv", dtype={"GEOID": str}).set_index("GEOID")
    bundle = joblib.load(C.STAGE2 / "model_scenario.joblib")
    m, feats = bundle["model"], bundle["features"]
    lo, hi = bundle["train_min"], bundle["train_max"]
    tp = pd.read_csv(C.STAGE2 / "tract_predictions.csv", dtype={"GEOID": str}).set_index("GEOID").loc[t.GEOID]
    vul_pct = tp.vulnerability_rc1.rank(pct=True).to_numpy()
    X0 = t[feats].copy()
    p0 = m.predict_proba(X0)[:, 1]
    base_haz = {f: X0[f].to_numpy() for f in C.HAZ_MAIN}
    base_expo = np.nanmean(np.column_stack([pct_vs(base_haz[f], base_haz[f]) for f in C.HAZ_MAIN]), axis=1)
    base_need = pct_vs(base_expo, base_expo) * vul_pct
    pop = t.population.to_numpy()
    sited_pct = tp.sited_pct.to_numpy()
    out, summ = [], []
    for s in SCENARIOS:
        X = X0.copy()
        f = s["feature"]
        X[f] = t[s["source"]].to_numpy() if "source" in s else X0[f].to_numpy() + s["shift"]
        v = X[f].to_numpy()
        extrap = (v > hi[f] + 1e-12) | (v < lo[f] - 1e-12)
        # heat changes need and gap only: past investment did not follow heat, so the model
        # is not applied to heat scenarios and the likelihood stays at its current value (D-093)
        model_applied = s["family"] != "surface heat"
        p = m.predict_proba(X)[:, 1] if model_applied else p0.copy()
        expo = np.nanmean(np.column_stack([pct_vs(base_haz[g], X[g].to_numpy()) for g in C.HAZ_MAIN]), axis=1)
        need = pct_vs(base_expo, expo) * vul_pct
        need_pct = pct_vs(base_need, need)
        pred_pct = pct_vs(p0, p)
        gap_expected = need_pct - pred_pct          # secondary: need versus expected investment
        gap = need_pct - sited_pct                  # primary: need versus actual sited investment (D-092)
        high_no = (need_pct >= 0.75) & (t.T1.to_numpy() == 0)
        exposed = ex.loc[t.GEOID, s["exposed"]].to_numpy() if s["exposed"] in ex else np.full(len(t), np.nan)
        summ.append({"id": s["id"], "family": s["family"], "label": s["label"], "hypothetical": s["hypothetical"],
                     "expected_tracts_with_sited_project": float(p.sum()),
                     "mean_likelihood": float(p.mean()), "mean_change_vs_current": float((p - p0).mean()),
                     "tracts_extrapolated": int(extrap.sum()), "residents_in_extrapolated_tracts": float(pop[extrap].sum()),
                     "residents_exposed": float(np.nansum(exposed)),
                     "model_applied": model_applied,
                     "mean_need_pct": float(np.nanmean(need_pct)), "tracts_gap_over_0.5": int(np.nansum(gap >= 0.5)),
                     "tracts_expected_gap_over_0.5": int(np.nansum(gap_expected >= 0.5)),
                     "tracts_high_need_no_sited_project": int(high_no.sum()),
                     "residents_high_need_no_sited_project": float(pop[high_no].sum())})
        out.append({**{k: s[k] for k in ("id", "family", "label", "hypothetical")}, "summary": summ[-1],
                    "columns": ["GEOID", "likelihood", "change", "extrapolated", "need_pct", "gap_actual",
                                "gap_expected", "high_need_no_sited_project"],
                    "tracts": [[g, round(float(a), 4), round(float(a - b), 4), int(e), r4(n), r4(q), r4(q2), int(h)]
                               for g, a, b, e, n, q, q2, h in zip(t.GEOID, p, p0, extrap, need_pct, gap, gap_expected, high_no)]})
    S = pd.DataFrame(summ)
    print(S.to_string(index=False, float_format=lambda v: f"{v:,.3f}"))
    S.to_csv(C.STAGE2 / "scenario_summary.csv", index=False)
    # monotonicity sanity: within each non-hypothetical family, more hazard never lowers a tract's prediction
    for fam, ids in (("sea level rise", ["slr_1ft", "slr_2ft", "slr_3ft", "slr_6ft"]),
                     ("surface heat", ["heat_current", "heat_plus1f", "heat_plus2f", "heat_plus3f"])):
        P = np.array([[r[1] for r in o["tracts"]] for o in out if o["id"] in ids])
        print(f"{fam}: tracts where a higher scenario lowers the prediction: {int((np.diff(P, axis=0) < -1e-9).any(axis=0).sum())}")
    meta = {"model": bundle["name"], "monotone_features": C.HAZ_MAIN, "preliminary": True,
            "note": ("Predicted likelihood of a sited project under current patterns of investment, not where "
                     "investment should go. Extrapolated tracts have scenario values outside the training range. "
                     "Heat +1 to +3 F are illustrative uniform warming, not projections."),
            "heat_note": ("Heat scenarios change need and the gap only. They do not change predicted investment, "
                          "because past investment did not follow heat."),
            "gap_actual": "need percentile minus the percentile of actual sited dollars per resident (primary)",
            "gap_expected": "need percentile minus the percentile of predicted likelihood (need versus expected investment)"}
    (C.DASH / "scenarios.json").write_text(json.dumps({"meta": meta, "scenarios": out}, separators=(",", ":")))
    print("wrote", C.DASH / "scenarios.json")


if __name__ == "__main__":
    main()
