"""
Build tracts.geojson for the admin draft gap map (src/admin/viz).

Joins Miami-Dade tract polygons (public/femaindex-4326.geojson) with the
tract-level investment, hazard and vulnerability outputs in
"Modelling Data from Web/". Read-only on every input.

Run with the repo venv:  .venv/bin/python scripts/python/build_viz_tracts.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from shapely.geometry import mapping, shape

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MODEL = ROOT / "Modelling Data from Web"
TRACTS = ROOT / "public" / "femaindex-4326.geojson"
OUT = ROOT / "src" / "admin" / "viz" / "data" / "tracts.geojson"

GEOID_COL = "L0Census_Tracts.GEOID"
NAME_COL = "L0Census_Tracts.NAME"


def read_csv(path: Path, cols: list[str]) -> dict[str, dict[str, float | None]]:
    rows = {}
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            rows[row["GEOID"].zfill(11)] = {c: _num(row.get(c)) for c in cols}
    return rows


def _num(value: str | None) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except ValueError:
        return None


def main() -> None:
    invest = read_csv(MODEL / "tract_investment.csv", [
        "population", "investment_total", "investment_per_capita", "project_count",
        "investment_type_gray", "investment_type_green", "investment_type_blue", "investment_type_hybrid",
    ])
    slr = read_csv(MODEL / "slr_tract.csv", ["slr_3ft_area_share"])
    surge = read_csv(MODEL / "surge_tract.csv", ["surge_cat3_area_share"])
    nri = read_csv(ROOT / "ols_tract_data_enriched.csv", ["RISK_SCORE", "EAL_SCORE", "SOVI_SCORE"])
    svi = read_csv(MODEL / "tract_analysis.csv", ["EP_POV150"])

    features = []
    for feat in json.load(open(TRACTS))["features"]:
        props = feat["properties"]
        geoid = str(props[GEOID_COL]).zfill(11)
        out = {"GEOID": geoid, "name": props.get(NAME_COL)}
        for source in (invest, slr, surge, nri, svi):
            out.update(source.get(geoid, {}))
        full = shape(feat["geometry"])
        # Anchor for the 3D column; always inside the tract, unlike the centroid.
        anchor = full.representative_point()
        out["cx"], out["cy"] = round(anchor.x, 5), round(anchor.y, 5)
        # ~10 m tolerance keeps tract edges crisp at city zoom and halves file size.
        geom = full.simplify(0.0001, preserve_topology=True)
        features.append({"type": "Feature", "properties": out, "geometry": mapping(geom)})

    with open(OUT, "w") as fh:
        json.dump({"type": "FeatureCollection", "features": features}, fh, separators=(",", ":"))
    print(f"wrote {len(features)} tracts to {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
