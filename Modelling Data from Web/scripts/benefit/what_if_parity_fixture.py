"""Admin Flood What-If: Python answers for the browser parity test (D-200).

    /Users/.../Climate-Resilience---Miami-Dade/.venv/bin/python -I scripts/benefit/what_if_parity_fixture.py

Reruns every Part 2 project (D-197, D-198) directly in Module C and writes the inputs and Python's damage
avoided (low, middle, high) to outputs/admin_data/what_if/parity_fixture.json (private, git-ignored):
- typical seawall, 10 placements, crest +6 and +8 ft;
- typical FEMA elevation, 10 placements (most damaged home), plus the 5th and 10th home, and the
  Elevate Florida case (10 homes); raise 3 ft;
- real projects: shoreline seawalls that run (stated or assumed crest, and +8 ft), port bulkheads,
  and the Miami Beach elevation SCALER-0684;
- the two coastline-scan stretches with the largest losses avoided.
src/admin/viz/whatif/whatIfParity.test.js reruns each in the browser engine.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from shapely.ops import substring

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
import typical_projects_part2 as tp  # noqa: E402
from progress import Progress  # noqa: E402

OUT = paths.ADMIN_WHAT_IF_DIR / "parity_fixture.json"


def main():
    tp.P = Progress("what-if parity fixture")
    E = tp.Engine()
    M, A = E.M, E.M.A
    runs = []

    def wall(rid, line, crest):
        # also the reason for every flooding building near the wall, for the explanation layer parity check (D-204)
        t, r = M.seawall_reasons(line, crest)
        runs.append({"id": rid, "kind": "seawall", "line": [[float(a), float(b)] for a, b in line], "crest_ft": float(crest),
                     "avoided": r["losses_avoided_per_year"], "buildings_affected_python": r["buildings_affected"],
                     "reasons": [[int(f), str(q)] for f, q in zip(t.fd_id, t.reason)]})

    def elev(rid, ids, raise_ft=tp.RAISE):
        r, _ = M.elevate(ids, raise_ft)
        runs.append({"id": rid, "kind": "elevation", "fd_ids": [int(i) for i in ids], "raise_ft": float(raise_ft),
                     "avoided": r["losses_avoided_per_year"], "buildings_affected_python": r["buildings_affected"]})

    # typical seawall placements, rebuilt exactly as in Part 2
    L = 550 * tp.FT
    st = tp.seawall_sites(E, L)
    pick = tp.choose(st, "eyd_on_stretch", "place")
    lines = {}
    for n, (_, p) in enumerate(pick.iterrows(), 1):
        g = E.base.geometry.iloc[int(p.line)]
        seg = substring(g, p.station - L / 2, p.station + L / 2)
        lines[f"S{n}"] = [tp.TO_LL.transform(*c) for c in seg.coords]
    for sid, line in lines.items():
        for crest in (6.0, 8.0):
            wall(f"typical {sid} +{crest:g} ft", line, crest)
    # two strongest coastline-scan stretches
    scan = pd.read_csv(tp.OUT / "part2_seawall_scan.csv").sort_values("avoided_mid", ascending=False).head(2)
    for k, (_, p) in enumerate(scan.iterrows(), 1):
        g = E.base.geometry.iloc[int(p.line)]
        seg = substring(g, p.station - L / 2, p.station + L / 2)
        wall(f"scan best {k} +6 ft", [tp.TO_LL.transform(*c) for c in seg.coords], tp.CREST)
    # typical elevation placements
    b = pd.read_csv(tp.OUT / "part2_typical_placements.csv", dtype={"tract": str})
    fema = b[b.case.str.startswith("typical elevation")]
    for _, p in fema.iterrows():
        mask = A.GEOID_tract.to_numpy() == p.tract
        ids, _ = E.top_homes(mask, 1)
        elev(f"typical {p.id} home 1", ids)
        for rank in (5, 10):
            ids, _ = E.top_homes(mask, 1, start=rank - 1)
            elev(f"typical {p.id} home {rank}", ids)
        ids, _ = E.top_homes(mask, 10)
        elev(f"Elevate Florida {p.id} 10 homes", ids)
    # real projects (Part 2A)
    d = pd.read_csv(tp.OUT / "part1_projects.csv")
    s = d[d.type.eq("seawall") & d.location_usable & d.cost_usable].copy()
    s["group"] = s.subtype.fillna("shoreline")
    for _, p in s[s.group.isin(["shoreline", "port bulkhead"])].iterrows():
        x, y = tp.TO_UTM.transform(p.Longitude, p.Latitude)
        want_ft = p.length_ft if pd.notna(p.length_ft) else p.cost_2025 / tp.COST_PER_FT
        line, dist, _, _ = E.wall_line(x, y, want_ft * tp.FT)
        if dist > tp.MAX_SNAP_M:
            continue
        crest = p.crest_ft_navd if pd.notna(p.crest_ft_navd) else tp.CREST
        wall(f"real {p.Project_ID} +{crest:g} ft", line, crest)
        if crest != 8.0:
            wall(f"real {p.Project_ID} +8 ft", line, 8.0)
    ids, _ = E.top_homes(E.place == "Miami Beach", 2)
    elev("real SCALER-0684 2 homes", ids)
    # Examples button in the view: typical seawall in Miami Beach (S2), typical elevation in Miami Shores (E4,
    # most damaged home) and a low-damage placement (typical elevation in Brownsville, E8)
    def home(eid):
        ids = next(r["fd_ids"] for r in runs if r["id"] == f"typical {eid} home 1")
        row = A[A.fd_id.isin(ids)].iloc[0]
        return {"fd_ids": ids, "tiles": [f"{int(row.x_utm // 2000)}_{int(row.y_utm // 2000)}"]}
    place = dict(zip(b.id, b.place))
    seawall_place = dict(zip([f"S{i}" for i in range(1, 11)], pick.place))
    ex = [{"id": "S2", "kind": "seawall", "label": f"Typical seawall, {seawall_place['S2']} (high damage)", "line": [[float(a), float(c)] for a, c in lines["S2"]], "crest_ft": 6.0},
          {"id": "E4", "kind": "elevation", "label": f"Typical elevation, {place['E4']} (high damage)", "raise_ft": 3.0, **home("E4")},
          {"id": "E8", "kind": "elevation", "label": f"Typical elevation, {place['E8']} (low damage)", "raise_ft": 3.0, **home("E8")}]
    (paths.ADMIN_WHAT_IF_DIR / "examples.json").write_text(json.dumps(ex, indent=1))
    OUT.write_text(json.dumps({"about":"Python Module C answers for the browser parity test (D-200). Private, not committed.",
                               "runs": runs}, indent=1, default=float))
    print(f"{len(runs)} runs written to {OUT}")
    tp.P.finish()


if __name__ == "__main__":
    main()
