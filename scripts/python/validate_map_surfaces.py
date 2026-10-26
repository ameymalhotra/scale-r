"""Validate packaged surface tiles: completeness, attributes, agreement with source classes and area."""
import json
import math
import os

import geopandas as gpd
import mapbox_vector_tile
import mercantile
import numpy as np
from pyproj import Transformer
from rasterio.crs import CRS
from rasterio.features import rasterize
from shapely import STRtree, make_valid
from shapely.geometry import box, shape

from prepare_map_surfaces import (OUT, METRIC, SLR_PATH, SURGE_PATH, DEM_URL, DEM_FACTOR, ELEVATION_LABELS, ELEVATION_BREAKS_FT,
                                  TILE_BOUNDS, county_and_bounds, read_source, transform)

TOLERANCE_PX = 3  # smoothing (surge, sigma 0.6) plus bilinear sampling can move an edge up to ~2 source pixels
TILE = box(0, 0, 4096, 4096)


def inventory(name):
    meta = json.loads((OUT / f'{name}.json').read_text())
    expected = list(mercantile.tiles(*meta['bounds'], zooms=range(meta['minzoom'], meta['maxzoom'] + 1)))
    total_bytes = 0
    for tile in expected:
        path = OUT / name / str(tile.z) / str(tile.x) / f'{tile.y}.pbf'
        assert path.exists(), f'Missing tile: {path}'
        assert 0 < path.stat().st_size < 25 * 1024 * 1024
        total_bytes += path.stat().st_size
    assert len(expected) == meta['tiles'] and total_bytes == meta['bytes']
    return meta, [tile for tile in expected if tile.z == meta['maxzoom']]


def features(name, tile):
    content = mapbox_vector_tile.decode((OUT / name / str(tile.z) / str(tile.x) / f'{tile.y}.pbf').read_bytes())
    assert 'surface' in content and content['surface']['extent'] == 4096
    for feature in content['surface']['features']:
        geom = shape(feature['geometry'])
        assert geom.geom_type in ('Polygon', 'MultiPolygon')
        # Snapping to whole tile units can make rings touch or cross; 'structure' repairs that while
        # keeping holes as holes, as Mapbox draws them.
        geom = make_valid(geom, method='structure')
        if not geom.is_empty:  # slivers can collapse when quantized to tile units
            yield geom, feature['properties']


def to_mercator(tile, x, y):
    b = mercantile.xy_bounds(tile)
    return b.left + x / 4096 * (b.right - b.left), b.bottom + y / 4096 * (b.top - b.bottom)


def ground_m2(tile, tile_area):
    """Area inside the tile (not its buffer), from tile units to square metres on the ground."""
    b, lnglat = mercantile.xy_bounds(tile), mercantile.bounds(tile)
    return tile_area * ((b.right - b.left) / 4096) ** 2 * math.cos(math.radians((lnglat.north + lnglat.south) / 2)) ** 2


def pixel_m2(affine, crs, rows):
    """Ground area of each source row's pixels."""
    if not CRS.from_user_input(crs).is_geographic:
        return np.full(rows, abs(affine.a * affine.e))
    lat = affine.f + (np.arange(rows) + 0.5) * affine.e
    return abs(affine.a) * 111320 * np.cos(np.radians(lat)) * abs(affine.e) * 110574


def tiled(county):
    """The county inside the area the tiles cover; its tracts reach into the ocean past the tiles' east edge."""
    tiles = list(mercantile.tiles(*TILE_BOUNDS, zooms=[14]))
    west, north = mercantile.ul(min(t.x for t in tiles), min(t.y for t in tiles), 14)
    east, south = mercantile.ul(max(t.x for t in tiles) + 1, max(t.y for t in tiles) + 1, 14)
    return county.intersection(transform(Transformer.from_crs('EPSG:4326', METRIC, always_xy=True).transform, box(west, south, east, north).segmentize(0.01)))


def validate_slr(county):
    meta, high = inventory('sea-level-rise-4ft')
    original = gpd.read_file(SLR_PATH, layer='FL_SE_slr_4_0ft', bbox=tuple(county_and_bounds()[1])).to_crs(METRIC)
    pieces = [make_valid(g) for g in original.geometry if county.intersects(g)]
    pieces = [g if county.covers(g) else g.intersection(county) for g in pieces]
    source_area = sum(g.area for g in pieces)
    tree = STRtree(pieces)
    to_metric = Transformer.from_crs('EPSG:3857', METRIC, always_xy=True).transform
    display_area, checked, mismatches = 0.0, 0, 0
    for i, tile in enumerate(high):
        for geom, props in features('sea-level-rise-4ft', tile):
            assert props == {'scenario': '4 ft above MHHW', 'connection': 'Ocean-connected inundation'}
            display_area += ground_m2(tile, geom.intersection(TILE).area)
            if i % 5:
                continue
            # Each tile holds one joined shape; check a point in each of its first few parts.
            for part in list(getattr(geom, 'geoms', [geom]))[:5]:
                point = transform(to_metric, shape({'type': 'Point', 'coordinates': to_mercator(tile, *part.representative_point().coords[0])}))
                checked += 1
                mismatches += not len(tree.query(point, predicate='dwithin', distance=3))
    difference = abs(display_area - source_area) / source_area
    assert difference < 0.01, f'SLR display area differs by {difference:.2%}'
    assert checked >= 100 and mismatches == 0, f'SLR: {mismatches}/{checked} points outside the source polygons'
    return {'tiles': meta['tiles'], 'bytes': meta['bytes'], 'source_area_m2': source_area, 'display_area_m2': display_area,
            'relative_area_difference': difference, 'source_points_checked': checked, 'source_point_mismatches': mismatches}


def validate_raster(name, county, bounds):
    meta, high = inventory(name)
    elevation = name == 'elevation'
    values, affine, crs = read_source(os.environ.get('MAP_DEM_SOURCE', DEM_URL), bounds, DEM_FACTOR) if elevation else read_source(SURGE_PATH, bounds)
    if elevation:
        codes = np.where(np.isfinite(values), np.digitize(values * 3.280839895013123, ELEVATION_BREAKS_FT), 255).astype('uint8')
    else:
        codes = np.where(np.isfinite(values), values, 255).astype('uint8')
    del values
    inside = rasterize([(transform(Transformer.from_crs(METRIC, crs, always_xy=True).transform, county), 1)],
                       out_shape=codes.shape, transform=affine, fill=0, dtype='uint8').astype(bool)
    row_m2 = pixel_m2(affine, crs, codes.shape[0])
    classes = list(range(len(ELEVATION_LABELS))) if elevation else [*range(1, 22), 99]
    source_area = {c: float(((codes == c) & inside).sum(axis=1) @ row_m2) for c in classes}
    display_area = dict.fromkeys(classes, 0.0)
    inverse = ~affine
    to_source = Transformer.from_crs('EPSG:3857', crs, always_xy=True).transform
    checked = mismatches = 0
    for i, tile in enumerate(high):
        for geom, props in features(name, tile):
            if elevation:
                assert props['vertical_datum'] == 'NAVD88' and props['units'] == 'feet'
                code = ELEVATION_LABELS.index(props['elevation_band'])
            else:
                code = props['depth_class']
                assert code in classes and props['scenario'] == 'Category 3, high tide'
            display_area[code] += ground_m2(tile, geom.intersection(TILE).area)
            if i % 10:
                continue
            # A smoothed band must lie between the classes of nearby source cells.
            col, row = inverse * to_source(*to_mercator(tile, *geom.representative_point().coords[0]))
            row, col = int(np.floor(row)), int(np.floor(col))
            near = codes[max(0, row - TOLERANCE_PX):row + TOLERANCE_PX + 1, max(0, col - TOLERANCE_PX):col + TOLERANCE_PX + 1]
            near = near[near == 99] if code == 99 else near[(near != 255) & (near != 99)]
            checked += 1
            mismatches += not (near.size and near.min() <= code <= near.max())
    assert checked >= 100 and mismatches == 0, f'{name}: {mismatches}/{checked} source samples disagree'
    if elevation:
        total = sum(source_area.values())
        # Bands holding at least 5% of the county must keep their area within 3%.
        worst = max(abs(display_area[c] - source_area[c]) / source_area[c] for c in classes if source_area[c] >= 0.05 * total)
        assert worst < 0.03, f'elevation band area differs by {worst:.2%}'
        areas = {ELEVATION_LABELS[c]: [source_area[c], display_area[c]] for c in classes}
    else:
        flooded = [sum(a[c] for c in range(1, 22)) for a in (source_area, display_area)]
        worst = abs(flooded[1] - flooded[0]) / flooded[0]
        assert worst < 0.02, f'surge flooded area differs by {worst:.2%}'
        areas = {'flooded': flooded, 'levee': [source_area[99], display_area[99]]}
    return {'tiles': meta['tiles'], 'bytes': meta['bytes'], 'source_samples_checked': checked, 'source_sample_mismatches': mismatches,
            'source_comparison_tolerance_pixels': TOLERANCE_PX, 'area_m2_source_vs_display': areas, 'largest_relative_area_difference': worst}


def main():
    county, bounds = county_and_bounds()
    county = tiled(county)
    report = {}
    for name in ['sea-level-rise-4ft', 'storm-surge-category-3', 'elevation']:
        print(f'Validating {name}…', flush=True)
        report[name] = validate_slr(county) if name == 'sea-level-rise-4ft' else validate_raster(name, county, bounds)
        print(json.dumps(report[name]), flush=True)
    (OUT / 'validation-report.json').write_text(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
