"""Distance from every building to its nearest inner water (D-202): the input to the seawall waterway rule.

    /Users/.../Climate-Resilience---Miami-Dade/.venv/bin/python -I scripts/benefit/build_water_distance.py

A seawall on the coastal shoreline cannot keep out water that reaches a building from a canal, creek, river or
inner waterway. Module C therefore counts a building as protected only if its nearest open water is the coastal
shoreline (FEMA's transect baseline) behind the wall, not inner water (user, D-202).

Inner water: FEMA 2027 FIRM database water lines (S_Wtr_Ln, already on disk), which include the canals, creeks,
rivers and inner waterways (Indian Creek, Miami River, Little River, Biscayne Canal, Oleta River, Intracoastal
Waterway, Aventura and Miami Beach waterways). FEMA's water areas (S_Wtr_Ar) are almost all ponds and golf lakes
and miss most canals, so they are not used. Left out:
- the open water the coastal study itself faces (Atlantic Ocean, Biscayne Bay, Florida Bay, Card, Little Card,
  Barnes and Long Sound, Manatee Bay, Government Cut): that is the shoreline the wall stands on;
- any water line point within 30 m of the coastal shoreline (the same edge of water, drawn twice);
- closed outlines (ponds and lakes) that do not touch another water line or the shoreline within 30 m: isolated
  ponds are not connected to the sea.
Writes data/processed/benefit/inner_water_distance.parquet (fd_id, inner_water_dist_m, inner_water_name).
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyogrio
from scipy.spatial import cKDTree
from shapely import points

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
import water_levels as wl  # noqa: E402

UTM = 26917
STEP_M = 10.0
SAME_EDGE_M = 30.0
OPEN_COAST = {"ATLANTIC OCEAN", "BISCAYNE BAY", "FLORIDA BAY", "CARD SOUND", "LITTLE CARD SOUND", "BARNES SOUND",
              "LONG SOUND", "MANATEE BAY", "GOVERNMENT CUT"}


def inner_water():
    ln = pyogrio.read_dataframe(paths.FIRM_2027_EXTRACT / "S_Wtr_Ln.shp").to_crs(UTM)
    ln["name"] = ln.WTR_NM.fillna("NP").str.upper().str.strip()
    base = wl.read(paths.FIRM_2027_EXTRACT, "S_Tsct_Basln").to_crs(UTM)
    coast = ln.name.isin(OPEN_COAST)
    ring = ln.geometry.apply(lambda g: g.is_ring)
    openl = ln[~coast & ~ring]
    # a closed outline counts only if it touches open inner water or the shoreline (connected lake), else it is a pond
    near = ln[~coast & ring].copy()
    touch = near.geometry.buffer(SAME_EDGE_M)
    idx_open = set(openl.sindex.query(touch.values, predicate="intersects")[0])
    idx_base = set(base.sindex.query(touch.values, predicate="intersects")[0])
    connected = near.iloc[sorted(idx_open | idx_base)]
    keep = pd.concat([openl, connected])
    pts, names = [], []
    for g, nm in zip(keep.geometry, keep.name):
        n = max(2, int(g.length // STEP_M) + 1)
        p = [g.interpolate(t) for t in np.linspace(0, g.length, n)]
        pts.extend((q.x, q.y) for q in p)
        names.extend([nm] * len(p))
    pts = np.array(pts)
    names = np.array(names)
    d_base = base.union_all().distance(points(pts))
    far = d_base > SAME_EDGE_M
    info = {"water_lines": int(len(ln)), "open_coast_lines": int(coast.sum()), "inner_open_lines": int(len(openl)),
            "closed_outlines": int((~coast & ring).sum()), "connected_lakes_kept": int(len(connected)),
            "points": int(far.sum()), "points_dropped_on_shoreline": int((~far).sum())}
    return pts[far], names[far], info


def main():
    pts, names, info = inner_water()
    A = pd.read_parquet(paths.MODULE_A_PARQUET, columns=["fd_id", "x_utm", "y_utm", "shore_dist_m"])
    d, i = cKDTree(pts).query(np.c_[A.x_utm, A.y_utm])
    out = pd.DataFrame({"fd_id": A.fd_id, "inner_water_dist_m": d.astype("float32"), "inner_water_name": names[i]})
    out.to_parquet(paths.INNER_WATER_PARQUET, index=False)
    near_coast = A.shore_dist_m.to_numpy() <= 2000
    info["buildings"] = int(len(A))
    info["within_2km_of_shoreline_where_inner_water_is_nearer"] = int((near_coast & (d < A.shore_dist_m.to_numpy())).sum())
    info["within_2km_of_shoreline"] = int(near_coast.sum())
    (paths.OUT_BENEFIT / "spec_alignment" / "inner_water_summary.json").write_text(json.dumps(info, indent=2))
    print(json.dumps(info, indent=1))


if __name__ == "__main__":
    main()
