"""Prompt 29 Part 2: run the engine on real and typical projects (D-197).

    /Users/.../Climate-Resilience---Miami-Dade/.venv/bin/python -I scripts/benefit/typical_projects_part2.py

A. Real projects at their real locations (from Part 1, D-196):
   - the 12 shoreline seawalls with a clean cost and a usable location; the
     5 PortMiami bulkheads and 4 canal or lake edges are run and shown
     separately;
   - wall alignment: the FEMA 2027 coastal shoreline (transect baseline,
     the line Module A measures from) at the point nearest the project,
     centred on that point; length as stated, otherwise cost / $3,500 per
     foot, limited to the shoreline line available there (user, D-197);
     crest +6.0 ft NAVD88 unless stated (assumption);
   - the one clear elevation project (SCALER-0684, Miami Beach, 2 homes):
     the homes are not named, so the 2 single-family homes with the highest
     expected yearly damage in Miami Beach are raised.
B. Typical project placed in 10 locations each (mix of high, middle and
   low expected damage, different jurisdictions; coastal and inland for
   elevation; seawalls are coastal by nature):
   - seawall: 550 ft, crest +6.0 ft NAVD88, $1.76M (middle half $0.56M to
     $2.74M), Part 1;
   - elevation, FEMA case: median South Florida HMA elevation project
     (homes and cost per home from typical_elevation_hma.py); elevation,
     Elevate Florida case: 10 homes at about $267,000 (assumption). In each
     location the homes with the highest expected yearly damage are raised
     (user, D-197), by 3 ft (Module C default, assumption).
Benefit per dollar = present value of losses avoided over the project life
/ (cost + present value of maintenance). FEMA BCA: 7% discount rate for new
BCAs (BCA Toolkit help content, Aug 2025, PDF page 59); project useful life
50 years for floodwalls and concrete infrastructure and 30 years for
residential building elevation (FEMA BCA Project Configuration and Cost
Estimation Methodology Report, July 2025, Table 1, page 16). Maintenance:
FEMA gives no standard rate; seawall 1% of construction cost a year and
elevation $0 (assumptions). Tax change and value change are reported
separately and kept out of the ratio. Tax uses the published Miami price
discount scenario (D-187, assumption).
D-198 additions: every ratio also at a 3% discount rate (sensitivity,
assumption); for the typical FEMA elevation, the same project on the 5th
and 10th most damaged home in each location; real walls shorter than
200 ft are flagged "end-around flooding not modelled, likely overstated"
and left out of pooled totals.
Writes outputs/benefit/typical_projects/part2_*.csv, part2_summary.json and
reports/benefit/typical_projects_part2_map.png.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer
from scipy.spatial import cKDTree
from shapely import Point, points
from shapely.ops import substring

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import paths  # noqa: E402
from progress import Progress  # noqa: E402

OUT = paths.OUT_BENEFIT / "typical_projects"
MAP_PNG = paths.ROOT / "reports" / "benefit" / "typical_projects_part2_map.png"
FT = 0.3048
RATE = 0.07
RATE_LOW = 0.03        # sensitivity only (assumption, D-198)
SHORT_FT = 200         # walls shorter than this: end-around flooding not modelled, likely overstated (D-198)
LIFE = {"seawall": 50, "elevation": 30}
MAINT = {"seawall": 0.01, "elevation": 0.0}
COST_PER_FT = 3500.0
MAX_SNAP_M = 500       # project point to FEMA coastal shoreline, beyond this the wall is not run
CREST = 6.0
RAISE = 3.0
TAX_SCENARIO = "published_miami"
RAIN_BASINS = {"C-8", "C-9"}
TO_UTM = Transformer.from_crs("EPSG:4326", "EPSG:26917", always_xy=True)
TO_LL = Transformer.from_crs("EPSG:26917", "EPSG:4326", always_xy=True)
P = None


def annuity(n, r=RATE):
    return (1 - (1 + r) ** -n) / r


def ratio(kind, avoided, cost, r=RATE):
    pv_b = avoided * annuity(LIFE[kind], r)
    pv_c = cost * (1 + MAINT[kind] * annuity(LIFE[kind], r))
    return pv_b / pv_c if cost > 0 else np.nan


class Engine:
    def __init__(self):
        import geopandas as gpd
        import module_c_projects as mc
        import module_d_value_tax as md
        import water_levels as wl
        self.mc, self.md = mc, md
        P.start("load Module A, B and coefficients")
        self.M = mc.Model()
        A = self.M.A
        self.C = pd.read_parquet(paths.MODULE_D_COEF_PARQUET)
        self.res = pd.Series(A.residents_night.to_numpy(), index=A.fd_id.to_numpy())
        self.rain = pd.Series(A.basin.isin(RAIN_BASINS).to_numpy(), index=A.fd_id.to_numpy())
        pl = gpd.read_file(f"zip://{paths.BOUNDARY_DIR / 'tl_2024_12_place.zip'}").to_crs(26917)
        pts = gpd.GeoDataFrame({"i": np.arange(len(A))}, geometry=gpd.points_from_xy(A.x_utm, A.y_utm), crs=26917)
        j = gpd.sjoin(pts, pl[["NAME", "geometry"]], how="left", predicate="within").drop_duplicates("i").sort_values("i")
        self.place = j.NAME.fillna("Unincorporated Miami-Dade").to_numpy()
        self.places = pl
        self.base = wl.read(paths.FIRM_2027_EXTRACT, "S_Tsct_Basln").reset_index(drop=True)
        self.base_tree = None
        P.end()

    def place_of(self, x, y):
        m = self.places[self.places.contains(Point(x, y))]
        return m.NAME.iloc[0] if len(m) else "Unincorporated Miami-Dade"

    # ---- seawall alignment on the FEMA shoreline ----
    def nearest_shore(self, x, y):
        p = Point(x, y)
        d = self.base.geometry.distance(p)
        k = int(d.idxmin())
        return self.base.geometry.iloc[k], float(d.iloc[k]), k

    def wall_line(self, x, y, length_m):
        g, dist, k = self.nearest_shore(x, y)
        L = min(length_m, g.length)
        s = g.project(Point(x, y))
        a = min(max(s - L / 2, 0), g.length - L)
        seg = substring(g, a, a + L)
        return [TO_LL.transform(*c) for c in seg.coords], dist, g.length, L

    # ---- one run, with benefit per dollar, residents and tax ----
    def summarise(self, kind, r, per, cost, cost_lo=None, cost_hi=None):
        red = per.eyd_mid_before - per.eyd_mid_after
        hit = per.fd_id[red > 0]
        avoided = r["losses_avoided_per_year"]
        d = self.md.value_change(per, self.C, TAX_SCENARIO)
        est = d[d[f"beta_{TAX_SCENARIO}"].notna() & d.val_struct.gt(0)]
        tax = self.md.tax_change(est) if len(est) and est.value_change_mid.abs().sum() > 0 else {"tax_change_year1": 0, "tax_change_year10": 0}
        rain_share = float(red[per.fd_id.map(self.rain).fillna(False).to_numpy()].sum() / red.sum()) if red.sum() > 0 else np.nan
        out = {"buildings_protected": int(per.building[red > 0].nunique()), "records_protected": int(len(hit)),   # D-218
               "residents_protected": int(round(self.res.reindex(hit).fillna(0).sum())),
               "avoided_low": avoided["low"], "avoided_mid": avoided["mid"], "avoided_high": avoided["high"],
               "eyd_before_mid": r["eyd_baseline"]["mid"], "cost": cost,
               "pv_benefit_mid": avoided["mid"] * annuity(LIFE[kind]),
               "bcr_mid": ratio(kind, avoided["mid"], cost), "bcr_low": ratio(kind, avoided["low"], cost),
               "bcr_high": ratio(kind, avoided["high"], cost),
               "bcr_mid_3pct": ratio(kind, avoided["mid"], cost, RATE_LOW),
               "value_change_mid": float(est.value_change_mid.sum()),
               "tax_year1": tax["tax_change_year1"], "tax_year10": tax["tax_change_year10"],
               "share_avoided_in_rain_basins": rain_share}
        if cost_lo is not None:
            out["bcr_mid_at_p75_cost"] = ratio(kind, avoided["mid"], cost_hi)
            out["bcr_mid_at_p25_cost"] = ratio(kind, avoided["mid"], cost_lo)
        return out

    def seawall(self, line, crest, cost, **k):
        r, per = self.M.seawall(line, crest)
        r8, _ = self.M.seawall(line, 8.0)
        return {**self.summarise("seawall", r, per, cost, **k), "buildings_behind_wall": r["buildings_affected"],
                "bcr_mid_crest_8ft": ratio("seawall", r8["losses_avoided_per_year"]["mid"], cost),
                "bcr_mid_crest_8ft_3pct": ratio("seawall", r8["losses_avoided_per_year"]["mid"], cost, RATE_LOW)}

    def elevate(self, fd_ids, cost, **k):
        r, per = self.M.elevate(fd_ids, RAISE)
        return self.summarise("elevation", r, per, cost, **k)

    def top_homes(self, mask, n, start=0):
        """Single-family homes ranked by expected yearly damage; ranks start+1 to start+n."""
        A, B = self.M.A, self.M.B
        sf = A.occtype.str.startswith("RES1").to_numpy() & mask & (B.eyd_mid.to_numpy() > 0)
        i = np.flatnonzero(sf)
        i = i[np.argsort(-B.eyd_mid.to_numpy()[i], kind="stable")][start:start + n]
        return A.fd_id.to_numpy()[i].tolist(), i


# ---------------------------------------------------------------- Part 2A
def part_a(E):
    d = pd.read_csv(OUT / "part1_projects.csv")
    s = d[d.type.eq("seawall") & d.location_usable & d.cost_usable].copy()
    s["group"] = s.subtype.fillna("shoreline")
    rows = []
    P.start("2A real seawalls", total=len(s))
    for n, (_, p) in enumerate(s.iterrows(), 1):
        x, y = TO_UTM.transform(p.Longitude, p.Latitude)
        stated = pd.notna(p.length_ft)
        want_ft = p.length_ft if stated else p.cost_2025 / COST_PER_FT
        line, dist, glen, L = E.wall_line(x, y, want_ft * FT)
        crest = p.crest_ft_navd if pd.notna(p.crest_ft_navd) else CREST
        row = {"project_id": p.Project_ID, "name": p.Project_Name, "jurisdiction": p.Jurisdiction, "group": p.group,
               "lon": p.Longitude, "lat": p.Latitude, "cost": p.cost_2025, "length_ft_used": L / FT,
               "length_source": "stated" if stated else ("cost / $3,500 per ft" if L >= want_ft * FT - 1 else "shoreline available"),
               "crest_ft_navd": crest, "crest_source": "stated" if pd.notna(p.crest_ft_navd) else "assumed +6.0",
               "distance_to_fema_shoreline_m": dist,
               "short_wall": bool(L / FT < SHORT_FT)}
        if row["short_wall"]:
            row["short_wall_note"] = "end-around flooding not modelled, likely overstated"
        if dist > MAX_SNAP_M:
            row["note"] = (f"FEMA coastal shoreline is {dist / 1000:.1f} km away: the wall is on a river, canal or lake the "
                           "coastal study does not follow, so Module C cannot model it (not run)")
        else:
            row.update(E.seawall(line, crest, p.cost_2025))
        rows.append(row)
        P.update(n)
    P.end()
    # the one clear elevation project: SCALER-0684, Miami Beach, 2 homes
    e = d[d.Project_ID.eq("SCALER-0684")].iloc[0]
    ids, i = E.top_homes(E.place == "Miami Beach", 2)
    r = {"project_id": e.Project_ID, "name": e.Project_Name, "jurisdiction": e.Jurisdiction, "group": "elevation",
         "lon": float(E.M.A.lon.to_numpy()[i].mean()), "lat": float(E.M.A.lat.to_numpy()[i].mean()), "cost": e.cost_2025,
         "homes": 2, "note": "homes not named: the 2 single-family homes with the highest expected yearly damage in Miami Beach, raised 3 ft"}
    r.update(E.elevate(ids, e.cost_2025))
    rows.append(r)
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- Part 2B
def choose(df, score, key, n_high=4, n_mid=3, n_low=3, alt=None):
    """Pick high, middle and low scoring rows, each in a different place; alternate coastal and inland if alt given."""
    df = df[df[score] > 0].sort_values(score, ascending=False).reset_index(drop=True)
    q = len(df)
    bands = [("high", df.iloc[: max(1, q // 10)], n_high), ("middle", df.iloc[int(q * .4): int(q * .6)], n_mid),
             ("low", df.iloc[int(q * .8):][::-1].reset_index(drop=True), n_low)]
    used, out, flip = set(), [], True
    for band, g, n in bands:
        k = 0
        g = g.reset_index(drop=True)
        while k < n:
            cand = g[~g[key].isin(used)]
            if alt is not None:
                pref = cand[cand[alt] == flip]
                cand = pref if len(pref) else cand
            if not len(cand):
                break
            r = cand.iloc[0]
            used.add(r[key]); out.append({**r.to_dict(), "band": band}); k += 1
            flip = not flip
    return pd.DataFrame(out)


def seawall_sites(E, length_m):
    A, B = E.M.A, E.M.B
    coastal = A.wse_coastal_p01.notna().to_numpy() & (B.eyd_mid.to_numpy() > 0) & (A.shore_dist_m.to_numpy() <= 2000) \
        & (A.ground_elev_ft_navd88.to_numpy() < CREST)
    sx, sy = A.shore_x.to_numpy()[coastal], A.shore_y.to_numpy()[coastal]
    bc = E.M.bldg[coastal]   # physical buildings (D-218)
    eyd = B.eyd_mid.to_numpy()[coastal]
    tree = cKDTree(np.c_[sx, sy])
    rows = []
    for k, g in enumerate(E.base.geometry):
        for s in np.arange(length_m / 2, max(g.length - length_m / 2, length_m / 2) + 1, 250.0):
            c = g.interpolate(s)
            idx = tree.query_ball_point([c.x, c.y], r=length_m / 2)
            rows.append({"line": k, "station": s, "x": c.x, "y": c.y, "eyd_on_stretch": float(eyd[idx].sum()) if idx else 0.0,
                         "buildings_on_stretch": int(pd.unique(bc[idx]).size) if idx else 0, "records_on_stretch": len(idx)})
    st = pd.DataFrame(rows)
    st = st[st.eyd_on_stretch > 0].copy()
    st["place"] = [E.place_of(x, y) for x, y in zip(st.x, st.y)]
    # one station per place and band: choose() keeps places distinct
    return st


def part_b(E, hma):
    rows = []
    # seawall
    L = 550 * FT
    st = seawall_sites(E, L)
    # every candidate stretch, for the countywide picture (losses avoided only)
    P.start("scan of all 550 ft shoreline stretches", total=len(st))
    av, beh = [], []
    for n, (_, p) in enumerate(st.iterrows(), 1):
        g = E.base.geometry.iloc[int(p.line)]
        seg = substring(g, p.station - L / 2, p.station + L / 2)
        r, _ = E.M.seawall([TO_LL.transform(*c) for c in seg.coords], CREST)
        av.append(r["losses_avoided_per_year"]["mid"]); beh.append(r["buildings_affected"])
        if n % 100 == 0:
            P.update(n)
    P.end()
    st["avoided_mid"], st["buildings_behind_wall"] = av, beh
    st["bcr_mid"] = [ratio("seawall", a, 1.76e6) for a in av]
    st["bcr_mid_3pct"] = [ratio("seawall", a, 1.76e6, RATE_LOW) for a in av]
    st.to_csv(OUT / "part2_seawall_scan.csv", index=False)
    pick = choose(st, "eyd_on_stretch", "place")
    P.start("2B typical seawall placements", total=len(pick))
    for n, (_, p) in enumerate(pick.iterrows(), 1):
        g = E.base.geometry.iloc[int(p.line)]
        seg = substring(g, p.station - L / 2, p.station + L / 2)
        line = [TO_LL.transform(*c) for c in seg.coords]
        lon, lat = TO_LL.transform(p.x, p.y)
        r = {"case": "typical seawall", "id": f"S{n}", "place": p.place, "band": p.band, "lon": lon, "lat": lat, "coastal": True,
             "homes_raised": None}
        r.update(E.seawall(line, CREST, 1.76e6, cost_lo=0.56e6, cost_hi=2.74e6))
        rows.append(r)
        P.update(n)
    P.end()
    # elevation: tracts ranked by the expected yearly damage of their 10 most exposed single-family homes
    A, B = E.M.A, E.M.B
    sf = A.occtype.str.startswith("RES1").to_numpy() & (B.eyd_mid.to_numpy() > 0)
    t = pd.DataFrame({"tract": A.GEOID_tract.to_numpy()[sf], "eyd": B.eyd_mid.to_numpy()[sf], "place": E.place[sf],
                      "coastal": A.wse_coastal_p01.notna().to_numpy()[sf]})
    t = t.sort_values("eyd", ascending=False).groupby("tract").head(10)
    tr = t.groupby("tract").agg(eyd_top10=("eyd", "sum"), homes=("eyd", "size"), place=("place", lambda s: s.mode().iloc[0]),
                                coastal=("coastal", "mean")).reset_index()
    tr = tr[tr.homes >= 10]
    tr["coastal"] = tr.coastal >= 0.5
    pick = choose(tr, "eyd_top10", "place", alt="coastal")
    typ = hma["typical"]
    cases = [("typical elevation, FEMA HMA South Florida", typ["homes"], typ["cost_per_home_2025"], typ["cost_per_home_p25"], typ["cost_per_home_p75"]),
             ("elevation, Elevate Florida assumption", 10, 267000.0, None, None)]
    P.start("2B elevation placements", total=len(pick) * len(cases))
    n = 0
    for m, (_, p) in enumerate(pick.iterrows(), 1):
        for case, homes, cph, lo, hi in cases:
            ids, i = E.top_homes(A.GEOID_tract.to_numpy() == p.tract, homes)
            r = {"case": case, "id": f"E{m}", "place": p.place, "tract": p.tract, "band": p.band, "coastal": bool(p.coastal),
                 "lon": float(A.lon.to_numpy()[i].mean()), "lat": float(A.lat.to_numpy()[i].mean()), "homes_raised": len(ids)}
            k = {} if lo is None else {"cost_lo": lo * len(ids), "cost_hi": hi * len(ids)}
            r.update(E.elevate(ids, cph * len(ids), **k))
            if homes == 1:
                # how fast the return falls: the same project on the 5th and the 10th most damaged home (D-198)
                for rank in (5, 10):
                    ids_k, _ = E.top_homes(A.GEOID_tract.to_numpy() == p.tract, 1, start=rank - 1)
                    rk, _ = E.M.elevate(ids_k, RAISE)
                    a = rk["losses_avoided_per_year"]["mid"]
                    r[f"home{rank}_eyd_before_mid"] = rk["eyd_baseline"]["mid"]
                    r[f"home{rank}_avoided_mid"] = a
                    r[f"home{rank}_bcr_mid"] = ratio("elevation", a, cph)
                    r[f"home{rank}_bcr_mid_3pct"] = ratio("elevation", a, cph, RATE_LOW)
            rows.append(r)
            n += 1
            P.update(n)
    P.end()
    return pd.DataFrame(rows)


def draw_map(b):
    import geopandas as gpd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import BoundaryNorm, ListedColormap
    tr = gpd.read_file(f"zip://{paths.TRACT_2024_ZIP}")
    county = tr[tr.COUNTYFP == "086"].dissolve().to_crs(4326)
    water = gpd.read_file(f"zip://{paths.BOUNDARY_DIR / 'tl_2024_12086_areawater.zip'}").to_crs(4326)
    water = water[water.AWATER > 2e5]
    bounds = [0, 0.1, 0.25, 0.5, 1, 2, 1e9]
    labels = ["under 0.10", "0.10 to 0.25", "0.25 to 0.50", "0.50 to 1", "1 to 2", "over 2"]
    cmap = ListedColormap(["#b2182b", "#ef8a62", "#fddbc7", "#d1e5f0", "#67a9cf", "#2166ac"])
    norm = BoundaryNorm(bounds, cmap.N)
    fig, ax = plt.subplots(figsize=(8, 8.4), dpi=150)
    ax.set_facecolor("#dbe9f4")
    county.plot(ax=ax, color="#f4f4f2", edgecolor="#999999", linewidth=0.5)
    water.plot(ax=ax, color="#dbe9f4", linewidth=0)
    shown = [("typical seawall", "^", "Typical seawall (550 ft, +6 ft NAVD, $1.76M)"),
             ("typical elevation, FEMA HMA South Florida", "o", "Typical FEMA elevation (1 home raised 3 ft)")]
    for case, mk, lab in shown:
        g = b[b.case == case]
        ax.scatter(g.lon, g.lat, c=g.bcr_mid.clip(upper=50), cmap=cmap, norm=norm, marker=mk, s=110,
                   edgecolor="black", linewidth=0.7, zorder=3, label=lab)
        for _, r in g.iterrows():
            ax.annotate(r.id, (r.lon, r.lat), xytext=(6, 4), textcoords="offset points", fontsize=7.5, weight="bold")
    ax.set_xlim(-80.45, -80.08); ax.set_ylim(25.62, 25.98)
    ax.set_xlabel("Longitude"); ax.set_ylabel("Latitude")
    ax.set_title("Typical projects placed in 10 locations each: benefit per dollar\n(losses avoided, 7% discount, FEMA project life; "
                 "labels match Table B)", fontsize=10)
    from matplotlib.patches import Patch
    leg1 = ax.legend(handles=[Patch(color=cmap(i), label=l) for i, l in enumerate(labels)], title="Benefit per dollar",
                     loc="lower left", fontsize=7, title_fontsize=8)
    ax.add_artist(leg1)
    ax.legend(loc="upper right", fontsize=7)
    fig.tight_layout()
    fig.savefig(MAP_PNG)
    plt.close(fig)


def main():
    global P
    P = Progress("typical projects part 2")
    hma = json.loads((OUT / "hma_elevation_summary.json").read_text())
    E = Engine()
    a = part_a(E)
    a.to_csv(OUT / "part2_real_projects.csv", index=False)
    b = part_b(E, hma)
    b.to_csv(OUT / "part2_typical_placements.csv", index=False)
    P.start("map")
    draw_map(b)
    P.end()
    sh = a[a.group.eq("shoreline") & ~a.short_wall.fillna(False).astype(bool) & a.bcr_mid.notna()]
    S = {"settings": {"discount_rate": RATE, "discount_rate_sensitivity": RATE_LOW, "short_wall_ft": SHORT_FT, "project_life_years": LIFE, "maintenance_share_of_cost_per_year": MAINT,
                      "annuity_factor": {k: annuity(v) for k, v in LIFE.items()},
                      "annuity_factor_3pct": {k: annuity(v, RATE_LOW) for k, v in LIFE.items()}, "crest_ft_navd": CREST, "raise_ft": RAISE,
                      "tax_scenario": TAX_SCENARIO, "typical_elevation": hma["typical"]},
         "real": {g: {"projects": int(len(x)), "cost": float(x.cost.sum()), "avoided_mid": float(x.avoided_mid.sum()),
                      "bcr_pooled": ratio("elevation" if g == "elevation" else "seawall", x.avoided_mid.sum(), x.cost.sum()),
                      "bcr_pooled_3pct": ratio("elevation" if g == "elevation" else "seawall", x.avoided_mid.sum(), x.cost.sum(), RATE_LOW),
                      "bcr_median": float(x.bcr_mid.median())} for g, x in a.groupby("group")},
         "real_shoreline_run_excluding_short": {"projects": int(len(sh)), "cost": float(sh.cost.sum()),
                                                "avoided_mid": float(sh.avoided_mid.sum()),
                                                "bcr_pooled": ratio("seawall", sh.avoided_mid.sum(), sh.cost.sum()),
                                                "bcr_pooled_3pct": ratio("seawall", sh.avoided_mid.sum(), sh.cost.sum(), RATE_LOW)},
         "typical": {c: {"placements": int(len(x)), "avoided_mid_median": float(x.avoided_mid.median()),
                         "bcr_median": float(x.bcr_mid.median()), "bcr_max": float(x.bcr_mid.max()), "bcr_min": float(x.bcr_mid.min()),
                         "above_one": int((x.bcr_mid >= 1).sum()), "above_one_3pct": int((x.bcr_mid_3pct >= 1).sum()),
                         "bcr_median_3pct": float(x.bcr_mid_3pct.median())} for c, x in b.groupby("case")}}
    (OUT / "part2_summary.json").write_text(json.dumps(S, indent=2, default=float))
    print(json.dumps(S, indent=1, default=float))
    P.finish()


if __name__ == "__main__":
    main()
