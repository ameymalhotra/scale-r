"""Copy the ML dashboard export into the admin Scenario view's data (src/admin/viz/scenario/data/).

    ../.venv/bin/python scripts/website/build_scenario_data.py      (from Modelling Data from Web/)

Reads outputs/ml/dashboard/{tracts,scores,scenarios}.json (written by
scripts/ml/stage2b_map_model.py and scripts/ml/scenarios.py) and the TIGER 2024
tract boundaries, and writes:
  src/admin/viz/scenario/data/tracts.geojson  tract outlines (land only, simplified) with
                                    the current-state attributes
  src/admin/viz/scenario/data/scenarios.json  per-scenario county summary and per-tract
                                    arrays, in the same tract order
  src/admin/viz/scenario/data/scores.json     model scores and definitions for the About panel
Nothing is hand-edited; rerun after the ML pipeline. No dollar predictions are
written (T5 is unreliable, D-088); observed sited dollars per resident are, so the
page can recompute the actual-investment gap for interventions.
"""
import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import shapely

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import paths  # noqa: E402

DASH = paths.OUT_ML / "dashboard"
# admin panel only: the public site never imports or links this view (D-094)
OUT = paths.REPO / "src" / "admin" / "viz" / "scenario" / "data"
SIMPLIFY_M = 25
KEEP = ["GEOID", "jurisdiction", "low_pop_flag", "population", "T1_observed", "T2_planned_projects",
        "pred_likelihood", "interval_lo", "interval_hi", "need_pct", "pred_pct", "vulnerability_rc1",
        "sited_dollars_per_resident_observed", "sited_pct", "gap_actual", "gap_expected",
        "high_need_no_sited_project", "driver1", "driver2", "driver3", "slr_3ft_pop_exposed",
        "surge_cat3_any_pop_exposed", "surge_cat4_any_pop_exposed", "heat_p95_pop_exposed"]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    tracts = json.loads((DASH / "tracts.json").read_text())
    scen = json.loads((DASH / "scenarios.json").read_text())
    scores = json.loads((DASH / "scores.json").read_text())
    by = {r["GEOID"]: r for r in tracts}
    order = [r["GEOID"] for r in tracts]

    u = gpd.read_file(f"zip://{paths.BOUNDARY_DIR / 'tl_2024_12_tract.zip'}", where="COUNTYFP='086'")
    u = u[u.GEOID.isin(by)].to_crs(6346)
    w = gpd.read_file(f"zip://{paths.BOUNDARY_DIR / 'tl_2024_12086_areawater.zip'}").to_crs(6346)
    water = shapely.union_all(w[w.AWATER > 0].geometry.values)
    land = shapely.difference(u.geometry.values, water)
    land = np.where(shapely.is_empty(land), u.geometry.values, land)
    land = shapely.simplify(land, SIMPLIFY_M, preserve_topology=True)
    g = gpd.GeoDataFrame({"GEOID": u.GEOID.values}, geometry=land, crs=6346).to_crs(4326)
    feats = []
    for gid, geom in zip(g.GEOID, g.geometry):
        props = {k: by[gid].get(k) for k in KEEP}
        props["i"] = order.index(gid)
        gj = json.loads(shapely.to_geojson(shapely.set_precision(geom, 1e-5)))
        feats.append({"type": "Feature", "id": props["i"], "properties": props, "geometry": gj})
    assert len(feats) == len(order), "every tract needs an outline"
    (OUT / "tracts.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats},
                                                   separators=(",", ":")))

    # scenarios: drop the GEOID column and keep the tract order of tracts.json
    out = []
    for s in scen["scenarios"]:
        cols = s["columns"]
        rows = {r[0]: r for r in s["tracts"]}
        arr = {c: [rows[gid][j] for gid in order] for j, c in enumerate(cols) if c != "GEOID"}
        out.append({k: s[k] for k in ("id", "family", "label", "hypothetical")} | {"summary": s["summary"], **arr})
    (OUT / "scenarios.json").write_text(json.dumps({"meta": scen["meta"], "order": order, "scenarios": out},
                                                   separators=(",", ":")))
    (OUT / "scores.json").write_text(json.dumps(scores, indent=1))
    for f in sorted(OUT.iterdir()):
        print(f"{f.name}: {f.stat().st_size / 1024:,.0f} KB")


if __name__ == "__main__":
    main()
