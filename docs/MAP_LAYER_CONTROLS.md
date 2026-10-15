# Modeling layers and admin controls

`/admin/layers` manages the built-in modeling layers, all seven Critical Infrastructure overlays, and uploaded GeoJSON layers. Availability means a layer is offered on the public map; it does not select that layer automatically. Viewers still select one modeling layer at a time, while project markers remain visible above it.

Admins can change names, descriptions, switch order, opacity, colors, geometry-appropriate styling, legend labels and popup fields. Infrastructure overlays have their own order and availability. Their opacity is multiplied by the Critical Infrastructure group's opacity. Source identifiers, scientific class values and vertical units are fixed.

## Draft and publish

Save draft does not change the public map. Publish writes a versioned configuration through the existing `publish-projects` function. Restore to draft and Make live retain built-in settings as well as uploaded layers. Older versions without built-in settings receive the original defaults plus the three new surface layers.

The configuration retains `layers` for uploads and adds `builtins`, `order` (top-level modeling switch IDs), and `overlayOrder`. Built-in settings are keyed by stable registry IDs. Unknown IDs are ignored, scientific classes are restored from the registry, and missing entries use defaults.

## Surface sources

| Layer | Source and display |
| --- | --- |
| Sea Level Rise — 4 ft | Local NOAA `FL_SE_slr_4_0ft` polygons; ocean-connected inundation 4 ft above MHHW. Unconnected low-lying polygons are excluded. |
| Storm Surge — Category 3 | Local NOAA/NHC June 2026 Category 3 SLOSH MOM high-tide raster, at about 10 m resolution. Original 1–21 depth classes in feet above ground are retained. Class 99 identifies levee areas where hazard is not assessed. NoData is transparent. |
| Elevation | [NOAA Southeast Florida 3 m NAVD88 DEM](https://coast.noaa.gov/slrdata/DEMs/FL/index.html), sampled at approximately 10 m for display. Bands: below 0, 0–2, 2–4, 4–6, 6–10, 10–20, and 20+ feet above NAVD88. NoData is transparent. |

MHHW, NAVD88 and depth above ground are different references. Surge is a composite maximum scenario, not the footprint of one hurricane. Display generalization is not a replacement for analytical source data or parcel-level assessment.

## Reproduce the packaged surfaces

Install `scripts/python/map-surfaces-requirements.txt`, then run `scripts/python/prepare_map_surfaces.py`. Use `--only sea-level-rise-4ft`, `--only storm-surge-category-3` or `--only elevation` to regenerate a single layer. The existing `.venv` contains these packages. The processor reads the local NOAA source files and Census county tract boundaries, clips to Miami-Dade, generalizes sea-level-rise geometry by 3 m, and writes GeoJSON or vector tiles plus provenance metadata under `public/layers/`. Elevation uses HTTP range requests rather than downloading the entire 7.9 GB DEM; `MAP_DEM_SOURCE` can select a local copy of the same DEM.

The sea-level-rise GeoJSON must be nonempty and below the existing 25 MiB layer-size limit. Surge and elevation exceed that limit as full-county GeoJSON, so they are packaged as XYZ vector tiles (source layer `surface`, zooms 6–14). Tile generation reprojects categorical samples with nearest-neighbor resampling onto 256-pixel tiles and clips to the county boundary; zooming in reveals finer detail. Empty tiles are included within the declared bounds so NoData is transparent rather than a missing-file error. Raster county windows are cached under `/private/tmp/scale-r-map-surfaces` for repeat processing. The original datasets are never overwritten. Packaged surfaces are served from `/layers/` and loaded only when selected.

## Validation

Run `scripts/python/validate_map_surfaces.py` after preparation. It checks every declared tile exists, validates source units/classes, verifies stored GeoJSON validity and county coverage, compares sea-level-rise area with the original polygons, and checks representative maximum-zoom tile points against the cached source classes within two source pixels. Results are written to `public/layers/validation-report.json`. This tolerance accounts for nearest-neighbor reprojection and tile quantization.

## Deployment

Deploy the app including `public/layers/` and redeploy the updated Supabase `publish-projects` function. Existing JSONB draft/version tables and admin access policies support the extended settings without a schema migration. The new function must be deployed before publishing built-in edits; the older function only writes uploaded layers into the public configuration.
