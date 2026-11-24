"""Module B: expected yearly damage (EYD) at every building (prompt 28 Part 2, spec Module B).

    /Users/.../Climate-Resilience---Miami-Dade/.venv/bin/python -I scripts/benefit/module_b_eyd.py

For each building and storm frequency:
1. percent damage to structure and contents from the depth-damage curve for
   its occupancy and foundation (USACE curves, Stage 2, D-138), at the depth
   above the first floor from Module A; salt-water curves where the coastal
   source sets the level or the zone is VE;
2. dollar loss = percent x structure value (+ contents), applied to the
   floors the water reaches for multi-story non-house buildings (D-143);
3. EYD with the trapezoid rule over the loss and annual-chance points, from
   the most frequent storm to the rarest:
       EYD = sum 0.5 x (L_i + L_i+1) x (p_i - p_i+1)
   Loss is 0 at any storm that causes no damage, so the curve starts at the
   most frequent storm with no damage. Rarer storms never do less damage
   than more frequent ones at the same building. The part of the curve
   beyond the 0.2% storm (loss x 0.002) is reported separately.
Range (config): low = low curve band and first floor 1 ft higher for
estimated floors; high = high curve band, whole-building damage for
non-house buildings (D-148) and first floor 1 ft lower; mid = mean curve.
Also: EYD with 1, 2 and 3 ft of sea level rise (mid), EYD from the 2009
effective map (comparison), displacement cost (FEMA standard values,
reported separately) and the provisional NFIP comparison (as Stage 2).

compute() is also used by Module C to rerun only the affected buildings.
Writes data/processed/benefit/module_b_eyd.parquet keyed by fd_id.
"""
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
from baseline_risk import (STORY_CAP, boot_spearman, curve_key, displacement_cost, displacement_rates,  # noqa: E402
                           flooded_share, load_curves, observed_claims, occupied_units)

CONFIG = json.loads((Path(__file__).resolve().parent / "module_config.json").read_text())
EVENTS = [e["name"] for e in CONFIG["events"]]
P = np.array([e["annual_chance"] for e in CONFIG["events"]])
assert (np.diff(P) < 0).all(), "events must run from most frequent to rarest"
MAIN = list(CONFIG["sources"])
COASTAL = [k for k, v in {**CONFIG["sources"], **CONFIG["comparison_sources"]}.items() if v["kind"] == "coastal"]
CASES = {"low": ("low", False, CONFIG["range"]["ffe_shift_estimated_ft"]["low"]),
         "mid": ("mean", False, 0.0),
         "high": ("high", CONFIG["range"]["whole_building_high"], CONFIG["range"]["ffe_shift_estimated_ft"]["high"])}


def levels(A, ev, slr=0.0, coastal_off=None, rain_cut=None, sources=None):
    """Highest water level and whether it is coastal, for one event. coastal_off: bool mask (seawall)."""
    coast = np.full(len(A), -np.inf)
    other = np.full(len(A), -np.inf)
    for name in (sources or MAIN):
        v = np.nan_to_num(A[f"wse_{name}_{ev}"].to_numpy(float), nan=-np.inf)
        if name in COASTAL:
            if name in CONFIG["sea_level_rise_applies_to"] and slr:
                # inside NOAA's sea level rise inundation area the FEMA extent cap is lifted (D-170)
                wide = A[f"slr_{int(slr)}ft"].to_numpy().astype(bool)
                v = np.where(wide, np.nan_to_num(A[f"wse_{name}_uncapped_{ev}"].to_numpy(float), nan=-np.inf), v) + slr
            coast = np.fmax(coast, v)
        else:
            if rain_cut is not None:
                v = v - rain_cut
            other = np.fmax(other, v)
    if coastal_off is not None:
        coast = np.where(coastal_off, -np.inf, coast)
    return np.fmax(coast, other), coast >= other


def event_loss(A, w, is_coast, ffe, cur, stat, whole):
    """Structure + contents loss for one event."""
    ground = A.ground_elev_ft_navd88.to_numpy(float)
    wet = w > ground
    din = w - ffe
    water = np.where(is_coast | A.zone27.eq("VE").to_numpy(), "salt", "fresh")
    fs = np.zeros(len(A))
    fc = np.zeros(len(A))
    egm = np.zeros(len(A), bool)
    if wet.any():
        keys = pd.Series(list(zip(A.occtype.to_numpy(), A.found_type.to_numpy(), water)))
        for (occ, found, wt), idx in keys[wet].groupby(keys[wet]).groups.items():
            occ2, w2 = curve_key(occ, found, wt, cur)
            if (occ2, "structure", w2) not in cur:
                continue
            cs, cc = cur[(occ2, "structure", w2)], cur[(occ2, "contents", w2)]
            ii = np.asarray(idx)
            fs[ii] = np.interp(din[ii], cs["x"], cs[stat])
            fc[ii] = np.interp(din[ii], cc["x"], cc[stat])
            egm[ii] = "EGM" in cc["source"]
    vs = A.val_struct.to_numpy(float)
    base_c = np.where(egm, vs, A.val_cont.to_numpy(float))
    sh = 1.0 if whole else flooded_share(A, din)
    loss = (fs * vs + fc * base_c) * sh
    return np.where(wet, loss, 0.0), np.where(wet, din, -np.inf)


def eyd(L):
    """Trapezoid rule over the events (columns most frequent to rarest); returns (body, tail)."""
    L = np.maximum.accumulate(L, axis=1)
    body = (0.5 * (L[:, :-1] + L[:, 1:]) * (P[:-1] - P[1:])).sum(1)
    return body, L[:, -1] * P[-1]


def compute(A, cur, cases=("low", "mid", "high"), slr=0.0, ffe_add=0.0, coastal_off=None, rain_cut=None,
            remove=None, sources=None, keep_losses=False):
    """EYD for the rows of A under one scenario. ffe_add: ft added to the first floor (array or number);
    coastal_off: function(event, levels_coastal) -> mask of buildings whose coastal level is removed (seawall)."""
    out = {}
    ffe0 = A.ffe_ft_navd88.to_numpy(float) + ffe_add
    est = A.ffe_estimated.to_numpy() == 1
    for case in cases:
        stat, whole, shift = CASES[case]
        ffe = ffe0 + np.where(est, shift, 0.0)
        L = np.zeros((len(A), len(EVENTS)))
        for j, ev in enumerate(EVENTS):
            off = coastal_off(ev, slr) if coastal_off is not None else None
            cut = rain_cut(ev) if rain_cut is not None else None
            w, isc = levels(A, ev, slr, off, cut, sources)
            L[:, j], _ = event_loss(A, w, isc, ffe, cur, stat, whole)
        if remove is not None:
            L[remove] = 0.0
        body, tail = eyd(L)
        out[f"eyd_{case}"] = body
        out[f"eyd_tail_{case}"] = tail
        if keep_losses:
            for j, ev in enumerate(EVENTS):
                out[f"loss_{ev}_{case}"] = L[:, j]
    return pd.DataFrame(out, index=A.index)


def load_a(columns=None):
    A = pd.read_parquet(paths.MODULE_A_PARQUET, columns=columns)
    A["stories"] = A.num_story.clip(1, STORY_CAP)
    return A


def main():
    t0 = time.time()
    A = load_a()
    cur = load_curves()
    R = pd.DataFrame({"fd_id": A.fd_id, "GEOID_tract": A.GEOID_tract})
    base = compute(A, cur, keep_losses=True)
    for c in base.columns:
        R[c] = base[c].to_numpy()
    print(f"baseline done, {time.time() - t0:.0f}s", flush=True)
    for s in CONFIG["sea_level_rise_ft"][1:]:
        r = compute(A, cur, cases=("mid",), slr=float(s))
        R[f"eyd_mid_slr{s}"] = r.eyd_mid.to_numpy()
        R[f"eyd_tail_mid_slr{s}"] = r.eyd_tail_mid.to_numpy()
    for name, cfg in CONFIG["comparison_sources"].items():
        r = compute(A, cur, cases=("low", "mid", "high"), sources=[name] + cfg.get("with", []))
        R[f"eyd_low_{name}"] = r.eyd_low.to_numpy()
        R[f"eyd_high_{name}"] = r.eyd_high.to_numpy()
        R[f"eyd_tail_low_{name}"] = r.eyd_tail_low.to_numpy()
        R[f"eyd_tail_high_{name}"] = r.eyd_tail_high.to_numpy()
        R[f"eyd_mid_{name}"] = r.eyd_mid.to_numpy()
        R[f"eyd_tail_mid_{name}"] = r.eyd_tail_mid.to_numpy()
    # displacement (FEMA standard values, 2021 dollars), mid case, separate from EYD
    rent, once = displacement_rates()
    Ld = np.zeros((len(A), len(EVENTS)))
    for j, ev in enumerate(EVENTS):
        w, _ = levels(A, ev)
        din = np.where(w > A.ground_elev_ft_navd88.to_numpy(), w - A.ffe_ft_navd88.to_numpy(), -1.0)
        Ld[:, j], _ = displacement_cost(A, din, rent, once)
    R["disp_mid"] = eyd(Ld)[0]
    R["residential"] = A.st_damcat.eq("RES").to_numpy()
    R.to_parquet(paths.MODULE_B_PARQUET, index=False)
    print(f"all scenarios done, {time.time() - t0:.0f}s", flush=True)

    # provisional NFIP comparison (as Stage 2, D-140): tract claims per occupied unit, 2025 dollars
    obs, _ = observed_claims()
    units = occupied_units()
    t = R[R.residential].groupby("GEOID_tract")[["eyd_mid", "eyd_tail_mid"]].sum()
    t = t.join(obs[["claims_weighted_annual_2025"]], how="left").join(units.rename("units"), how="left").fillna(0)
    t = t[t.units > 0]
    t["model_per_unit"] = (t.eyd_mid + t.eyd_tail_mid) / t.units
    t["claims_per_unit"] = t.claims_weighted_annual_2025 / t.units
    tot = lambda c: round(float(R[c].sum()) / 1e6, 1)
    S = {"buildings": len(R), "seconds": round(time.time() - t0),
         "eyd_million": {c: tot(c) for c in ["eyd_low", "eyd_mid", "eyd_high", "eyd_tail_mid", "eyd_mid_slr1",
                                             "eyd_mid_slr2", "eyd_mid_slr3", "eyd_mid_map2009", "eyd_tail_mid_map2009",
                                             "eyd_mid_coastal_transect", "eyd_tail_mid_coastal_transect",
                                             "disp_mid"]},
         "eyd_residential_mid_million": round(float(R.loc[R.residential, "eyd_mid"].sum()) / 1e6, 1),
         "buildings_with_eyd": int((R.eyd_mid > 0).sum()),
         "event_loss_million_mid": {ev: tot(f"loss_{ev}_mid") for ev in EVENTS},
         "nfip_check": {
             "claims_annual_2025_million": round(float(obs.claims_weighted_annual_2025.sum()) / 1e6, 1),
             "model_residential_incl_tail_million": round(float((R.loc[R.residential, "eyd_mid"] + R.loc[R.residential, "eyd_tail_mid"]).sum()) / 1e6, 1),
             "tract_spearman": round(float(spearmanr(t.model_per_unit, t.claims_per_unit).statistic), 3),
             "tract_spearman_ci95": boot_spearman(t.model_per_unit, t.claims_per_unit),
             "tracts": int(len(t)),
             "tracts_zero_model_with_claims": int(((t.model_per_unit == 0) & (t.claims_per_unit > 0)).sum())}}
    S["nfip_check"]["ratio_model_to_claims"] = round(S["nfip_check"]["model_residential_incl_tail_million"] /
                                                     S["nfip_check"]["claims_annual_2025_million"], 2)
    t.to_csv(paths.OUT_BENEFIT / "spec_alignment" / "module_b_tract_check.csv")
    (paths.OUT_BENEFIT / "spec_alignment" / "module_b_summary.json").write_text(json.dumps(S, indent=2))
    print(json.dumps(S, indent=1))


if __name__ == "__main__":
    main()
