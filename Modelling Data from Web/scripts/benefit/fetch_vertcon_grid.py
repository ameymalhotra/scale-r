"""NGVD29 to NAVD88 height shift over Miami-Dade from NOAA NCAT (VERTCON 3.0), on a 0.05 degree grid (D-131).

    python3 -I "Modelling Data from Web/scripts/benefit/fetch_vertcon_grid.py"

Standard library only. NOAA's NGS Coordinate Conversion and Transformation Tool
(NCAT) web API is asked, for each grid point, what NAVD88 height an NGVD29
height of 0 has. The answer (metres) is the shift to ADD to an NGVD29 height
to get NAVD88. Writes data/reference/ngvd29_to_navd88_grid.csv; the building
script interpolates it bilinearly to each building.
"""
import csv
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))
import paths  # noqa: E402

API = "https://geodesy.noaa.gov/api/ncat/llh"
UA = "SCALE-R research (python urllib)"
LON0, LON1, LAT0, LAT1, STEP = -80.90, -80.10, 25.10, 26.00, 0.05


def query(lat, lon):
    q = {"lat": f"{lat:.4f}", "lon": f"{lon:.4f}", "inDatum": "NAD83(1986)", "outDatum": "NAD83(1986)",
         "inVertDatum": "NGVD29", "outVertDatum": "NAVD88", "orthoHt": "0"}
    req = urllib.request.Request(API + "?" + urllib.parse.urlencode(q), headers={"User-Agent": UA})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.loads(r.read().decode())
            return d
        except Exception as e:
            if attempt == 4:
                raise
            print(f"  retry {attempt + 1}: {e}", flush=True)
            time.sleep(5 * (attempt + 1))


def main():
    out = paths.REFERENCE_DIR / "ngvd29_to_navd88_grid.csv"
    rows = []
    nlon = round((LON1 - LON0) / STEP) + 1
    nlat = round((LAT1 - LAT0) / STEP) + 1
    for i in range(nlat):
        for j in range(nlon):
            lat, lon = LAT0 + i * STEP, LON0 + j * STEP
            d = query(lat, lon)
            assert d["heightUnits"] == "m" and float(d["srcOrthoht"]) == 0.0, d
            rows.append({"lat": round(lat, 4), "lon": round(lon, 4), "shift_m": float(d["destOrthoht"]),
                         "sigma_m": float(d["sigOrthoht"]), "vertcon_version": d["vertconVersion"]})
            time.sleep(0.2)
        print(f"row {i + 1}/{nlat}", flush=True)
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    s = [r["shift_m"] for r in rows]
    print(f"{len(rows)} points; shift {min(s):.3f} to {max(s):.3f} m ({min(s) / 0.3048:.2f} to {max(s) / 0.3048:.2f} ft)")


if __name__ == "__main__":
    main()
