"""Carrying FEMA 2027 water levels to buildings (prompt 28 Part 2, D-170).

Shared by compare_water_levels.py (method comparison) and module_a_depth.py.
All distances are in metres in NAD83 / UTM 17N (EPSG:26917); elevations are
feet NAVD88. Event names: p10, p04, p02, p01, p002 (annual chance 10%, 4%,
2%, 1%, 0.2%).

Coastal (FEMA coastal study, 218 transects, still-water elevations):
- "nearest": the still-water level of the nearest transect line;
- "alongshore": the building is projected onto the nearest transect
  baseline (the shoreline the transects start from) and the level is
  interpolated linearly between the two transects on that baseline that
  bracket it (nearest transect where it is beyond the end ones).
Rainfall and canal (XP-SWMM, C-8 and C-9 basins only):
- "nearest": the nearest model node;
- "subbasin": the node that drains the building's own subbasin
  (S_Subbasins.NODE_ID); nearest node if the subbasin node has no levels;
- "idw3": inverse-distance (squared) average of the 3 nearest nodes.
"""
import numpy as np
import pandas as pd
import pyogrio
from shapely.geometry import Point
from shapely.strtree import STRtree

EVENTS = {"10 Percent Chance": "p10", "4 Percent Chance": "p04", "2 Percent Chance": "p02",
          "1 Percent Chance": "p01", "0.2 Percent Chance": "p002"}
EV = list(EVENTS.values())
CRS = "EPSG:26917"


def read(ext, name, geometry=True):
    if geometry:
        g = pyogrio.read_dataframe(ext / f"{name}.shp")
        return g.to_crs(CRS)
    return pyogrio.read_dataframe(ext / f"{name}.dbf", read_geometry=False)


def transects(ext):
    t = read(ext, "S_Cst_Tsct_Ln")
    e = read(ext, "L_Cst_Tsct_Elev", geometry=False)
    w = e.pivot_table(index="TRAN_LN_ID", columns="EVENT_TYP", values="WSEL_START").rename(columns=EVENTS)[EV]
    t = t.merge(w, left_on="TRAN_LN_ID", right_index=True, how="inner")
    return t


def nodes(ext):
    n = read(ext, "S_Nodes")
    s = read(ext, "L_Summary_Elevations", geometry=False)
    s = s[s.WSEL > -8000]
    w = s.pivot_table(index="NODE_ID", columns="EVENT_TYP", values="WSEL").rename(columns=EVENTS)[EV]
    return n.merge(w, left_on="NODE_ID", right_index=True, how="inner")


def coastal_nearest(pts, t):
    tree = STRtree(t.geometry.values)
    idx, dist = tree.query_nearest(pts, return_distance=True, all_matches=False)
    order = np.argsort(idx[0])
    j = idx[1][order]
    out = pd.DataFrame(t[EV].to_numpy()[j], columns=EV)
    out["tsct_dist_m"] = dist[order]
    out["tsct_id"] = t.TRAN_LN_ID.to_numpy()[j]
    return out


def coastal_alongshore(pts, t, ext):
    base = read(ext, "S_Tsct_Basln")
    base = base[base.TBASELN_ID.isin(t.TBASELN_ID.unique())].reset_index(drop=True)
    # station of each transect along its own baseline: where the transect meets (or comes closest to) it
    bl = base.set_index("TBASELN_ID").geometry
    st = []
    for _, r in t.iterrows():
        g = bl.get(r.TBASELN_ID)
        if g is None:
            st.append(np.nan)
            continue
        x = r.geometry.intersection(g)
        p = x if (not x.is_empty and x.geom_type == "Point") else r.geometry.interpolate(r.geometry.project(g.centroid))
        st.append(g.project(p if p.geom_type == "Point" else p.centroid))
    t = t.assign(station=st)
    tree = STRtree(base.geometry.values)
    idx = tree.query_nearest(pts, all_matches=False)
    order = np.argsort(idx[0])
    bj = idx[1][order]
    out = np.full((len(pts), len(EV)), np.nan)
    near = coastal_nearest(pts, t)
    for k in np.unique(bj):
        g = base.geometry.iloc[k]
        bid = base.TBASELN_ID.iloc[k]
        tt = t[(t.TBASELN_ID == bid) & t.station.notna()].sort_values("station")
        m = np.flatnonzero(bj == k)
        if len(tt) < 2:
            out[m] = near.loc[m, EV].to_numpy()
            continue
        s = np.array([g.project(p) for p in pts[m]])
        for c, ev in enumerate(EV):
            out[m, c] = np.interp(s, tt.station.to_numpy(), tt[ev].to_numpy())   # flat beyond the end transects
    o = pd.DataFrame(out, columns=EV)
    o["tsct_dist_m"] = near.tsct_dist_m
    return o


def rain_nearest(pts, n):
    tree = STRtree(n.geometry.values)
    idx, dist = tree.query_nearest(pts, return_distance=True, all_matches=False)
    order = np.argsort(idx[0])
    j = idx[1][order]
    out = pd.DataFrame(n[EV].to_numpy()[j], columns=EV)
    out["node_dist_m"] = dist[order]
    out["node_id"] = n.NODE_ID.to_numpy()[j]
    return out


def rain_subbasin(pts, n, sub_node):
    """sub_node: the NODE_ID of each building's subbasin (NaN outside the C-8 and C-9 subbasins)."""
    near = rain_nearest(pts, n)
    w = n.set_index("NODE_ID")[EV]
    w = w[~w.index.duplicated()]
    own = w.reindex(pd.Series(sub_node).to_numpy())
    has = own.notna().all(axis=1).to_numpy()
    out = near.copy()
    out.loc[has, EV] = own.to_numpy()[has]
    out["node_source"] = np.where(has, "own_subbasin", "nearest")
    return out


def rain_idw(pts, n, k=3):
    xy = np.c_[[p.x for p in pts], [p.y for p in pts]]
    nx = np.c_[n.geometry.x.to_numpy(), n.geometry.y.to_numpy()]
    from scipy.spatial import cKDTree
    d, j = cKDTree(nx).query(xy, k=k)
    w = 1.0 / np.maximum(d, 1.0) ** 2
    vals = n[EV].to_numpy()
    out = np.einsum("ik,ikc->ic", w, vals[j]) / w.sum(1, keepdims=True)
    o = pd.DataFrame(out, columns=EV)
    o["node_dist_m"] = d[:, 0]
    return o


def points(df):
    from pyproj import Transformer
    e, n = Transformer.from_crs("EPSG:4269", CRS, always_xy=True).transform(df.lon.values, df.lat.values)
    return np.array([Point(a, b) for a, b in zip(e, n)], dtype=object), e, n
