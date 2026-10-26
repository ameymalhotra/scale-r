# Modeling layers and admin controls

`/admin/layers` manages the built-in modeling layers, all seven Critical Infrastructure overlays, and uploaded GeoJSON layers. Availability means a layer is offered on the public map; it does not select that layer automatically. Viewers still select one modeling layer at a time, while project markers remain visible above it.

Admins can change names, descriptions, switch order, opacity, colors, geometry-appropriate styling, legend labels and popup fields. Infrastructure overlays have their own order and availability. Their opacity is multiplied by the Critical Infrastructure group's opacity. Source identifiers, scientific class values and vertical units are fixed.

## Draft and publish

Save draft does not change the public map. Publish writes a versioned configuration through the existing `publish-projects` function. Restore to draft and Make live retain built-in settings as well as uploaded layers. Older versions without built-in settings receive the original defaults plus the three new surface layers.

The configuration retains `layers` for uploads and adds `builtins`, `order` (top-level modeling switch IDs), and `overlayOrder`. Built-in settings are keyed by stable registry IDs. Unknown IDs are ignored, scientific classes are restored from the registry, and missing entries use defaults.

## Surface sources

| Layer | Source and display |
| --- | --- |
| Sea Level Rise — 4 ft | Local NOAA `FL_SE_slr_4_0ft` polygons; ocean-connected inundation 4 ft above MHHW. Unconnected low-lying polygons are excluded. Simplified by half a tile sample per zoom (about 2 m at zoom 14). |
| Storm Surge — Category 3 | Local NOAA/NHC June 2026 Category 3 SLOSH MOM high-tide raster (about 10 m). Original 1–21 depth classes in feet above ground are retained and drawn as smooth contour bands. Class 99 identifies levee areas where hazard is not assessed. NoData is transparent. |
| Elevation | [NOAA Southeast Florida 3 m NAVD88 DEM](https://coast.noaa.gov/slrdata/DEMs/FL/index.html), read from its ~6 m overview and drawn as smooth contour bands: below 0, 0–2, 2–4, 4–6, 6–10, 10–20, and 20+ feet above NAVD88. NoData is transparent. |

MHHW, NAVD88 and depth above ground are different references. Surge is a composite maximum scenario, not the footprint of one hurricane. Display generalization is not a replacement for analytical source data or parcel-level assessment.

## Reproduce the packaged surfaces

Install `scripts/python/map-surfaces-requirements.txt`, then run `scripts/python/prepare_map_surfaces.py`. Use `--only sea-level-rise-4ft`, `--only storm-surge-category-3` or `--only elevation` to regenerate a single layer. The existing `.venv` contains these packages. The processor reads the local NOAA source files and Census county tract boundaries, clips to Miami-Dade, and writes vector tiles plus provenance metadata under `public/layers/`. Elevation uses HTTP range requests rather than downloading the entire 7.9 GB DEM; `MAP_DEM_SOURCE` can select a local copy of the same DEM. The county raster windows are cached in `/private/tmp/scale-r-map-surfaces`.

All three surfaces are XYZ vector tiles (source layer `surface`, zooms 6–14). Rasters are not drawn as square pixels, which looked blocky when zoomed in. Instead the source is smoothed slightly (Gaussian, sigma 0.6 source pixels), each tile samples it onto a 512-sample grid (bilinear when zoomed in, averaged when zoomed out), and class boundaries are traced as contour bands. Neighbouring bands are simplified together so they keep shared edges, and each tile carries 16 extra samples beyond its edge so bands meet cleanly across tiles. For surge, the flood edge is traced from the wet/dry field and depth bands are traced inside it, so the edge is not pulled toward dry land. Smoothing removes isolated single source cells; flooded and band areas stay within the limits checked below.

## Validation

Run `scripts/python/validate_map_surfaces.py` after preparation. It checks that every declared tile exists and carries valid attributes; that representative maximum-zoom points fall within three source pixels of a matching source class (sea level rise: within 3 m of the source polygons); and that display areas match the source: sea level rise within 1%, total surge flood area within 2%, and every elevation band holding at least 5% of the county within 3%. Results are written to `public/layers/validation-report.json`.

## Deployment

Deploy the app including `public/layers/` and redeploy the updated Supabase `publish-projects` function. Existing JSONB draft/version tables and admin access policies support the extended settings without a schema migration. The new function must be deployed before publishing built-in edits; the older function only writes uploaded layers into the public configuration.
