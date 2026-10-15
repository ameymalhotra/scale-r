"""Stage 1 inspection of the NOAA Sea Level Rise Viewer download.

Read-only. This script reports what is in the GeoPackage: layers, scenarios,
CRS, feature counts, attributes, geometry complexity and a timing probe for
the Stage 2 spatial join. It does NOT clip, join, build variables or write any
data output, and it never modifies the downloaded files.

Full geometries are only read for two Miami-Dade bounding-box subsets, used to
measure geometry complexity and estimate processing time. Everything else is
metadata, read via pyogrio without loading geometry.

Usage: python scripts/inspect_slr.py [--timing]
  --timing  also run the overlay timing probe (slow, about 2 minutes)
"""
import sqlite3
import sys
import time
from pathlib import Path

import geopandas as gpd
import pyogrio
from shapely import get_num_coordinates

BASE = Path(__file__).resolve().parent.parent
GPKG = (BASE / "tract-level" / "Physical Indicators" / "FL_SE_slr_data_dist"
        / "FL_SE_slr_final_dist.gpkg")
TRACTS = BASE / "boundaries" / "tl_2024_12_tract.zip"
BG = BASE / "boundaries" / "tl_2024_12_bg.zip"
AREA_CRS = "EPSG:6346"  # UTM 17N, NAD83(2011); matches the rest of the project
MD_STATE, MD_COUNTY = "12", "086"


def sec(t):
    print("\n" + "=" * 78 + f"\n{t}\n" + "=" * 78)


def miami_dade_tracts():
    tr = gpd.read_file(f"zip://{TRACTS}")
    return tr[(tr.STATEFP == MD_STATE) & (tr.COUNTYFP == MD_COUNTY)].copy()


def inventory():
    sec("1a. FILES AND LAYERS")
    print(f"geopackage : {GPKG}")
    print(f"size       : {GPKG.stat().st_size:,} bytes "
          f"({GPKG.stat().st_size / 1e9:.2f} GB)")
    readme = GPKG.parent / "NOAA_OCM_SLR_Data_README.txt"
    print(f"readme     : {'present' if readme.exists() else 'ABSENT'}")

    layers = pyogrio.list_layers(GPKG)
    print(f"\nlayers     : {len(layers)}")
    rows = []
    for name, geom in layers:
        i = pyogrio.read_info(GPKG, layer=name)
        rows.append({
            "layer": name, "kind": "slr" if "_slr_" in name else "low",
            "geometry": geom, "crs": str(i["crs"]), "features": i["features"],
            "fields": tuple(i["fields"]), "bounds": i["total_bounds"],
        })

    print(f"distinct CRS   : {sorted({r['crs'] for r in rows})}")
    print(f"geometry types : {sorted({r['geometry'] for r in rows})}")
    print(f"field sets     : {sorted({r['fields'] for r in rows})}")

    for kind in ("slr", "low"):
        sub = [r for r in rows if r["kind"] == kind]
        print(f"\n--- {kind} layers ({len(sub)}), "
              f"{sum(r['features'] for r in sub):,} features ---")
        for r in sorted(sub, key=lambda r: r["layer"]):
            print(f"  {r['layer']:22s} {r['features']:>8,} features  "
                  f"fields={list(r['fields'])}")

    odd = [r["layer"] for r in rows if len(r["fields"]) != 2]
    if odd:
        print(f"\nschema inconsistency, layers without exactly 2 fields: {odd}")

    b = rows[0]["bounds"]
    print(f"\nfull extent (EPSG:4269): lon {b[0]:.3f} to {b[2]:.3f}, "
          f"lat {b[1]:.3f} to {b[3]:.3f}")
    return rows


def attributes():
    sec("1a. ATTRIBUTE VALUES (no geometry read)")
    for lyr in ["FL_SE_slr_0_0ft", "FL_SE_slr_3_0ft", "FL_SE_slr_10_0ft",
                "FL_SE_low_3_0ft"]:
        d = pyogrio.read_dataframe(GPKG, layer=lyr, read_geometry=False)
        print(f"  {lyr:18s} n={len(d):,}  gridcode: "
              f"{d.gridcode.nunique():,} distinct, "
              f"range {d.gridcode.min()} to {d.gridcode.max()}")
    print("\ngridcode is constant at 1 in the slr layers, so it carries no")
    print("information there. In the low layers it varies widely and its")
    print("meaning is NOT determinable from the field name or the README.")


def spatial_index():
    sec("1a. SPATIAL INDEX AND DECLARED CRS")
    con = sqlite3.connect(f"file:{GPKG}?mode=ro", uri=True)
    c = con.cursor()
    n = c.execute("select count(*) from sqlite_master "
                  "where type='table' and name like 'rtree_%'").fetchone()[0]
    print(f"rtree index tables: {n} (a full set means bbox reads are fast)")
    print("declared spatial reference systems:")
    for r in c.execute("select srs_id, srs_name from gpkg_spatial_ref_sys"):
        print("   ", r)
    con.close()


def crs_check():
    sec("1b. COORDINATE REFERENCE SYSTEMS")
    noaa = {str(pyogrio.read_info(GPKG, layer=n)["crs"])
            for n, _ in pyogrio.list_layers(GPKG)}
    print(f"NOAA layers      : {sorted(noaa)}")
    for path, label in [(TRACTS, "TIGER tracts"), (BG, "TIGER block groups")]:
        print(f"{label:17s}: {pyogrio.read_info(path)['crs']}")
    print(f"\nArea CRS for Stage 2: {AREA_CRS}")
    print("Both sources are EPSG:4269, so no datum shift is involved, but")
    print("EPSG:4269 is geographic (degrees) and cannot be used for area.")
    print("Both must be reprojected before any area calculation.")


def complexity_and_timing(run_timing):
    sec("1c. GEOMETRY COMPLEXITY AND PROCESSING ESTIMATE")
    md = miami_dade_tracts()
    bbox = tuple(md.total_bounds)
    print(f"Miami-Dade bbox: lon {bbox[0]:.3f} to {bbox[2]:.3f}, "
          f"lat {bbox[1]:.3f} to {bbox[3]:.3f}  ({len(md)} tracts)")

    for lyr in ["FL_SE_slr_3_0ft", "FL_SE_low_3_0ft"]:
        full = pyogrio.read_info(GPKG, layer=lyr)["features"]
        t = time.time()
        g = gpd.read_file(GPKG, layer=lyr, bbox=bbox)
        t_read = time.time() - t
        v = get_num_coordinates(g.geometry.values)
        t = time.time()
        invalid = int((~g.geometry.is_valid).sum())
        t_valid = time.time() - t
        print(f"\n  {lyr}")
        print(f"    bbox read   : {t_read:.1f}s -> {len(g):,} of {full:,} "
              f"features ({len(g)/full*100:.0f}% inside Miami-Dade bbox)")
        print(f"    vertices    : {v.sum():,} total, mean {v.mean():,.0f}, "
              f"max {v.max():,}")
        print(f"    invalid     : {invalid:,} ({invalid/len(g)*100:.2f}%), "
              f"checked in {t_valid:.1f}s")

    if not run_timing:
        print("\n(overlay timing probe skipped; pass --timing to run it)")
        return

    print("\n--- overlay timing probe (subsets only, nothing is written) ---")
    g = gpd.read_file(GPKG, layer="FL_SE_slr_3_0ft", bbox=bbox).to_crs(AREA_CRS)
    md6 = md.to_crs(AREA_CRS)
    pts = []
    for n in (25, 100):
        t = time.time()
        gpd.overlay(md6.head(n)[["GEOID", "geometry"]], g[["geometry"]],
                    how="intersection", keep_geom_type=True)
        dt = time.time() - t
        pts.append((n, dt))
        print(f"    {n:3d} tracts: {dt:6.1f}s")
    (n1, t1), (n2, t2) = pts
    slope = (t2 - t1) / (n2 - n1)
    fixed = t1 - n1 * slope
    print(f"\n    fitted: {fixed:.0f}s fixed + {slope:.2f}s per unit")
    print(f"    -> 707 tracts      ~{(fixed + 707*slope)/60:.1f} min/scenario")
    print(f"    -> 1,843 blockgrps ~{(fixed + 1843*slope)/60:.1f} min/scenario")
    print("    The cost is mostly fixed, not per unit: it is the engine")
    print("    preparing the single very large ocean-connected polygon.")


def main():
    if not GPKG.exists():
        raise SystemExit(f"GeoPackage not found at {GPKG}")
    inventory()
    attributes()
    spatial_index()
    crs_check()
    complexity_and_timing("--timing" in sys.argv)
    print("\n" + "=" * 78)
    print("Stage 1 only. No scenario processed, no output data written.")
    print("=" * 78)


if __name__ == "__main__":
    main()
