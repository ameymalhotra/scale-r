"""Sensitivity, not a typical project (D-203): a closed seawall system along the Miami Beach bayfront.

    /Users/.../Climate-Resilience---Miami-Dade/.venv/bin/python -I scripts/benefit/closed_system_miami_beach.py

The wall runs the whole 13.1 km FEMA coastal shoreline on the bay side of Miami Beach's main island (about 63rd
Street to South Beach) and closes the three waterway mouths it crosses (Biscayne Waterway, Indian Creek, and an
unnamed waterway at the north end), as backflow valves, gates or canal walls would. With the mouths closed, water
cannot come in through the canals and creeks, so Module C's waterway rule and 1 km cap (D-202) are switched off
for this run only; every building whose line to its nearest coastal shoreline point crosses the wall counts.
Buildings whose nearest coastal shoreline is the Atlantic side are not protected (the ocean side stays open).
Compared with the same wall with the mouths left open (rule on). Cost: $3,500 per foot of wall (Part 1); the
mouth closures are not costed, so benefit per dollar is an upper bound. Writes
outputs/benefit/typical_projects/closed_system_miami_beach.json.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
import module_c_projects as mc  # noqa: E402
import typical_projects_part2 as tp  # noqa: E402
import water_levels as wl  # noqa: E402

BAY_LINE_M = 13082        # the bay-side baseline line of Miami Beach's main island


def main():
    base = wl.read(paths.FIRM_2027_EXTRACT, "S_Tsct_Basln").to_crs(26917)
    bay = base[base.length.round() == BAY_LINE_M].geometry.iloc[0]
    line = [tp.TO_LL.transform(*c) for c in bay.coords]
    length_ft = bay.length / tp.FT
    cost = length_ft * tp.COST_PER_FT
    M = mc.Model()
    cfg = mc.CONFIG["projects"]["seawall"]
    keep = dict(cfg)
    out = {"wall_length_ft": round(length_ft), "cost": round(cost), "mouths_closed": ["Biscayne Waterway", "Indian Creek", "unnamed waterway, north end"],
           "note": "Sensitivity, not a typical project. Mouth closures not costed: benefit per dollar is an upper bound."}
    for label, rule in (("mouths_closed", False), ("mouths_open", True)):
        cfg["inner_water_rule"] = rule
        cfg["max_distance_from_wall_m"] = keep["max_distance_from_wall_m"] if rule else None
        for crest in (6.0, 8.0):
            r, per = M.seawall(line, crest)
            red = per.eyd_mid_before - per.eyd_mid_after
            prot = per.fd_id[red > 0]
            res = float(M.A.set_index("fd_id").residents_night.reindex(prot).sum())
            a = r["losses_avoided_per_year"]
            out[f"{label}_{crest:g}ft"] = {"avoided_low": round(a["low"]), "avoided_mid": round(a["mid"]), "avoided_high": round(a["high"]),
                                           "buildings_protected": int(len(prot)), "residents_protected": round(res),
                                           "bcr_7pct": round(tp.ratio("seawall", a["mid"], cost), 3), "bcr_3pct": round(tp.ratio("seawall", a["mid"], cost, tp.RATE_LOW), 3),
                                           "bcr_7pct_low_high": [round(tp.ratio("seawall", a["low"], cost), 3), round(tp.ratio("seawall", a["high"], cost), 3)],
                                           "eyd_before_mid": round(r["eyd_baseline"]["mid"])}
    cfg.clear(); cfg.update(keep)
    (tp.OUT / "closed_system_miami_beach.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
