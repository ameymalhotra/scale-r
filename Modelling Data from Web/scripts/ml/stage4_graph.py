"""Stage 4, A1: tract adjacency graph and BYM2 scaling factor.

    bash scripts/ml/run_ml.sh scripts/ml/stage4_graph.py      (from Modelling Data from Web/)

Queen contiguity on the TIGER 2024 tract polygons (EPSG:6346) for the 697
training tracts (the Stage 2 frame). Disconnected components (islands, or
tracts cut off when the one tract under 100 residents is left out) are joined
to the nearest tract outside the component, by the shortest distance between
polygons, until one component remains. Every added link is listed.

The BYM2 scaling factor (Riebler et al. 2016) is the geometric mean of the
diagonal of the generalized inverse of the ICAR precision Q = D - W on the
connected graph, under the sum-to-zero constraint. Scaling Q by it makes the
structured effect's marginal variance about 1, so the BYM2 mixing parameter
reads as a share of variance.

Outputs: outputs/ml/stage4/graph_edges.csv, graph_added_links.csv, graph_summary.json
"""
import json

import geopandas as gpd
import numpy as np
import pandas as pd
from libpysal.weights import Queen
from scipy.sparse.csgraph import connected_components

import ml_common as C

OUT = C.paths.OUT_ML / "stage4"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    t = C.load_table()
    tr = t[C.train_mask(t)].reset_index(drop=True)
    u = gpd.read_file(f"zip://{C.paths.BOUNDARY_DIR / 'tl_2024_12_tract.zip'}", where="COUNTYFP='086'").to_crs(6346)
    u = u.set_index("GEOID").loc[tr.GEOID].reset_index()
    w = Queen.from_dataframe(u, use_index=False, silence_warnings=True)
    n = len(u)
    A = np.zeros((n, n), dtype=bool)
    for i, nb in w.neighbors.items():
        A[i, nb] = True
    A = A | A.T
    ncomp0, lab0 = connected_components(A, directed=False)
    sizes0 = pd.Series(lab0).value_counts().sort_values(ascending=False)
    print(f"queen contiguity: {n} tracts, {int(A.sum() // 2)} links, {ncomp0} components; "
          f"sizes {sizes0.tolist()[:10]}{' ...' if len(sizes0) > 10 else ''}; tracts with no neighbour {int((A.sum(1) == 0).sum())}")
    added = []
    geoms = u.geometry.values
    while True:
        ncomp, lab = connected_components(A, directed=False)
        if ncomp == 1:
            break
        main_comp = pd.Series(lab).value_counts().idxmax()
        # join the smallest component to its nearest tract outside it
        small = pd.Series(lab).value_counts().idxmin()
        inside = np.flatnonzero(lab == small)
        outside = np.flatnonzero(lab != small)
        best = (np.inf, None, None)
        for i in inside:
            d = geoms[outside].distance(geoms[i]) if hasattr(geoms[outside], "distance") else \
                gpd.GeoSeries(geoms[outside]).distance(geoms[i]).to_numpy()
            d = np.asarray(d)
            j = int(np.argmin(d))
            if d[j] < best[0]:
                best = (float(d[j]), int(i), int(outside[j]))
        dist, i, j = best
        A[i, j] = A[j, i] = True
        added.append({"from_GEOID": u.GEOID[i], "from_jurisdiction": tr.jurisdiction[i], "component_size": len(inside),
                      "to_GEOID": u.GEOID[j], "to_jurisdiction": tr.jurisdiction[j], "distance_m": round(dist, 1),
                      "joined_main_component": bool(lab[j] == main_comp)})
    add = pd.DataFrame(added)
    print(f"added {len(add)} links; components after: 1")
    if len(add):
        print(add.to_string(index=False))
    # BYM2 scaling factor
    W = A.astype(float)
    D = np.diag(W.sum(1))
    Q = D - W
    Q_pert = Q + np.eye(n) * max(np.diag(Q)) * np.sqrt(np.finfo(float).eps)
    Qinv = np.linalg.inv(Q_pert)
    # sum-to-zero constraint (conditioning on the constraint, as INLA does)
    ones = np.ones((n, 1))
    Qinv_c = Qinv - Qinv @ ones @ np.linalg.inv(ones.T @ Qinv @ ones) @ ones.T @ Qinv
    scaling = float(np.exp(np.mean(np.log(np.diag(Qinv_c)))))
    print(f"BYM2 scaling factor (geometric mean of the constrained ICAR marginal variances): {scaling:.4f}")
    ii, jj = np.nonzero(np.triu(A))
    pd.DataFrame({"i": ii, "j": jj, "GEOID_i": u.GEOID.values[ii], "GEOID_j": u.GEOID.values[jj]}).to_csv(
        OUT / "graph_edges.csv", index=False)
    add.to_csv(OUT / "graph_added_links.csv", index=False)
    pd.DataFrame({"i": range(n), "GEOID": u.GEOID}).to_csv(OUT / "graph_nodes.csv", index=False)
    summ = {"tracts": n, "queen_links": int(A.sum() // 2) - len(add), "components_before": int(ncomp0),
            "component_sizes_before": sizes0.tolist(), "tracts_without_neighbour_before": int(((W.sum(1) == 0)).sum()),
            "links_added": len(add), "components_after": 1, "total_links": int(A.sum() // 2),
            "mean_neighbours": float(W.sum(1).mean()), "min_neighbours": int(W.sum(1).min()),
            "bym2_scaling_factor": scaling}
    (OUT / "graph_summary.json").write_text(json.dumps(summ, indent=1))
    print(json.dumps(summ))


if __name__ == "__main__":
    main()
