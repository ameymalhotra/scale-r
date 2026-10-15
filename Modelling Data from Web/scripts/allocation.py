"""Geography + allocation helpers for the SCALE-R investment tables.

Allocation rules (professor's classification - scale tags are used AS GIVEN and
are never corrected, even where a footprint is obviously misrepresented):

  Parcel / Neighborhood / Corridor -> whole investment to the single unit
                                      containing the project's point
  Municipality                     -> distributed across every unit in that
                                      municipality, population-weighted
  County                           -> distributed across every unit in
                                      Miami-Dade, population-weighted

Population weighting applies ONLY to the multi-unit paths.

Municipality assignment: each unit goes to the incorporated municipality whose
polygon contains the unit's centroid. CDPs (Kendall, Westchester, Tamiami, ...)
are NOT municipalities - they are unincorporated and fold into
"Unincorporated Miami-Dade", which is treated as its own jurisdiction.

Centroid fallback: two municipalities (El Portal, Bay Harbor Islands) contain no
tract centroid at all - they are small enough to sit inside a larger tract. For
a municipality with zero centroid-assigned units, the recipient set falls back
to every unit whose geometry INTERSECTS that municipality, still
population-weighted. Without this, those dollars have nowhere to land and the
reconciliation check fails. The fallback is per-municipality and does not touch
the other 32.
"""
import re
from pathlib import Path

import geopandas as gpd
import pandas as pd

from scaler_projects import BASE, BOUNDARY_DIR

STATE_FIPS, COUNTY_FIPS = "12", "086"
# NAD83(2011) / UTM 17N - metric CRS, so centroids are computed on a plane
PROJ_CRS = "EPSG:6346"
UNINCORPORATED = "Unincorporated Miami-Dade"

POP_FILES = {
    "tract": (BASE / "tract-level/ACS Data/B01001-SexByAge"
              / "ACSDT5Y2024.B01001-Data.csv", "B01001_001E", "1400000US"),
    "bg": (BASE / "block-group-level/ADI Data/B01003-Total Population"
           / "ACSDT5Y2024.B01003-Data.csv", "B01003_001E", "1500000US"),
}
BOUNDARY_ZIPS = {"tract": "tl_2024_12_tract.zip", "bg": "tl_2024_12_bg.zip"}


def load_units(grain):
    """TIGER units for Miami-Dade with GEOID (string), ALAND, geometry."""
    g = gpd.read_file(f"zip://{BOUNDARY_DIR / BOUNDARY_ZIPS[grain]}")
    g["GEOID"] = g["GEOID"].astype(str)
    g = g[(g["STATEFP"] == STATE_FIPS) & (g["COUNTYFP"] == COUNTY_FIPS)]
    return g[["GEOID", "ALAND", "AWATER", "geometry"]].sort_values("GEOID").reset_index(drop=True)


def load_population(grain):
    """ACS total population, GEOID as string."""
    path, col, prefix = POP_FILES[grain]
    d = pd.read_csv(path, dtype=str, skiprows=[1])
    d["GEOID"] = d["GEO_ID"].str.replace(prefix, "", regex=False)
    d["population"] = pd.to_numeric(d[col], errors="coerce")
    return d[["GEOID", "population"]]


def load_municipalities():
    """Incorporated places only (CLASSFP C*) that touch Miami-Dade."""
    pl = gpd.read_file(f"zip://{BOUNDARY_DIR / 'tl_2024_12_place.zip'}")
    tr = load_units("tract")
    pl = pl[pl.intersects(tr.union_all())]
    return pl[pl["CLASSFP"].str.startswith("C")][["NAME", "geometry"]].copy()


def normalize_municipality(name):
    """Project Jurisdiction spelling -> TIGER place NAME.

    The project file runs some names together ('MiamiBeach') and spells two
    differently from TIGER ('Opa-Locka', 'Indian Creek Village'). This is name
    normalization only - no scale tag or jurisdiction is reclassified.
    """
    s = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", str(name).strip())
    return {"Opa-Locka": "Opa-locka",
            "Indian Creek Village": "Indian Creek"}.get(s, s)


def assign_municipality(units):
    """Municipality of each unit's centroid; unmatched -> Unincorporated."""
    munis = load_municipalities().to_crs(PROJ_CRS)
    cen = units.to_crs(PROJ_CRS).copy()
    cen["geometry"] = cen.geometry.centroid
    j = gpd.sjoin(cen[["GEOID", "geometry"]], munis, how="left", predicate="within")
    j = j[~j.index.duplicated(keep="first")]
    return j.set_index("GEOID")["NAME"].fillna(UNINCORPORATED)


def municipality_members(units, muni_assignment, name):
    """GEOIDs receiving a municipality-scale project for `name`.

    Returns (geoids, path) where path is 'centroid' or the intersect fallback.
    """
    members = muni_assignment.index[muni_assignment == name].tolist()
    if members:
        return members, "centroid"
    munis = load_municipalities()
    poly = munis[munis["NAME"] == name]
    if poly.empty:
        return [], "unmatched"
    hit = units[units.intersects(poly.union_all())]
    return hit["GEOID"].tolist(), "intersect-fallback"
