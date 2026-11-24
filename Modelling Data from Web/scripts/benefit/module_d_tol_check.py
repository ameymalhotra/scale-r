"""Does a looser backfitting tolerance change the single-family MGWR results? (D-194)

    /Users/.../Climate-Resilience---Miami-Dade/.venv/bin/python -I scripts/benefit/module_d_tol_check.py

Compares the saved single-family main model (n10000, tolerance 0.00001, bandwidths
from the search) with the refit at tolerance 0.00002 and the same bandwidths
(n10000_tol2e5). The two differ in tolerance and also in the backfitting path (the
saved model's path includes the search rounds, the refit holds the bandwidths fixed
from round 1), so the differences are an upper bound on the effect of the tolerance.
For every variable: largest and median change in the local coefficients and in their
standard errors (absolute, relative to the standard error, and in percent). For the
flood rate: median, share negative, number of significant local estimates (|t| > 1.96
and after mgwr's multiple-testing correction) in both models.
Writes outputs/benefit/module_d/tol_check.json. Exits with code 1 (so the queue stops)
if the flood result changes: the sign of the median, or the number of significant
local estimates (raw or corrected).
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import paths  # noqa: E402

D = paths.OUT_BENEFIT / "module_d"
SEG = "single_family"


def load(sub):
    j = json.loads((D / sub / f"{SEG}_main.json").read_text())
    return j, pd.read_parquet(D / sub / f"{SEG}_main_local.parquet")


def main():
    (ja, la), (jb, lb) = load("n10000"), load("n10000_tol2e5")
    assert np.allclose(la[["x", "y"]], lb[["x", "y"]]), "different calibration sales"
    names = [c[2:] for c in la.columns if c.startswith("b_")]
    R = {"saved": {"tolerance": ja["mgwr"].get("tolerance", 1e-5), "rounds": ja["mgwr"].get("backfitting_rounds", 33)},
         "refit": {"tolerance": jb["mgwr"]["tolerance"], "rounds": jb["mgwr"]["backfitting_rounds"],
                   "last_change": jb["mgwr"]["backfitting_last_change"]},
         "same_bandwidths": ja["mgwr"]["bandwidths"] == jb["mgwr"]["bandwidths"], "variables": {}}
    worst = 0.0
    for n in names:
        ba, bb, sa, sb = la[f"b_{n}"], lb[f"b_{n}"], la[f"se_{n}"], lb[f"se_{n}"]
        db, ds = (bb - ba).abs(), (sb - sa).abs()
        rel = db / sa                       # coefficient change in standard errors
        sep = ds / sa * 100                 # standard error change in percent
        R["variables"][n] = {"coef_change_max": float(db.max()), "coef_change_median": float(db.median()),
                             "coef_change_in_se_max": float(rel.max()), "coef_change_in_se_median": float(rel.median()),
                             "se_change_pct_max": float(sep.max()), "se_change_pct_median": float(sep.median())}
        worst = max(worst, float(rel.max()))
    R["largest_coef_change_in_se_any_variable"] = worst
    fl = {}
    for k, (j, l) in {"saved": (ja, la), "refit": (jb, lb)}.items():
        t = l.b_FLOOD / l.se_FLOOD
        loc = j["mgwr"]["local"]["FLOOD"]
        fl[k] = {"median_pct_per_unit": float((np.exp(l.b_FLOOD.median()) - 1) * 100),
                 "share_negative": float((l.b_FLOOD < 0).mean()), "significant_raw": int((t.abs() > 1.96).sum()),
                 "significant_corrected": int(round((loc["share_significant_corrected"] or 0) * len(l))),
                 "se_median": float(l.se_FLOOD.median())}
    R["flood"] = fl
    changed = (np.sign(fl["saved"]["median_pct_per_unit"]) != np.sign(fl["refit"]["median_pct_per_unit"])
               or fl["saved"]["significant_raw"] != fl["refit"]["significant_raw"]
               or fl["saved"]["significant_corrected"] != fl["refit"]["significant_corrected"])
    R["flood_result_changed"] = bool(changed)
    R["holdout_error"] = {"saved": ja["mgwr"]["holdout_median_abs_pct_error"], "refit": jb["mgwr"]["holdout_median_abs_pct_error"]}
    (D / "tol_check.json").write_text(json.dumps(R, indent=2))
    print(json.dumps(R, indent=1), flush=True)
    if changed:
        print("FLOOD RESULT CHANGED at the looser tolerance: stopping so the user can decide", flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
