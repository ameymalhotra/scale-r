"""Build the one-row-per-building table for the benefit simulator (prompt 27 Stage 1).

    .venv/bin/python -I "Modelling Data from Web/scripts/benefit/build_buildings.py"

Inputs (paths in scripts/common/paths.py):
  - USACE NSI 2026, Miami-Dade extract from the NSI API (D-130). NSI basement
    foundations are recoded to slab (D-132).
  - Florida DOR 2026 final NAL (tax roll) and 2026 parcel polygons, plus the
    Miami-Dade condo unit points shipped with the parcels (D-121, D-122).
  - TIGER/Line 2024 block groups (2020 geography).
  - FEMA NFHL Miami-Dade county file, flood hazard areas (D-123); the file in
    use is paths.NFHL_COUNTY_ZIP, so the 2027 maps can be swapped in by
    changing that one name. NGVD29 base flood elevations are converted to
    NAVD88 with NOAA NCAT (VERTCON 3.0) shifts (D-131).
  - NHC SLOSH MOM v4 surge rasters, Categories 1 to 5 (depth class at the point).
  - NOAA OCM sea level rise polygons (FL_SE), 1, 2, 3 and 6 ft, plus the
    "low-lying, not connected" 3 ft layer.
  - NOAA OCM FL_SE 3 m DEM (NAVD88), read by HTTP range requests (D-126).

Each step is checkpointed to outputs/benefit/stage1/ (keyed by NSI fd_id) and
skipped on rerun. The final table goes to data/processed/benefit/buildings.parquet.
(pyarrow 21.0.0, D-127).

Privacy: owner names and mailing addresses in the tax roll are never read.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
import shapely

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import paths  # noqa: E402

CK = paths.OUT_BENEFIT / "stage1"
NSI_GEOJSON = paths.NSI_2026_GEOJSON
NAL_CSV = paths.DOR_DIR / "extract" / "NAL23F202601.csv"
PARCEL_SHP = paths.DOR_DIR / "extract" / "miamidade_2026Ppar.shp"
CONDO_SHP = paths.DOR_DIR / "extract" / "miamidade_condos_2026.shp"
NFHL_EXTRACT = paths.NFHL_DIR / "extract" / paths.NFHL_COUNTY_ZIP.stem  # unzipped once, per map version
BG_ZIP = paths.BOUNDARY_DIR / "tl_2024_12_bg.zip"
NEAREST_FT = 50          # D-122: a point off every parcel takes the nearest parcel within 50 ft
NSI_COLS = ["fd_id", "bid", "cbfips", "st_damcat", "occtype", "bldgtype", "num_story", "sqft", "found_type",
            "found_ht", "med_yr_blt", "val_struct", "val_cont", "val_vehic", "ftprntsrc", "source", "students",
            "pop2amu65", "pop2amo65", "pop2pmu65", "pop2pmo65", "o65disable", "u65disable", "firmzone",
            "ground_elv", "x", "y",
            # fields new in NSI 2026
            "bldheight", "fullrep", "resunits", "ftprntsqft", "static_bfe", "zone_sub", "creprcnt", "crerank",
            "novehprob", "vehperunit"]
NAL_COLS = ["PARCEL_ID", "DOR_UC", "PA_UC", "JV", "LND_VAL", "LND_SQFOOT", "TOT_LVG_AREA", "ACT_YR_BLT",
            "EFF_YR_BLT", "NO_RES_UNTS", "NO_BULDNG", "TV_SD", "TV_NSD", "TAX_AUTH_CD", "CENSUS_BK",
            "QUAL_CD1", "VI_CD1", "SALE_PRC1", "SALE_YR1", "SALE_MO1",
            "QUAL_CD2", "VI_CD2", "SALE_PRC2", "SALE_YR2", "SALE_MO2"]
NUM_NAL = ["JV", "LND_VAL", "LND_SQFOOT", "TOT_LVG_AREA", "ACT_YR_BLT", "EFF_YR_BLT", "NO_RES_UNTS", "NO_BULDNG",
           "TV_SD", "TV_NSD", "SALE_PRC1", "SALE_YR1", "SALE_MO1", "SALE_PRC2", "SALE_YR2", "SALE_MO2"]
SLR_LAYERS = {"FL_SE_slr_1_0ft": "slr_1ft", "FL_SE_slr_2_0ft": "slr_2ft", "FL_SE_slr_3_0ft": "slr_3ft",
              "FL_SE_slr_6_0ft": "slr_6ft", "FL_SE_low_3_0ft": "slr_low_3ft"}
STATS = {}


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def ck_path(name):
    return CK / f"{name}.csv.gz"


def cached(name, fn):
    p = ck_path(name)
    if p.exists():
        log(f"{name}: checkpoint found, skipping")
        return pd.read_csv(p, dtype={"fd_id": "int64", "parcel_geo_id": str, "GEOID_bg": str, "GEOID_tract": str})
    t = time.time()
    df = fn()
    df.to_csv(p, index=False)
    log(f"{name}: done in {time.time() - t:.0f}s")
    return df


# ---------------------------------------------------------------- NSI
def load_nsi():
    df = pyogrio.read_dataframe(NSI_GEOJSON, columns=NSI_COLS, read_geometry=False)
    df = df[df.cbfips.str.startswith("12086")].reset_index(drop=True)
    STATS["nsi_version"] = "2026 (API)"
    STATS["nsi_rows"] = len(df)
    assert df.fd_id.is_unique
    # D-132: Miami-Dade has almost no basements (high water table). NSI basement
    # foundations become slab and "with basement" curves become "no basement".
    # The tax roll has no foundation field, so it cannot refine this.
    df["nsi_found_type_orig"] = df.found_type
    df["nsi_occtype_orig"] = df.occtype
    wb = df.occtype.str.contains("WB", na=False)
    b = df.found_type == "B"
    df.loc[b, "found_type"] = "S"
    df.loc[wb, "occtype"] = df.loc[wb, "occtype"].str.replace("WB", "NB", regex=False)
    df["basement_recoded"] = b | wb
    # NSI gives basement structures a first floor 2 ft above ground; a slab house's first
    # floor is lower, so recoded buildings take the median height of existing slab
    # buildings of the same (recoded) occupancy type
    df["nsi_found_ht_orig"] = df.found_ht
    slab = df[(df.found_type == "S") & ~df.basement_recoded]
    med = slab.groupby("occtype").found_ht.median()
    rec = df.basement_recoded
    df.loc[rec, "found_ht"] = df.loc[rec, "occtype"].map(med).fillna(slab.found_ht.median())
    STATS["basement_recode_found_ht_after"] = df.loc[rec, "found_ht"].value_counts().to_dict()
    STATS["basement_recode"] = {"found_type_B_to_S": int(b.sum()), "occtype_WB_to_NB": int(wb.sum()),
                                "either": int((b | wb).sum()), "both": int((b & wb).sum()),
                                "found_ht_of_recoded_before": df.loc[b | wb, "nsi_found_ht_orig"].describe().round(2).to_dict()}
    return gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.x, df.y), crs="EPSG:4326")


# ---------------------------------------------------------------- parcels and tax roll
def load_nal():
    d = pd.read_csv(NAL_CSV, usecols=NAL_COLS, dtype=str)
    for c in NUM_NAL:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    assert d.PARCEL_ID.is_unique
    return d


def parcel_lookup(nal):
    """Map every NAL record to a parcel polygon (the 'geo parcel')."""
    par = pyogrio.read_dataframe(PARCEL_SHP, columns=["PARCEL_ID"])
    STATS["parcel_polygons"] = len(par)
    STATS["parcel_polygons_null_geom"] = int(par.geometry.isna().sum())
    STATS["parcel_ids_unique"] = int(par.PARCEL_ID.nunique())
    poly_ids = set(par.PARCEL_ID.dropna())
    nal_ids = set(nal.PARCEL_ID)
    STATS["nal_records"] = len(nal)
    STATS["nal_matched_to_polygon"] = len(nal_ids & poly_ids)
    STATS["polygons_matched_to_nal"] = int(par.PARCEL_ID.isin(nal_ids).sum())
    condo = pyogrio.read_dataframe(CONDO_SHP, columns=["FOLIO", "PARENT_FOL", "CONDO_FLAG"])
    STATS["condo_points"] = len(condo)
    condo = condo.dropna(subset=["FOLIO"]).drop_duplicates("FOLIO")
    m = nal[["PARCEL_ID"]].copy()
    m["parcel_geo_id"] = np.where(m.PARCEL_ID.isin(poly_ids), m.PARCEL_ID, None)
    m["placed_by"] = np.where(m.parcel_geo_id.notna(), "own polygon", None)
    # condo units: parent folio polygon, else the polygon under the unit point
    c = condo.set_index("FOLIO")
    todo = m.parcel_geo_id.isna() & m.PARCEL_ID.isin(c.index)
    parent = m.loc[todo, "PARCEL_ID"].map(c.PARENT_FOL)
    ok = parent.isin(poly_ids)
    m.loc[ok[ok].index, "parcel_geo_id"] = parent[ok]
    m.loc[ok[ok].index, "placed_by"] = "condo parent polygon"
    todo = m.parcel_geo_id.isna() & m.PARCEL_ID.isin(c.index)
    if todo.any():
        pts = condo[condo.FOLIO.isin(m.loc[todo, "PARCEL_ID"])].to_crs(par.crs)
        j = gpd.sjoin(pts[["FOLIO", "geometry"]], par[["PARCEL_ID", "geometry"]], predicate="within", how="inner")
        j = j.drop_duplicates("FOLIO").set_index("FOLIO").PARCEL_ID
        hit = m.index[todo & m.PARCEL_ID.isin(j.index)]
        m.loc[hit, "parcel_geo_id"] = m.loc[hit, "PARCEL_ID"].map(j)
        m.loc[hit, "placed_by"] = "condo point in polygon"
    m["placed_by"] = m.placed_by.fillna("not placed")
    STATS["nal_placement"] = m.placed_by.value_counts().to_dict()
    STATS["nal_jv_by_placement"] = nal.groupby(m.placed_by).JV.sum().round(0).to_dict()
    return par, m


def parcel_attributes(nal, m):
    """One row per geo parcel: tax roll values summed over the parcel and its condo units."""
    d = nal.merge(m[["PARCEL_ID", "parcel_geo_id"]], on="PARCEL_ID")
    d = d[d.parcel_geo_id.notna()]
    own = d[d.PARCEL_ID == d.parcel_geo_id].set_index("parcel_geo_id")
    g = d.groupby("parcel_geo_id")
    out = pd.DataFrame({
        "nal_records": g.size(),
        "jv_parcel": g.JV.sum(),
        "lnd_val_parcel": g.LND_VAL.sum(),
        "tv_nsd_parcel": g.TV_NSD.sum(),
        "tot_lvg_area_parcel": g.TOT_LVG_AREA.sum(min_count=1),
        "no_res_unts_parcel": g.NO_RES_UNTS.sum(min_count=1),
        "condo_units": g.DOR_UC.apply(lambda s: int((s == "004").sum())),
        "act_yr_blt": g.ACT_YR_BLT.median(),
        "eff_yr_blt": g.EFF_YR_BLT.median(),
        "dor_uc_mode": g.DOR_UC.agg(lambda s: s.mode().iat[0]),
        "pa_uc_mode": g.PA_UC.agg(lambda s: s.mode().iat[0]),
        "tax_auth_cd": g.TAX_AUTH_CD.agg(lambda s: s.mode().iat[0]),
        "qualified_sales_2025_26": g.apply(lambda x: int(x.QUAL_CD1.isin(["01", "02"]).sum()
                                                           + x.QUAL_CD2.isin(["01", "02"]).sum()),
                                           include_groups=False),
    })
    for c in ["DOR_UC", "PA_UC", "LND_SQFOOT", "QUAL_CD1", "VI_CD1", "SALE_PRC1", "SALE_YR1", "SALE_MO1",
              "QUAL_CD2", "VI_CD2", "SALE_PRC2", "SALE_YR2", "SALE_MO2"]:
        out[c.lower() + "_own"] = own[c]
    out.index.name = "parcel_geo_id"
    return out.reset_index()


def join_parcels(nsi, par):
    pts = nsi[["fd_id", "geometry"]].to_crs(par.crs)
    par = par[par.geometry.notna()].reset_index(drop=True)
    j = gpd.sjoin(pts, par[["PARCEL_ID", "geometry"]], predicate="within", how="left")
    n_hits = j.groupby("fd_id").PARCEL_ID.count()
    STATS["buildings_in_overlapping_parcels"] = int((n_hits > 1).sum())
    j = j.sort_values(["fd_id", "PARCEL_ID"]).drop_duplicates("fd_id")
    j["parcel_match"] = np.where(j.PARCEL_ID.notna(), "within", None)
    miss = j.PARCEL_ID.isna()
    if miss.any():
        near = gpd.sjoin_nearest(pts[pts.fd_id.isin(j.loc[miss, "fd_id"])], par[["PARCEL_ID", "geometry"]],
                                 how="left", max_distance=NEAREST_FT, distance_col="parcel_dist_ft")
        near = near.sort_values(["fd_id", "parcel_dist_ft"]).drop_duplicates("fd_id").set_index("fd_id")
        idx = j.index[miss]
        j.loc[idx, "PARCEL_ID"] = j.loc[idx, "fd_id"].map(near.PARCEL_ID)
        j.loc[idx, "parcel_dist_ft"] = j.loc[idx, "fd_id"].map(near.parcel_dist_ft)
        got = j.index[miss & j.PARCEL_ID.notna()]
        j.loc[got, "parcel_match"] = f"nearest within {NEAREST_FT} ft"
    j["parcel_match"] = j.parcel_match.fillna("none")
    out = j[["fd_id", "PARCEL_ID", "parcel_match"]].rename(columns={"PARCEL_ID": "parcel_geo_id"})
    out["parcel_dist_ft"] = j.get("parcel_dist_ft")
    return out.reset_index(drop=True)


# ---------------------------------------------------------------- census geography
def join_bg(nsi):
    bg = gpd.read_file(f"zip://{BG_ZIP}", columns=["GEOID", "COUNTYFP"])
    bg = bg[bg.COUNTYFP == "086"].to_crs("EPSG:4326")
    j = gpd.sjoin(nsi[["fd_id", "geometry"]], bg[["GEOID", "geometry"]], predicate="within", how="left")
    j = j.drop_duplicates("fd_id")
    out = pd.DataFrame({"fd_id": j.fd_id.values, "GEOID_bg": j.GEOID.values})
    miss = out.GEOID_bg.isna()
    if miss.any():  # points on the county edge or in water: nearest block group
        near = gpd.sjoin_nearest(nsi[nsi.fd_id.isin(out.loc[miss, "fd_id"])][["fd_id", "geometry"]].to_crs(3086),
                                 bg[["GEOID", "geometry"]].to_crs(3086), how="left", distance_col="d")
        near = near.drop_duplicates("fd_id").set_index("fd_id")
        out.loc[miss, "GEOID_bg"] = out.loc[miss, "fd_id"].map(near.GEOID)
        STATS["bg_assigned_by_nearest"] = int(miss.sum())
    out["GEOID_tract"] = out.GEOID_bg.str[:11]
    return out


# ---------------------------------------------------------------- flood zones
def vertcon_shift_m(lon, lat):
    """Bilinear NGVD29 -> NAVD88 shift (metres, to add) from the NCAT grid (D-131)."""
    g = pd.read_csv(paths.VERTCON_GRID_CSV)
    lons, lats = np.sort(g.lon.unique()), np.sort(g.lat.unique())
    grid = g.pivot(index="lat", columns="lon", values="shift_m").loc[lats, lons].values
    x = np.clip((np.asarray(lon) - lons[0]) / (lons[1] - lons[0]), 0, len(lons) - 1.000001)
    y = np.clip((np.asarray(lat) - lats[0]) / (lats[1] - lats[0]), 0, len(lats) - 1.000001)
    i, j = y.astype(int), x.astype(int)
    fy, fx = y - i, x - j
    return (grid[i, j] * (1 - fx) * (1 - fy) + grid[i, j + 1] * fx * (1 - fy)
            + grid[i + 1, j] * (1 - fx) * fy + grid[i + 1, j + 1] * fx * fy)


def join_nfhl(nsi):
    if not NFHL_EXTRACT.exists():
        import zipfile
        with zipfile.ZipFile(paths.NFHL_COUNTY_ZIP) as z:
            z.extractall(NFHL_EXTRACT)
    STATS["nfhl_file"] = paths.NFHL_COUNTY_ZIP.name
    fz = pyogrio.read_dataframe(NFHL_EXTRACT / "S_FLD_HAZ_AR.shp", columns=["FLD_ZONE", "ZONE_SUBTY", "SFHA_TF", "STATIC_BFE", "V_DATUM",
                                                    "DEPTH"]).to_crs("EPSG:4326")
    fz["geometry"] = shapely.make_valid(fz.geometry.values)
    j = gpd.sjoin(nsi[["fd_id", "geometry"]], fz, predicate="within", how="left")
    STATS["buildings_in_overlapping_flood_zones"] = int((j.groupby("fd_id").size() > 1).sum())
    # where flood polygons overlap, keep the higher-hazard one (V, then A, then X)
    rank = {"VE": 0, "AE": 1, "AH": 2, "A": 3, "AO": 3, "D": 5, "X": 6, "OPEN WATER": 7}
    j["r"] = j.FLD_ZONE.map(rank).fillna(9)
    j = j.sort_values(["fd_id", "r"]).drop_duplicates("fd_id")
    out = pd.DataFrame({"fd_id": j.fd_id.values, "fema_zone": j.FLD_ZONE.values, "fema_zone_subtype": j.ZONE_SUBTY.values,
                        "fema_sfha": j.SFHA_TF.values, "fema_bfe_ft": j.STATIC_BFE.where(j.STATIC_BFE > -9000).values,
                        "fema_bfe_datum": j.V_DATUM.values, "fema_depth_ft": j.DEPTH.where(j.DEPTH > -9000).values})
    # D-131: BFEs in NGVD29 are converted to NAVD88 (the DEM's datum); NAVD88 BFEs pass through
    shift_ft = vertcon_shift_m(nsi.geometry.x.values, nsi.geometry.y.values) / 0.3048
    out["ngvd29_to_navd88_shift_ft"] = shift_ft
    ngvd = out.fema_bfe_datum == "NGVD29"
    navd = out.fema_bfe_datum == "NAVD88"
    out["fema_bfe_ft_navd88"] = np.where(ngvd, out.fema_bfe_ft + shift_ft, np.where(navd, out.fema_bfe_ft, np.nan))
    other = out.fema_bfe_ft.notna() & ~ngvd & ~navd
    STATS["bfe_datums"] = out.fema_bfe_datum.fillna("none").value_counts().to_dict()
    STATS["bfe_other_datum_not_converted"] = int(other.sum())
    sh = shift_ft[out.fema_bfe_ft.notna().values]
    STATS["bfe_shift_ft_buildings_with_bfe"] = {"min": round(float(sh.min()), 3), "median": round(float(np.median(sh)), 3),
                                               "max": round(float(sh.max()), 3)}
    return out


# ---------------------------------------------------------------- sea level rise
def sample_slr(nsi):
    out = pd.DataFrame({"fd_id": nsi.fd_id.values})
    bbox = tuple(nsi.total_bounds + np.array([-.01, -.01, .01, .01]))
    pts = nsi[["fd_id", "geometry"]].to_crs("EPSG:4269")
    for layer, col in SLR_LAYERS.items():
        t = time.time()
        g = pyogrio.read_dataframe(paths.SLR_GPKG, layer=layer, bbox=bbox, columns=[])
        geoms = shapely.make_valid(g.geometry.values)
        parts = shapely.get_parts(geoms)
        parts = parts[shapely.get_type_id(parts) >= 3]  # polygons only
        # split very large parts so point tests stay fast (as process_slr.py does)
        big = shapely.get_num_coordinates(parts) > 5000
        pieces = [parts[~big]]
        for p in parts[big]:
            x0, y0, x1, y1 = p.bounds
            nx = ny = int(np.ceil(np.sqrt(shapely.get_num_coordinates(p) / 5000))) + 1
            xs, ys = np.linspace(x0, x1, nx + 1), np.linspace(y0, y1, ny + 1)
            cells = [shapely.clip_by_rect(p, xs[i], ys[k], xs[i + 1], ys[k + 1]) for i in range(nx) for k in range(ny)]
            pieces.append(np.array([c for c in cells if not c.is_empty], dtype=object))
        polys = np.concatenate(pieces)
        tree = shapely.STRtree(polys)
        hit = tree.query(pts.geometry.values, predicate="intersects")
        flag = np.zeros(len(pts), dtype=np.int8)
        flag[np.unique(hit[0])] = 1
        out[col] = flag
        STATS[f"{col}_buildings"] = int(flag.sum())
        log(f"  {layer}: {flag.sum():,} buildings inundated ({time.time() - t:.0f}s, {len(polys):,} pieces)")
    return out


# ---------------------------------------------------------------- assemble
def main():
    CK.mkdir(parents=True, exist_ok=True)
    paths.BENEFIT_DIR.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    log("loading NSI 2026 (Miami-Dade)")
    nsi = load_nsi()
    log(f"NSI rows {len(nsi):,}")
    log("loading NAL 2026 final")
    nal = load_nal()
    par, m = parcel_lookup(nal)
    log(f"NAL placement: {STATS['nal_placement']}")
    m.to_csv(ck_path("nal_to_parcel"), index=False)
    attrs = parcel_attributes(nal, m)
    attrs.to_csv(ck_path("parcel_attributes"), index=False)
    pj = cached("bld_parcel", lambda: join_parcels(nsi, par))
    del par
    bg = cached("bld_bg", lambda: join_bg(nsi))
    fz = cached("bld_nfhl", lambda: join_nfhl(nsi))
    pd.DataFrame({"fd_id": nsi.fd_id, "lon": nsi.geometry.x, "lat": nsi.geometry.y}).to_csv(
        CK / "points.csv.gz", index=False)
    for which in ("surge", "dem"):  # separate process: rasterio after pyogrio aborts (see sample_rasters.py)
        if not ck_path(f"bld_{which}").exists():
            log(f"sampling {which} in a separate process")
            subprocess.run([sys.executable, "-I", str(Path(__file__).parent / "sample_rasters.py"), which], check=True)
            STATS.update(json.loads((CK / f"stats_{which}.json").read_text()))
    sg = pd.read_csv(ck_path("bld_surge"))
    dm = pd.read_csv(ck_path("bld_dem"))
    sl = cached("bld_slr", lambda: sample_slr(nsi))

    b = pd.DataFrame(nsi.drop(columns="geometry")).rename(columns={"x": "lon", "y": "lat",
                                                                   "ground_elv": "nsi_ground_elev_ft"})
    for part in [pj, bg, fz, sg, sl, dm]:
        assert len(part) == len(b) and part.fd_id.is_unique
        b = b.merge(part, on="fd_id", how="left", validate="one_to_one")
    b = b.merge(attrs, on="parcel_geo_id", how="left", validate="many_to_one")
    # share of the parcel's value given to each building on it, by NSI floor area
    b["buildings_on_parcel"] = b.groupby("parcel_geo_id").fd_id.transform("size")
    sq = b.groupby("parcel_geo_id").sqft.transform("sum")
    b["parcel_share"] = np.where(b.parcel_geo_id.notna(), b.sqft / sq.replace(0, np.nan), np.nan)
    b["jv_alloc"] = b.jv_parcel * b.parcel_share
    b["residents_night"] = b.pop2amu65 + b.pop2amo65
    b["residents_day"] = b.pop2pmu65 + b.pop2pmo65
    b["nsi_cbfips_bg_matches"] = b.cbfips.str[:12] == b.GEOID_bg

    STATS["rows"] = len(b)
    STATS["elapsed_s"] = round(time.time() - t0)
    out = paths.BUILDINGS_PARQUET
    try:
        b.to_parquet(out, index=False)
        STATS["written"] = str(out.relative_to(paths.ROOT))
    except ImportError:
        out = paths.BENEFIT_DIR / "buildings.csv.gz"
        b.to_csv(out, index=False)
        STATS["written"] = str(out.relative_to(paths.ROOT))
        STATS["parquet_pending"] = "no Parquet engine (pyarrow) installed; see D-127"
        log("NO PARQUET ENGINE: wrote buildings.csv.gz instead (D-127)")
    (CK / "build_stats.json").write_text(json.dumps(STATS, indent=2, default=str))
    log(f"wrote {STATS['written']}: {len(b):,} rows, {b.shape[1]} columns")


if __name__ == "__main__":
    main()
