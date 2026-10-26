"""Build county-clipped display surfaces; never modifies analytical source data.

Run with a Python environment containing geopandas, rasterio, numpy, scipy, contourpy and shapely.
Elevation is read through HTTP range requests from NOAA's cloud optimized TIFF.

All three surfaces are published as XYZ vector tiles (source layer `surface`, zooms 6-14).
The rasters are drawn as continuous contour bands instead of square pixels: each tile samples the
source onto a 512-sample grid (bilinear) and traces the band boundaries with marching squares, so
edges stay smooth at every zoom. Surge depth classes are smoothed slightly first, because a class
raster has no values between its cells to interpolate.
"""
import hashlib
import json
import math
import os
import shutil
from pathlib import Path

import contourpy
import geopandas as gpd
import mapbox_vector_tile
import mercantile
import numpy as np
import rasterio
import rasterio.warp
from rasterio.enums import Resampling
from rasterio.transform import from_bounds as grid_transform
from rasterio.windows import from_bounds
from scipy.ndimage import distance_transform_edt, gaussian_filter, uniform_filter
from shapely import (STRtree, clip_by_rect, coverage_simplify, from_wkb, get_num_coordinates, make_valid, prepare, simplify,
                     to_wkb, transform as transform_geometry, union_all)
from shapely.geometry import MultiPolygon, Polygon, box
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'Modelling Data from Web'
OUT = ROOT / 'public/layers'
CACHE = Path('/private/tmp/scale-r-map-surfaces')
METRIC = 'EPSG:6346'
DEM_URL = 'https://coast.noaa.gov/slrdata/DEMs/FL/FL_SE_GCS_3m_NAVDm_v3.tif'
SLR_PATH = BASE / 'tract-level/Physical Indicators/FL_SE_slr_data_dist/FL_SE_slr_final_dist.gpkg'
SURGE_PATH = BASE / 'tract-level/Physical Indicators/US_SLOSH_MOM_Inundation_v4_20260617/us_Category3_MOM_Inundation_HIGH.tif'
ELEVATION_LABELS = ['Below 0 ft', '0–2 ft', '2–4 ft', '4–6 ft', '6–10 ft', '10–20 ft', '20+ ft']
ELEVATION_BREAKS_FT = [0, 2, 4, 6, 10, 20]
DEM_FACTOR = 2  # read the DEM's 2x overview (~6 m) rather than all 3 m pixels
TILE_BOUNDS = [-80.9, 25, -80.1, 26]
MINZOOM, MAXZOOM = 6, 14
GRID_PX = 512  # contour samples per tile side
BUFFER_PX = 16  # samples beyond each tile edge; Mapbox clips them, so bands meet cleanly across tiles
SMOOTH_SIGMA_PX = 0.6  # Gaussian sigma in source pixels for class rasters: removes stair-steps, keeps class areas within ~1%
OPEN = 1e9  # stands in for ±infinity in contour levels
CUT_ZOOM = 12  # sea-level-rise polygons are cut along this zoom's tile grid


def transform(transformer, geom):
    return transform_geometry(geom, transformer, interleaved=False)


def surge_props(code):
    label = 'Levee area — hazard not assessed' if code == 99 else ('Less than 1 ft' if code == 1 else ('Greater than 20 ft' if code == 21 else f'{code - 1}–{code} ft'))
    return {'depth_class': code, 'depth_range': label, 'scenario': 'Category 3, high tide'}


def elevation_props(code):
    return {'elevation_band': ELEVATION_LABELS[code], 'vertical_datum': 'NAVD88', 'units': 'feet'}


def read_source(path, bounds, factor=1):
    """County window of a single-band raster as float32 (NaN = NoData), cached because the DEM is read over HTTP."""
    key = hashlib.sha256(json.dumps([str(path), factor, list(bounds)], default=float).encode()).hexdigest()[:16]
    cache = CACHE / f'{key}.npz'
    if cache.exists():
        print('Using cached county raster window…', flush=True)
        with np.load(cache) as saved:
            return saved['values'], rasterio.Affine(*saved['affine'][:6]), str(saved['crs'])
    env = {'GDAL_DISABLE_READDIR_ON_OPEN': 'EMPTY_DIR', 'CPL_VSIL_CURL_ALLOWED_EXTENSIONS': '.tif'}
    with rasterio.Env(**env), rasterio.open(path) as src:
        window = from_bounds(*rasterio.warp.transform_bounds('EPSG:4326', src.crs, *bounds), src.transform).round_offsets().round_lengths()
        height, width = math.ceil(window.height / factor), math.ceil(window.width / factor)
        values = src.read(1, window=window, out_shape=(height, width), masked=True, resampling=Resampling.nearest)
        values = values.astype('float32').filled(np.nan)
        affine = src.window_transform(window) * src.transform.scale(window.width / width, window.height / height)
        crs = str(src.crs)
    CACHE.mkdir(parents=True, exist_ok=True)
    np.savez(cache, values=values, affine=tuple(affine), crs=crs)
    return values, affine, crs


def smooth(values):
    """Gaussian smoothing that ignores NoData, so the coast is not pulled toward missing cells."""
    valid = np.isfinite(values)
    out = gaussian_filter(np.where(valid, values, 0).astype('float32'), SMOOTH_SIGMA_PX)
    weight = gaussian_filter(valid.astype('float32'), SMOOTH_SIGMA_PX)
    with np.errstate(invalid='ignore', divide='ignore'):
        out /= weight
    out[weight < 0.5] = np.nan
    return out


def extend_edges(values, rings=2):
    """Fill NoData cells within `rings` cells of data with the mean of their data neighbours."""
    for _ in range(rings):
        valid = np.isfinite(values)
        total = uniform_filter(np.where(valid, values, 0), 3, mode='constant')
        count = uniform_filter(valid.astype('float32'), 3, mode='constant')
        fill = ~valid & (count > 0)
        values[fill] = total[fill] / count[fill]
    return values


def polygonal(geom):
    if geom is None or geom.is_empty:
        return None
    if geom.geom_type in ('Polygon', 'MultiPolygon'):
        return geom
    parts = [p for g in getattr(geom, 'geoms', []) if g.geom_type in ('Polygon', 'MultiPolygon') for p in getattr(g, 'geoms', [g])]
    return MultiPolygon(parts) if parts else None


class TileGrid:
    """A tile's sample grid in Web Mercator, with a buffer of extra samples on every side."""

    def __init__(self, tile):
        b = mercantile.xy_bounds(tile)
        self.bounds = b
        self.res = (b.right - b.left) / GRID_PX
        self.n = GRID_PX + 2 * BUFFER_PX
        self.left, self.top = b.left - BUFFER_PX * self.res, b.top + BUFFER_PX * self.res
        self.footprint = box(self.left, self.top - self.n * self.res, self.left + self.n * self.res, self.top)
        self.transform = grid_transform(*self.footprint.bounds, self.n, self.n)
        lng_lat = mercantile.bounds(tile)
        self.ground_res = self.res * math.cos(math.radians((lng_lat.north + lng_lat.south) / 2))

    def isobands(self, grid, levels):
        """Polygons where lo <= value < hi for each consecutive pair of levels, in Web Mercator."""
        generator = contourpy.contour_generator(z=np.ma.masked_invalid(grid), fill_type='OuterOffset')
        bands = []
        for lo, hi in zip(levels[:-1], levels[1:]):
            points, offsets = generator.filled(lo, hi)
            polygons = []
            for p, o in zip(points, offsets):
                rings = [np.column_stack([self.left + (r[:, 0] + 0.5) * self.res, self.top - (r[:, 1] + 0.5) * self.res])
                         for r in (p[o[i]:o[i + 1]] for i in range(len(o) - 1)) if len(r) >= 4]
                if rings:
                    polygons.append(Polygon(rings[0], rings[1:]))
            bands.append(polygonal(make_valid(union_all(polygons))) if polygons else None)
        return bands


def simplified(bands, grid):
    """Simplify neighbouring bands together by half a sample, so shared edges stay shared."""
    idx = [i for i, g in enumerate(bands) if g is not None]
    if idx:
        for i, g in zip(idx, coverage_simplify(np.array([bands[i] for i in idx], dtype=object), grid.res / 2)):
            bands[i] = polygonal(g)
    return bands


def raster_sampler(affine, crs):
    source_res = abs(affine.a) * (111320 * math.cos(math.radians(25.6)) if rasterio.crs.CRS.from_user_input(crs).is_geographic else 1)

    def sample(values, grid):
        out = np.full((grid.n, grid.n), np.nan, 'float32')
        # Interpolate between source cells when zoomed in; average them when zoomed out.
        method = Resampling.bilinear if grid.ground_res < 1.5 * source_res else Resampling.average
        rasterio.warp.reproject(values, out, src_transform=affine, src_crs=crs, src_nodata=np.nan,
                                dst_transform=grid.transform, dst_crs='EPSG:3857', dst_nodata=np.nan, resampling=method)
        return out
    return sample


def surge_tiles(path, bounds):
    raw, affine, crs = read_source(path, bounds)
    wet = (raw >= 1) & (raw <= 21)
    # Dry cells take the nearest flooded depth, so depth bands are not pulled toward zero at the
    # flood edge; the edge itself is traced from the wet/dry field.
    _, (rows, cols) = distance_transform_edt(~wet, return_indices=True)
    depth = smooth(raw[rows, cols])
    del rows, cols
    flooded, levee = smooth(wet.astype('float32')), smooth((raw == 99).astype('float32'))
    sample = raster_sampler(affine, crs)
    depth_levels = [-OPEN] + [k + 0.5 for k in range(1, 21)] + [OPEN]  # class k covers k-0.5 to k+0.5 ft classes

    def features(grid):
        levee_area = simplified(grid.isobands(sample(levee, grid), [0.5, OPEN]), grid)[0]
        wet_area = grid.isobands(sample(flooded, grid), [0.5, OPEN])[0]
        if wet_area is not None and levee_area is not None:
            wet_area = polygonal(wet_area.difference(levee_area))
        bands = [None] * 21
        if wet_area is not None:
            bands = [polygonal(b.intersection(wet_area)) if b is not None else None for b in grid.isobands(sample(depth, grid), depth_levels)]
        return [(g, surge_props(code)) for code, g in zip([*range(1, 22), 99], [*simplified(bands, grid), levee_area])]
    return features


def elevation_tiles(source, bounds):
    feet, affine, crs = read_source(source, bounds, DEM_FACTOR)
    # Elevation is already continuous, so contours traced on the bilinear surface are smooth without
    # blurring, which would narrow canals and shift the bands.
    feet *= 3.280839895013123
    data = np.isfinite(feet).astype('float32')
    # Interpolation next to NoData would otherwise drop a strip up to one sample wide along every
    # data edge; extend the values a little past the edge and trace the edge itself from `data`.
    feet = extend_edges(feet)
    sample = raster_sampler(affine, crs)

    def features(grid):
        data_area = grid.isobands(sample(data, grid), [0.5, OPEN])[0]
        if data_area is None:
            return []
        # Contour bands hold lo < z <= hi; nudging each break down keeps a value exactly on a break
        # (such as flattened water at 0 ft) in the band above it, as the legend's "0–2 ft" reads.
        bands = grid.isobands(sample(feet, grid), [-OPEN, *(b - 1e-4 for b in ELEVATION_BREAKS_FT), OPEN])
        bands = [polygonal(b.intersection(data_area)) if b is not None else None for b in bands]
        return [(g, elevation_props(code)) for code, g in enumerate(simplified(bands, grid))]
    return features


def slr_tiles(county, bounds):
    cache = CACHE / 'sea-level-rise-4ft-county.wkb.npy'
    if cache.exists():
        polygons = list(from_wkb(np.load(cache, allow_pickle=True)))
    else:
        slr = gpd.read_file(SLR_PATH, layer='FL_SE_slr_4_0ft', bbox=tuple(bounds)).to_crs(METRIC)
        to_mercator = Transformer.from_crs(METRIC, 'EPSG:3857', always_xy=True).transform
        polygons = []
        for geom in slr.geometry:
            geom = make_valid(geom)
            if county.intersects(geom):
                clipped = polygonal(geom if county.covers(geom) else geom.intersection(county))
                if clipped is not None:
                    polygons.extend(getattr(clipped, 'geoms', [clipped]))
        polygons = [transform(to_mercator, p) for p in polygons]
        CACHE.mkdir(parents=True, exist_ok=True)
        np.save(cache, np.array(to_wkb(polygons), dtype=object), allow_pickle=True)
    props = {'scenario': '4 ft above MHHW', 'connection': 'Ocean-connected inundation'}
    # The largest polygon has millions of vertices, so it is cut once along the zoom-12 tile grid:
    # zoom 12-14 tiles each sit inside one cut piece, and simplifying a piece is fast.
    pieces = []
    for p in polygons:
        if p.area < 1e5 and get_num_coordinates(p) < 5000:
            pieces.append(p)
            continue
        for t in mercantile.tiles(*transform(Transformer.from_crs('EPSG:3857', 'EPSG:4326', always_xy=True).transform, p).bounds, zooms=[CUT_ZOOM]):
            part = polygonal(clip_by_rect(p, *mercantile.xy_bounds(t)))
            if part is not None:
                pieces.extend(getattr(part, 'geoms', [part]))
    by_zoom = {}

    def features(grid):
        zoom = round(math.log2(40075016.68557849 / (grid.res * GRID_PX)))
        if zoom not in by_zoom:
            # Half a sample at this zoom: about 2 m at zoom 14, coarser when zoomed out. Douglas-Peucker
            # then make_valid, piece by piece; on the uncut polygons either step takes many minutes.
            shapes = [g for g in (polygonal(make_valid(s)) for s in simplify(pieces, grid.res / 2, preserve_topology=False)) if g is not None]
            by_zoom.clear()
            by_zoom[zoom] = (shapes, STRtree(shapes))
        shapes, tree = by_zoom[zoom]
        parts = [g for g in (polygonal(clip_by_rect(shapes[i], *grid.footprint.bounds)) for i in tree.query(grid.footprint)) if g is not None]
        if not parts:
            return []
        # Join the pieces in the tile and close gaps narrower than half a sample: neighbouring NOAA
        # polygons and the cut pieces leave hairline gaps that otherwise show as straight seams.
        joined = make_valid(union_all(parts)).buffer(grid.res / 4, quad_segs=2).buffer(-grid.res / 4, quad_segs=2)
        return [(polygonal(joined), props)] if polygonal(joined) is not None else []
    return features


def write_tiles(name, features, county, metadata, clipped=False):
    """Publish XYZ vector tiles, clipped to the county (unless `clipped` already), overlapping into each tile's buffer."""
    projected_county = transform(Transformer.from_crs(METRIC, 'EPSG:3857', always_xy=True).transform, county)
    prepare(projected_county)
    shutil.rmtree(OUT / name, ignore_errors=True)
    tiles = list(mercantile.tiles(*TILE_BOUNDS, zooms=range(MINZOOM, MAXZOOM + 1)))
    total_bytes = max_bytes = feature_count = 0
    for i, tile in enumerate(tiles):
        grid = TileGrid(tile)
        encoded = []
        if projected_county.intersects(grid.footprint):
            clip = None if clipped or projected_county.covers(grid.footprint) else projected_county.intersection(grid.footprint)
            for geom, props in features(grid):
                geom = polygonal(geom if clip is None or geom is None else geom.intersection(clip))
                if geom is not None:
                    encoded.append({'geometry': geom, 'properties': props})
        payload = mapbox_vector_tile.encode({'name': 'surface', 'features': encoded}, default_options={'quantize_bounds': tuple(grid.bounds), 'extents': 4096})
        target = OUT / name / str(tile.z) / str(tile.x) / f'{tile.y}.pbf'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        total_bytes += len(payload)
        max_bytes = max(max_bytes, len(payload))
        feature_count += len(encoded)
        if i % 100 == 0:
            print(f'{name}: {i}/{len(tiles)} tiles', flush=True)
    metadata = {**metadata, 'format': 'vector-tiles', 'source_layer': 'surface', 'bounds': TILE_BOUNDS, 'minzoom': MINZOOM, 'maxzoom': MAXZOOM,
                'tiles': len(tiles), 'bytes': total_bytes, 'max_tile_bytes': max_bytes, 'features_across_zooms': feature_count,
                'extent': 4096, 'grid_samples_per_tile': GRID_PX, 'tile_buffer_samples': BUFFER_PX}
    (OUT / f'{name}.json').write_text(json.dumps(metadata, indent=2))
    report_path = OUT / 'surface-metadata.json'
    report = json.loads(report_path.read_text()) if report_path.exists() else {}
    report[name] = metadata
    report_path.write_text(json.dumps(report, indent=2))
    print(f'{name}: {len(tiles)} tiles, {total_bytes / 1048576:.2f} MiB total; largest tile {max_bytes} bytes', flush=True)
    return metadata


def county_and_bounds():
    tracts = gpd.read_file(f"zip://{BASE / 'boundaries/tl_2024_12_tract.zip'}")
    tracts = tracts[tracts.COUNTYFP == '086']
    county = tracts.to_crs(METRIC).geometry.union_all()
    prepare(county)
    return county, tracts.to_crs('EPSG:4326').total_bounds


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only', choices=['sea-level-rise-4ft', 'storm-surge-category-3', 'elevation'])
    args = parser.parse_args()
    print('Loading county boundary…', flush=True)
    county, bounds = county_and_bounds()
    if args.only in (None, 'sea-level-rise-4ft'):
        print('Reading 4-ft sea-level-rise polygons…', flush=True)
        write_tiles('sea-level-rise-4ft', slr_tiles(county, bounds), county, {
            'source': 'NOAA OCM FL_SE_slr_4_0ft', 'scenario_ft': 4, 'datum': 'MHHW',
            'simplification': 'half a grid sample per zoom (about 2 m at zoom 14)'}, clipped=True)
        (OUT / 'sea-level-rise-4ft.geojson').unlink(missing_ok=True)
    if args.only in (None, 'storm-surge-category-3'):
        print('Contouring Category 3 surge…', flush=True)
        write_tiles('storm-surge-category-3', surge_tiles(SURGE_PATH, bounds), county, {
            'source': SURGE_PATH.relative_to(ROOT).as_posix(), 'display': 'contour bands traced on a smoothed copy of the source',
            'smoothing_sigma_source_pixels': SMOOTH_SIGMA_PX,
            'category': 3, 'tide': 'high', 'source_resolution_m': 10, 'units': 'feet above ground'})
    if args.only in (None, 'elevation'):
        print('Reading NOAA elevation through HTTP range requests…', flush=True)
        source = os.environ.get('MAP_DEM_SOURCE', DEM_URL)
        write_tiles('elevation', elevation_tiles(source, bounds), county, {
            'source': DEM_URL, 'display': 'contour bands traced on the bilinear-interpolated source', 'units': 'feet', 'datum': 'NAVD88', 'display_resolution_m': 6, 'source_resolution_m': 3})


if __name__ == '__main__':
    main()
