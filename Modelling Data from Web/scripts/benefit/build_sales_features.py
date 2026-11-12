"""Stage 3 model table: one row per qualified residential sale with its features (prompt 27, D-149 to D-152).

    ../.venv/bin/python -I scripts/benefit/build_sales_features.py

Sales: 2026 final NAL, sale 1 and sale 2, qualified codes 01 and 02 (D-121),
improved (VI_CD = I), single-family (DOR_UC 001) and condominium (004) units.
Location: the centroid of the parcel the record sits on (condo units take
the building parcel, Stage 1 placement). Distances are in metres (UTM 17N).

Writes data/processed/benefit/sales_features.parquet and .csv.gz, and
outputs/benefit/stage3/build_log.json.
"""
import json
import subprocess
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
from scipy.spatial import cKDTree
from shapely import STRtree

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import paths  # noqa: E402

OUT = paths.OUT_BENEFIT / "stage3"
UTM = 32617
NAL_CSV = paths.DOR_DIR / "extract" / "NAL23F202601.csv"
PARCEL_SHP = paths.DOR_DIR / "extract" / "miamidade_2026Ppar.shp"
SEGMENTS = {"001": "single_family", "004": "condo"}
TRIM = 0.005                      # drop the lowest and highest 0.5% of prices per segment (D-149)
MAJOR_PARK_ACRES = 10             # "major park" = at least 10 acres (D-150)
PROJECT_STATUS = ["Completed", "Ongoing"]
PROJECT_RESOLUTION = ["Parcel", "Corridor", "Neighborhood"]   # points that mark a real place (D-151)
TYPES = ["gray", "green", "blue", "hybrid"]
BG_FEATURES = ["median_family_income", "LOWINCPCT", "PEOPCOLORPCT", "OVER64PCT", "LESSHSPCT",
               "pct_owner_occupied", "UNEMPPCT", "no_vehicle"]
LOG = {}


def sales():
    cols = ["PARCEL_ID", "DOR_UC", "TOT_LVG_AREA", "LND_SQFOOT", "ACT_YR_BLT", "EFF_YR_BLT", "JV", "NO_RES_UNTS",
            "TAX_AUTH_CD"] + [f"{c}{k}" for k in "12" for c in ["QUAL_CD", "VI_CD", "SALE_PRC", "SALE_YR", "SALE_MO"]]
    d = pd.read_csv(NAL_CSV, usecols=cols, dtype=str)
    rows = []
    for k in "12":
        s = d[d[f"QUAL_CD{k}"].isin(["01", "02"]) & d[f"VI_CD{k}"].eq("I") & d.DOR_UC.isin(SEGMENTS)].copy()
        s["sale_price"] = pd.to_numeric(s[f"SALE_PRC{k}"])
        s["sale_year"] = pd.to_numeric(s[f"SALE_YR{k}"]).astype(int)
        s["sale_month"] = pd.to_numeric(s[f"SALE_MO{k}"]).astype(int)
        s["qual_cd"] = s[f"QUAL_CD{k}"]
        s["sale_no"] = int(k)
        rows.append(s)
    s = pd.concat(rows, ignore_index=True)
    for c in ["TOT_LVG_AREA", "LND_SQFOOT", "ACT_YR_BLT", "EFF_YR_BLT", "JV", "NO_RES_UNTS"]:
        s[c] = pd.to_numeric(s[c], errors="coerce")
    s["segment"] = s.DOR_UC.map(SEGMENTS)
    LOG["qualified_improved_sales"] = s.segment.value_counts().to_dict()
    keep = []
    for seg, g in s.groupby("segment"):
        lo, hi = g.sale_price.quantile([TRIM, 1 - TRIM])
        keep.append(g[(g.sale_price >= lo) & (g.sale_price <= hi)])
        LOG[f"trim_{seg}"] = {"low": float(lo), "high": float(hi)}
    s = pd.concat(keep, ignore_index=True)
    s = s[s.TOT_LVG_AREA.gt(0) & s.ACT_YR_BLT.gt(1800)]
    LOG["after_trim_and_basic_checks"] = s.segment.value_counts().to_dict()
    s["ym"] = s.sale_year.astype(str) + "-" + s.sale_month.astype(str).str.zfill(2)
    s["age"] = (s.sale_year - s.ACT_YR_BLT).clip(lower=0)
    s["eff_age"] = (s.sale_year - s.EFF_YR_BLT).clip(lower=0)
    s["log_price"] = np.log(s.sale_price)
    s["log_jv"] = np.log(s.JV.where(s.JV > 0))
    s["log_living_area"] = np.log(s.TOT_LVG_AREA)
    s["log_lot"] = np.log(s.LND_SQFOOT.where(s.LND_SQFOOT > 0))
    return s


def locate(s):
    m = pd.read_csv(paths.OUT_BENEFIT / "stage1" / "nal_to_parcel.csv.gz", dtype=str)
    s = s.merge(m[["PARCEL_ID", "parcel_geo_id", "placed_by"]], on="PARCEL_ID", how="left")
    LOG["not_placed"] = int(s.parcel_geo_id.isna().sum())
    s = s[s.parcel_geo_id.notna()]
    par = pyogrio.read_dataframe(PARCEL_SHP, columns=["PARCEL_ID"])
    par = par[par.PARCEL_ID.isin(set(s.parcel_geo_id))].drop_duplicates("PARCEL_ID").to_crs(UTM)
    cen = par.set_index("PARCEL_ID").geometry.representative_point()
    s = s[s.parcel_geo_id.isin(cen.index)].copy()
    pt = cen.loc[s.parcel_geo_id]
    s["x"], s["y"] = pt.x.to_numpy(), pt.y.to_numpy()
    ll = gpd.GeoSeries(pt.to_numpy(), crs=UTM).to_crs(4326)
    s["lon"], s["lat"] = ll.x.to_numpy(), ll.y.to_numpy()
    bg = gpd.read_file(f"zip://{paths.BOUNDARY_DIR / 'tl_2024_12_bg.zip'}")
    bg = bg[bg.COUNTYFP == "086"].to_crs(UTM)[["GEOID", "geometry"]]
    g = gpd.GeoDataFrame(s[["x"]], geometry=gpd.points_from_xy(s.x, s.y), crs=UTM)
    j = gpd.sjoin(g, bg, predicate="within", how="left")
    j = j[~j.index.duplicated()]
    s["GEOID_bg"] = j.GEOID
    s["GEOID_tract"] = s.GEOID_bg.str[:11]
    return s.reset_index(drop=True)


def parcel_hazards(s):
    b = pd.read_parquet(paths.BUILDINGS_PARQUET, columns=["parcel_geo_id", "fema_sfha", "fema_zone",
                                                         "ground_elev_ft_navd88", "slr_3ft", "slr_6ft",
                                                         "surge_cat3_depth_ft", "surge_cat1_depth_ft", "lon", "lat"])
    b["sfha"] = b.fema_sfha.eq("T").astype(float)
    g = b.groupby("parcel_geo_id").agg(sfha=("sfha", "max"), ground_elev_ft=("ground_elev_ft_navd88", "median"),
                                       slr_3ft=("slr_3ft", "max"), slr_6ft=("slr_6ft", "max"),
                                       surge_cat3_ft=("surge_cat3_depth_ft", "max"),
                                       surge_cat1_ft=("surge_cat1_depth_ft", "max"))
    s = s.merge(g, left_on="parcel_geo_id", right_index=True, how="left")
    miss = s.sfha.isna()
    LOG["no_building_on_parcel"] = int(miss.sum())
    # sales on parcels without an NSI building take the values of the nearest building (D-149)
    bx = gpd.GeoSeries(gpd.points_from_xy(b.lon, b.lat), crs=4326).to_crs(UTM)
    d, i = cKDTree(np.c_[bx.x, bx.y]).query(s.loc[miss, ["x", "y"]].to_numpy())
    near = b.iloc[i]
    for c, src in [("sfha", "sfha"), ("ground_elev_ft", "ground_elev_ft_navd88"), ("slr_3ft", "slr_3ft"),
                   ("slr_6ft", "slr_6ft"), ("surge_cat3_ft", "surge_cat3_depth_ft"), ("surge_cat1_ft", "surge_cat1_depth_ft")]:
        s.loc[miss, c] = near[src].to_numpy()
    LOG["nearest_building_distance_m"] = pd.Series(d).describe().round(1).to_dict()
    return s


def sample_lst(s):
    """Landsat surface temperature at each sale, read in a separate process (rasterio and pyogrio clash, Stage 1)."""
    tmp = OUT / "lst_points.csv"
    s[["lon", "lat"]].to_csv(tmp, index=False)
    code = (
        "import sys,rasterio,numpy as np,pandas as pd\n"
        "p=pd.read_csv(sys.argv[1]);src=rasterio.open(sys.argv[2])\n"
        "from rasterio.warp import transform\n"
        "xs,ys=transform('EPSG:4326',src.crs,p.lon.tolist(),p.lat.tolist())\n"
        "v=np.array([x[0] for x in src.sample(zip(xs,ys))],dtype=float)\n"
        "nd=src.nodata\n"
        "v[(v==nd)|~np.isfinite(v)]=np.nan if nd is not None else v[~np.isfinite(v)]\n"
        "pd.DataFrame({'lst_f':v}).to_csv(sys.argv[3],index=False)\n")
    out = OUT / "lst_values.csv"
    subprocess.run([sys.executable, "-I", "-c", code, str(tmp), str(paths.LST_TIF), str(out)], check=True)
    s["lst_f"] = pd.read_csv(out).lst_f.to_numpy()
    LOG["lst_missing"] = int(s.lst_f.isna().sum())
    return s


def read_layer(stem, layer_dir=paths.MDC_LAYERS_DIR):
    parts = sorted(layer_dir.glob(f"{stem}_p*.geojson"))
    return pd.concat([gpd.read_file(p) for p in parts], ignore_index=True).set_crs(4326, allow_override=True).to_crs(UTM)


def nearest_polygon_dist(xy, polys):
    tree = STRtree(polys)
    pts = gpd.points_from_xy(xy[:, 0], xy[:, 1])
    _, dist = tree.query_nearest(pts, return_distance=True, all_matches=False)
    return dist


def access(s):
    xy = s[["x", "y"]].to_numpy()
    rail = read_layer("MetroRailStations_gdb")
    sch = read_layer("SchoolSite_gdb")
    parks = pd.concat([read_layer("CountyParkBoundaries_PROS_View_for_ALWAYS_ON")[["NAME", "TOTACRE", "geometry"]],
                       read_layer("MunicipalParkBoundary_gdb")[["NAME", "TOTACRE", "geometry"]]], ignore_index=True)
    parks["TOTACRE"] = pd.to_numeric(parks.TOTACRE, errors="coerce")
    major = parks[parks.TOTACRE >= MAJOR_PARK_ACRES]
    gc = rail[rail.NAME.str.contains("Government Center", case=False)]
    assert len(gc) == 1, "Government Center station not found"
    LOG["access_layers"] = {"metrorail_stations": len(rail), "public_schools": len(sch), "parks_all": len(parks),
                            "major_parks_10ac": len(major), "downtown_point": "Government Center Metrorail station"}
    s["dist_rail_m"] = cKDTree(np.c_[rail.geometry.x, rail.geometry.y]).query(xy)[0]
    s["dist_school_m"] = cKDTree(np.c_[sch.geometry.x, sch.geometry.y]).query(xy)[0]
    s["dist_major_park_m"] = nearest_polygon_dist(xy, major.geometry.to_numpy())
    s["dist_downtown_m"] = np.hypot(xy[:, 0] - gc.geometry.x.iloc[0], xy[:, 1] - gc.geometry.y.iloc[0])
    aw = gpd.read_file(f"zip://{paths.BOUNDARY_DIR / 'tl_2024_12086_areawater.zip'}").to_crs(UTM)
    coast = aw[aw.MTFCC.isin(["H2051", "H2053"])]      # bays, sounds and the ocean
    LOG["coast_polygons"] = coast.FULLNAME.fillna("unnamed").value_counts().to_dict()
    s["dist_coast_m"] = nearest_polygon_dist(xy, coast.geometry.to_numpy())
    return s


def projects(s):
    p = pd.read_csv(paths.PROJECT_CSV, encoding="utf-8-sig")
    LOG["projects_all"] = len(p)
    p = p[p.Project_Status.isin(PROJECT_STATUS) & p.Spatial_Resolution.isin(PROJECT_RESOLUTION)].copy()
    p["type"] = p.Infrastructure_Type.str.lower()
    LOG["projects_used"] = p.groupby(["type", "Project_Status"]).size().unstack(fill_value=0).to_dict()
    LOG["projects_used_total"] = len(p)
    g = gpd.GeoSeries(gpd.points_from_xy(p.Longitude, p.Latitude), crs=4326).to_crs(UTM)
    p["x"], p["y"] = g.x.to_numpy(), g.y.to_numpy()
    xy = s[["x", "y"]].to_numpy()
    for t in TYPES:
        q = p[p.type == t]
        tree = cKDTree(q[["x", "y"]].to_numpy())
        s[f"dist_{t}_m"] = tree.query(xy)[0]
        cost = q.Estimated_Cost.to_numpy(float)
        for r in (500, 1000):
            idx = tree.query_ball_point(xy, r)
            s[f"n_{t}_{r}m"] = [len(i) for i in idx]
            s[f"usd_{t}_{r}m"] = [cost[i].sum() if i else 0.0 for i in idx]
    p[["Project_ID", "type", "Project_Status", "Spatial_Resolution", "Estimated_Cost", "Reported_Year", "x", "y"]].to_csv(
        OUT / "projects_used.csv", index=False)
    return s


def neighbourhood(s):
    bg = pd.read_csv(paths.ANALYSIS_DIR / "blockgroup_analysis.csv", dtype={"GEOID": str})[["GEOID"] + BG_FEATURES]
    s = s.merge(bg.rename(columns={"GEOID": "GEOID_bg"}), on="GEOID_bg", how="left")
    # block groups with suppressed ACS values: tract mean of the block groups, then county median, plus a flag
    bg["GEOID_tract"] = bg.GEOID.str[:11]
    for c in BG_FEATURES:
        miss = s[c].isna()
        s[f"{c}_imputed"] = miss.astype(int)
        s.loc[miss, c] = s.loc[miss, "GEOID_tract"].map(bg.groupby("GEOID_tract")[c].mean())
        s[c] = s[c].fillna(bg[c].median())
        LOG.setdefault("bg_imputed", {})[c] = int(miss.sum())
    t = pd.read_csv(paths.EAD_TRACT_CSV, dtype={"GEOID_tract": str})[["GEOID_tract", "claims_per_unit"]]
    s = s.merge(t.rename(columns={"claims_per_unit": "tract_claims_per_unit"}), on="GEOID_tract", how="left")
    f = pd.read_csv(paths.OUT_ML / "stage1" / "spatial_fold_assignment.csv", dtype={"GEOID": str})
    s = s.merge(f.rename(columns={"GEOID": "GEOID_tract"}), on="GEOID_tract", how="left")
    # tracts outside the ML fold table take the fold of the nearest assigned sale
    miss = s.fold_spatial.isna()
    if miss.any():
        ok = s[~miss]
        _, i = cKDTree(ok[["x", "y"]].to_numpy()).query(s.loc[miss, ["x", "y"]].to_numpy())
        s.loc[miss, "fold_spatial"] = ok.fold_spatial.to_numpy()[i]
    LOG["fold_filled_from_nearest"] = int(miss.sum())
    s["fold_spatial"] = s.fold_spatial.astype(int)
    return s


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    s = sales()
    s = locate(s)
    s = parcel_hazards(s)
    s = sample_lst(s)
    s = access(s)
    s = projects(s)
    s = neighbourhood(s)
    LOG["rows"] = len(s)
    LOG["rows_by_segment"] = s.segment.value_counts().to_dict()
    LOG["missing_share"] = s.isna().mean().round(4)[lambda x: x > 0].to_dict()
    keep = [c for c in s.columns if not c.startswith(("QUAL_CD", "VI_CD", "SALE_PRC", "SALE_YR", "SALE_MO"))]
    s = s[keep]
    s.to_parquet(paths.SALES_FEATURES_PARQUET, index=False)
    s.to_csv(paths.SALES_FEATURES_CSV, index=False)
    (OUT / "build_log.json").write_text(json.dumps(LOG, indent=2, default=str))
    print(json.dumps(LOG, indent=1, default=str))


if __name__ == "__main__":
    main()
