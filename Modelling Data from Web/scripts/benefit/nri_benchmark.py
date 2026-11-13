"""Benchmark our expected yearly damage against FEMA's National Risk Index (prompt 28 follow-up, D-177).

    /Users/.../Climate-Resilience---Miami-Dade/.venv/bin/python -I scripts/benefit/nri_benchmark.py

NRI (December 2025, census tracts): expected annual loss to buildings from
coastal flooding (CFLD_EALB) and inland flooding (IFLD_EALB). Hurricane wind
is excluded. NRI counts building value only (no contents), so our side is
shown both as structure + contents and as structure only.
Versions compared (nothing tuned):
- anchored: Module B main (D-173/D-174), 10% to 0.2% storms plus the part beyond;
- frequent: anchored, storms 10% to 2% only;
- stage2: Stage 2 benchmark.
Ranking: Spearman correlation across tracts of loss per dollar of building
value (NRI BUILDVALUE; ours: NSI structure value), and of tract totals.
Writes outputs/benefit/spec_alignment/nri_benchmark.json and nri_benchmark_tracts.csv.
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
from baseline_risk import boot_spearman  # noqa: E402
from module_b_eyd import EVENTS, P, CASES, compute, levels, event_loss, load_a, load_curves, eyd  # noqa: E402

OUT = paths.OUT_BENEFIT / "spec_alignment"


def structure_only(A, cur):
    """Anchored mid EYD counting structure damage only (NRI counts buildings, not contents)."""
    A2 = A.copy()
    A2["val_cont"] = 0.0
    # EGM curves put contents on structure value; zero those too by zeroing contents curves below
    stat, whole, shift = CASES["mid"]
    L = np.zeros((len(A2), len(EVENTS)))
    cur2 = {k: (dict(v, mean=np.zeros_like(v["mean"])) if k[1] == "contents" else v) for k, v in cur.items()}
    for j, ev in enumerate(EVENTS):
        w, isc = levels(A2, ev)
        L[:, j], _ = event_loss(A2, w, isc, A2.ffe_ft_navd88.to_numpy(float), cur2, stat, whole)
    body, tail = eyd(L)
    return body + tail


def main():
    nri = pd.read_csv(paths.NRI_CSV, low_memory=False, dtype={"TRACTFIPS": str})
    nri["GEOID_tract"] = nri.TRACTFIPS.str.zfill(11)
    nri = nri.set_index("GEOID_tract")[["CFLD_EALB", "IFLD_EALB", "BUILDVALUE"]].fillna(0)
    nri["FLOOD_EALB"] = nri.CFLD_EALB + nri.IFLD_EALB
    A = load_a()
    B = pd.read_parquet(paths.MODULE_B_PARQUET)
    L = np.maximum.accumulate(B[[f"loss_{e}_mid" for e in EVENTS]].to_numpy(), axis=1)
    freq = (0.5 * (L[:, :-1] + L[:, 1:]) * (P[:-1] - P[1:]))[:, :2].sum(1)
    S2 = pd.read_parquet(paths.EAD_BUILDINGS_PARQUET, columns=["fd_id", "ead_mid_slr0", "ead_disp_slr0"]).set_index("fd_id").reindex(B.fd_id)
    V = pd.DataFrame({"GEOID_tract": B.GEOID_tract.to_numpy(),
                      "anchored": (B.eyd_mid + B.eyd_tail_mid).to_numpy(),
                      "anchored_structure_only": structure_only(A, load_curves()),
                      "frequent": freq,
                      "stage2": (S2.ead_mid_slr0 - S2.ead_disp_slr0).fillna(0).to_numpy(),
                      "val_struct": A.val_struct.to_numpy()})
    T = V.groupby("GEOID_tract").sum().join(nri, how="inner")
    T.to_csv(OUT / "nri_benchmark_tracts.csv")
    R = {"nri_version": "December 2025", "tracts": len(T),
         "nri_million": {k: round(float(nri[k].sum()) / 1e6, 1) for k in ["CFLD_EALB", "IFLD_EALB", "FLOOD_EALB"]},
         "ours_million": {k: round(float(V[k].sum()) / 1e6, 1) for k in ["anchored", "anchored_structure_only", "frequent", "stage2"]},
         "building_value_billion": {"nri": round(float(nri.BUILDVALUE.sum()) / 1e9, 1), "nsi": round(float(V.val_struct.sum()) / 1e9, 1)},
         "ranking": {}}
    for v in ["anchored", "anchored_structure_only", "frequent", "stage2"]:
        R["ranking"][v] = {}
        for ref in ["FLOOD_EALB", "CFLD_EALB", "IFLD_EALB"]:
            ours, theirs = T[v] / T.val_struct.replace(0, np.nan), T[ref] / T.BUILDVALUE.replace(0, np.nan)
            ok = ours.notna() & theirs.notna()
            R["ranking"][v][ref] = {"spearman_rate": round(float(spearmanr(ours[ok], theirs[ok]).statistic), 3),
                                    "spearman_rate_ci95": boot_spearman(ours[ok], theirs[ok], n=500),
                                    "spearman_totals": round(float(spearmanr(T[v], T[ref]).statistic), 3),
                                    "ratio_totals": round(float(T[v].sum() / max(T[ref].sum(), 1)), 2)}
    # where the two disagree most: top tenth of tracts by each
    for v in ["anchored", "frequent"]:
        top_ours = set(T[v].nlargest(len(T) // 10).index)
        top_nri = set(T.FLOOD_EALB.nlargest(len(T) // 10).index)
        R[f"top_tenth_overlap_{v}"] = round(len(top_ours & top_nri) / max(len(top_nri), 1), 3)
    (OUT / "nri_benchmark.json").write_text(json.dumps(R, indent=2))
    print(json.dumps(R, indent=1))


if __name__ == "__main__" and len(sys.argv) == 1:
    main()


def nri_vs_claims():
    """Context check: how NRI itself ranks against NFIP claims per occupied home (same tracts as D-174)."""
    from baseline_risk import observed_claims, occupied_units
    T = pd.read_csv(OUT / "nri_benchmark_tracts.csv", dtype={"GEOID_tract": str}).set_index("GEOID_tract")
    obs, _ = observed_claims()
    u = occupied_units()
    T = T.join(obs.claims_weighted_annual_2025.rename("claims")).join(u.rename("units")).fillna(0)
    T = T[T.units >= 50]
    r = {}
    for c in ["FLOOD_EALB", "CFLD_EALB", "IFLD_EALB", "anchored", "frequent", "stage2"]:
        r[c] = round(float(spearmanr(T[c] / T.units, T.claims / T.units).statistic), 3)
    j = json.loads((OUT / "nri_benchmark.json").read_text())
    j["spearman_with_claims_per_home"] = r
    (OUT / "nri_benchmark.json").write_text(json.dumps(j, indent=2))
    print(r)


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "claims":
    nri_vs_claims()
