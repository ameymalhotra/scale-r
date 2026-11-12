"""Estimated first-floor elevation for every building (prompt 28 Part 1, D-162; updated Part 2, D-166, D-168).

    /Users/.../Climate-Resilience---Miami-Dade/.venv/bin/python -I scripts/benefit/build_ffe.py

No elevation certificates are available yet, so every building is estimated
(ffe_estimated = 1). Rule: ground elevation plus a typical floor height for the
building type and year built.

1. Typical floor height by foundation type (from the National Structure
   Inventory, per building; NSI 2022 technical documentation):
   slab 0.25 to 0.75 ft, crawlspace 2 ft, solid wall 2 ft, pier or pile 5.25 to
   6.25 ft (6.5 to 9 ft in VE zones). Basements were already recoded to slab in
   Stage 1 (D-127).
2. Year built: buildings in the 1% flood zone built after the community joined
   the NFIP and got its first flood map (29 Sep 1972 for all 35 Miami-Dade
   communities, FIRM database table L_Comm_Info) had to put the lowest floor at
   or above the base flood elevation (44 CFR 60.3). From 15 Mar 2012 the Florida
   Building Code (4th edition, 2010, with ASCE 24) requires the base flood
   elevation plus 1 ft for most buildings. The floor is therefore:
   - built 1972 or before, or outside the 1% zone: ground + foundation height;
   - built 1973 to 2011 inside zones A, AE, AH, VE: the higher of
     ground + foundation height and the base flood elevation;
   - built 2012 or later inside those zones: the higher of
     ground + foundation height and the base flood elevation + 1 ft;
   - zone AO (depth zone): ground + the zone depth (+1 ft from 2012).
   The base flood elevation is the one on the current effective map (2009,
   converted to NAVD88 in Stage 1). Buildings built under earlier maps may have
   used a different base flood elevation; this is an assumption.
Part 2 updates:
- first flood map date per community (D-168): each building is placed in
  its NFIP community (2027 FIRM database S_Pol_Ar) and given that
  community's initial FIRM date from FEMA's NFIP Community Status Book
  (OpenFEMA). In Miami-Dade all 35 communities have 29 Sep 1972 (newer
  cities kept the county's date), so the result is unchanged; the rule
  will pick up any future difference.
- ground elevation (D-166): USGS 3DEP 1 m (NAVD88, GEOID18) replaces the
  NOAA 3 m DEM. The NOAA value is kept in ground_elev_ft_noaa.
Year built: the parcel's actual year built from the tax roll; NSI's block
median where the parcel value is missing. Buildings with no ground value get
their tract median (flagged).
Adds columns to data/processed/benefit/buildings.parquet (no building dropped)
and writes outputs/benefit/spec_alignment/ffe_summary.json.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import paths  # noqa: E402

OUT = paths.OUT_BENEFIT / "spec_alignment"
FREEBOARD_FROM_YEAR = 2012        # Florida Building Code 2010 edition effective 15 Mar 2012: BFE + 1 ft
FREEBOARD_FT = 1.0
SFHA_BFE_ZONES = ["A", "AE", "AH", "VE"]
NEW_COLS = ["nfip_cid", "initial_firm_date", "ground_source", "year_built_used", "year_built_source", "ground_elev_filled", "ffe_simple_ft_navd88",
            "ffe_ft_navd88", "ffe_rule", "ffe_estimated", "ffe_above_ground_ft"]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    b = pd.read_parquet(paths.BUILDINGS_PARQUET)
    b = b.drop(columns=[c for c in NEW_COLS if c in b.columns])
    n0 = len(b)

    # ground elevation: 3DEP 1 m, NOAA kept alongside (D-166)
    if "ground_elev_ft_noaa" not in b.columns:
        b["ground_elev_ft_noaa"] = b.ground_elev_ft_navd88
    if paths.GROUND_3DEP_PARQUET.exists():
        g3 = pd.read_parquet(paths.GROUND_3DEP_PARQUET)
        if "fd_id" not in g3.columns:                       # first run wrote rows in the buildings order
            assert len(g3) == n0 and (g3.bid.to_numpy() == b.bid.to_numpy()).all()
            g3["fd_id"] = b.fd_id.to_numpy()
        g3 = g3.set_index("fd_id")
        b["ground_elev_ft_navd88"] = b.fd_id.map(g3.ground_elev_ft_3dep).to_numpy()
        b["ground_source"] = b.fd_id.map(g3.ground_source).fillna("noaa_3m_fallback").to_numpy()
    else:
        b["ground_source"] = "noaa_3m"

    # NFIP community and its initial FIRM date (D-168)
    import geopandas as gpd
    pol = gpd.read_file(paths.FIRM_2027_EXTRACT / "S_Pol_Ar.shp")[["CID", "geometry"]]
    pts = gpd.GeoDataFrame({"i": np.arange(n0)}, geometry=gpd.points_from_xy(b.lon, b.lat), crs="EPSG:4269").to_crs(pol.crs)
    j = gpd.sjoin(pts, pol, how="left", predicate="within").drop_duplicates("i").sort_values("i")
    csb = pd.DataFrame(json.loads(paths.COMMUNITY_STATUS_JSON.read_text())["NfipCommunityStatusBook"])
    firm = pd.to_datetime(csb.set_index("communityIdNumber").initialFloodInsuranceRateMap).dt.tz_localize(None)
    b["nfip_cid"] = j.CID.fillna("120635").to_numpy()          # outside every polygon: unincorporated county
    b["initial_firm_date"] = b.nfip_cid.map(firm).fillna(firm["120635"]).to_numpy()

    yb = b.act_yr_blt.where(b.act_yr_blt.between(1800, 2026))
    b["year_built_source"] = np.where(yb.notna(), "tax_roll_parcel", "nsi_block_median")
    b["year_built_used"] = yb.fillna(b.med_yr_blt).astype(int)

    g = b.ground_elev_ft_navd88
    b["ground_elev_filled"] = g.isna().astype(int)
    g = g.fillna(b.groupby("GEOID_tract").ground_elev_ft_navd88.transform("median"))
    g = g.fillna(b.ground_elev_ft_navd88.median())

    base = g + b.found_ht
    b["ffe_simple_ft_navd88"] = base                     # the Stage 2 assumption (foundation height only)
    zone = b.fema_zone.fillna("X")
    bfe = b.fema_bfe_ft_navd88
    post = b.year_built_used > b.initial_firm_date.dt.year
    fb = np.where(b.year_built_used >= FREEBOARD_FROM_YEAR, FREEBOARD_FT, 0.0)
    req = pd.Series(np.nan, index=b.index)
    m_bfe = post & zone.isin(SFHA_BFE_ZONES) & bfe.notna()
    req[m_bfe] = bfe[m_bfe] + fb[m_bfe]
    m_ao = post & (zone == "AO") & b.fema_depth_ft.notna()
    req[m_ao] = g[m_ao] + b.fema_depth_ft[m_ao] + fb[m_ao]
    ffe = np.where(req.notna(), np.maximum(base, req), base)
    b["ffe_ft_navd88"] = ffe
    b["ffe_rule"] = np.select(
        [req.notna() & (req > base) & (fb > 0), req.notna() & (req > base), req.notna()],
        ["code_bfe_plus_1ft", "code_bfe", "foundation_above_code"], "foundation_only")
    b["ffe_estimated"] = 1
    b["ffe_above_ground_ft"] = b.ffe_ft_navd88 - g
    assert len(b) == n0 and b.ffe_ft_navd88.notna().all()
    b.to_parquet(paths.BUILDINGS_PARQUET, index=False)

    raised = b.ffe_ft_navd88 - b.ffe_simple_ft_navd88
    sfha = zone.isin(SFHA_BFE_ZONES + ["AO"])
    R = {"buildings": n0, "ffe_estimated_share": 1.0,
         "ground_source": b.ground_source.value_counts().to_dict(),
         "communities": int(b.nfip_cid.nunique()),
         "initial_firm_dates": b.initial_firm_date.dt.strftime("%Y-%m-%d").value_counts().to_dict(),
         "year_built_source": b.year_built_source.value_counts().to_dict(),
         "ground_elev_filled": int(b.ground_elev_filled.sum()),
         "rule_counts": b.ffe_rule.value_counts().to_dict(),
         "sfha_buildings": int(sfha.sum()),
         "sfha_post_firm": int((sfha & post).sum()),
         "raised_above_simple": {"buildings": int((raised > 0.01).sum()),
                                 "median_ft_where_raised": round(float(raised[raised > 0.01].median()), 2),
                                 "p90_ft_where_raised": round(float(raised[raised > 0.01].quantile(.9)), 2)},
         "ffe_above_ground_ft_by_foundation": b.groupby("found_type").ffe_above_ground_ft.describe()[
             ["count", "25%", "50%", "75%"]].round(2).to_dict("index"),
         "typical_foundation_height_ft": b.groupby(["found_type", "found_ht"]).size().rename("buildings").reset_index()
             .to_dict("records"),
         "first_floor_below_bfe_1pct": {
             "simple_rule": int((sfha & bfe.notna() & (b.ffe_simple_ft_navd88 < bfe)).sum()),
             "main_rule": int((sfha & bfe.notna() & (b.ffe_ft_navd88 < bfe)).sum())}}
    (OUT / "ffe_summary.json").write_text(json.dumps(R, indent=2, default=str))
    print(json.dumps(R, indent=1, default=str))


if __name__ == "__main__":
    main()
