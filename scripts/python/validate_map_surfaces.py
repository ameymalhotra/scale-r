"""Validate packaged surface geometry, coverage, tile attributes and source samples."""
import hashlib
import json
from pathlib import Path

import geopandas as gpd
import mapbox_vector_tile
import mercantile
import numpy as np
from affine import Affine
from pyproj import Transformer
from shapely import prepare, make_valid
from shapely.geometry import shape

from prepare_map_surfaces import ROOT, BASE, OUT, METRIC, ELEVATION_LABELS


def validate_geojson(county, bounds):
    path = OUT / 'sea-level-rise-4ft.geojson'
    assert path.stat().st_size <= 25 * 1024 * 1024
    data = gpd.read_file(path)
    assert len(data) and data.is_valid.all() and not data.is_empty.any()
    data = data.to_crs(METRIC)
    # Nonlinear reprojection can introduce tiny crossings in formerly collinear rings.
    invalid = ~data.is_valid
    data.loc[invalid, 'geometry'] = make_valid(data.loc[invalid, 'geometry'].array, method='structure')
    assert set(data.scenario) == {'4 ft above MHHW'}
    assert set(data.connection) == {'Ocean-connected inundation'}
    outside = data.geometry.difference(county.buffer(5)).area.sum()
    assert outside < 1, f'SLR outside county tolerance: {outside} m²'
    source_path = BASE / 'tract-level/Physical Indicators/FL_SE_slr_data_dist/FL_SE_slr_final_dist.gpkg'
    original = gpd.read_file(source_path, layer='FL_SE_slr_4_0ft', bbox=tuple(bounds)).to_crs(METRIC)
    invalid = ~original.is_valid
    original.loc[invalid, 'geometry'] = make_valid(original.loc[invalid, 'geometry'].array, method='structure')
    source_area = sum(g.area if county.covers(g) else g.intersection(county).area for g in original.geometry if county.intersects(g))
    output_area = data.geometry.area.sum()
    difference = abs(output_area - source_area) / source_area
    assert difference < 0.01, f'SLR display area differs by {difference:.2%}'
    return {'features': len(data), 'bytes': path.stat().st_size, 'valid_geometry': True, 'source_area_m2': source_area, 'display_area_m2': output_area, 'relative_area_difference': difference, 'outside_county_5m_buffer_m2': outside}


def validate_tiles(name, bounds):
    meta = json.loads((OUT / f'{name}.json').read_text())
    expected = list(mercantile.tiles(*meta['bounds'], zooms=range(meta['minzoom'], meta['maxzoom'] + 1)))
    total_bytes = 0
    for tile in expected:
        path = OUT / name / str(tile.z) / str(tile.x) / f'{tile.y}.pbf'
        assert path.exists(), f'Missing tile: {path}'
        assert 0 < path.stat().st_size < 25 * 1024 * 1024
        total_bytes += path.stat().st_size
    assert len(expected) == meta['tiles'] and total_bytes == meta['bytes']
    elevation = name == 'elevation'
    source = meta['source'] if meta['source'].startswith('https://') else str(ROOT / meta['source'])
    key = hashlib.sha256(json.dumps([source, elevation, list(bounds)], default=float).encode()).hexdigest()[:16]
    with np.load(Path('/private/tmp/scale-r-map-surfaces') / f'{key}.npz') as cached:
        codes, valid = cached['codes'], cached['valid']
        inverse = ~Affine(*cached['affine'][:6])
        to_source = Transformer.from_crs('EPSG:3857', str(cached['crs']), always_xy=True).transform
    high = [tile for tile in expected if tile.z == meta['maxzoom']]
    sampled = high[::max(1, len(high) // 80)]
    classes = set()
    checked = mismatches = nonempty = 0
    for tile in sampled:
        content = mapbox_vector_tile.decode((OUT / name / str(tile.z) / str(tile.x) / f'{tile.y}.pbf').read_bytes())
        assert 'surface' in content and content['surface']['extent'] == 4096
        features = content['surface']['features']
        nonempty += bool(features)
        tile_bounds = mercantile.xy_bounds(tile)
        for feature in features[::max(1, len(features) // 20)]:
            props = feature['properties']
            if elevation:
                assert props['elevation_band'] in ELEVATION_LABELS
                assert props['vertical_datum'] == 'NAVD88' and props['units'] == 'feet'
                code = ELEVATION_LABELS.index(props['elevation_band'])
            else:
                code = props['depth_class']
                assert code in list(range(1, 22)) + [99]
                assert props['scenario'] == 'Category 3, high tide'
                if code == 99:
                    assert 'hazard not assessed' in props['depth_range']
            classes.add(code)
            geom = shape(feature['geometry'])
            assert geom.geom_type in ('Polygon', 'MultiPolygon')
            point = geom.representative_point()
            x = tile_bounds.left + point.x / 4096 * (tile_bounds.right - tile_bounds.left)
            y = tile_bounds.bottom + point.y / 4096 * (tile_bounds.top - tile_bounds.bottom)
            col, row = inverse * to_source(x, y)
            row, col = int(np.floor(row)), int(np.floor(col))
            neighborhood = np.s_[max(0, row - 2):row + 3, max(0, col - 2):col + 3]
            matches = ((codes[neighborhood] == code) & valid[neighborhood]).any()
            checked += 1
            mismatches += not matches
    assert nonempty >= 10 and len(classes) >= 4 and checked >= 100
    assert mismatches == 0, f'{name}: {mismatches}/{checked} source samples disagree'
    return {'tiles': len(expected), 'bytes': total_bytes, 'sampled_tiles': len(sampled), 'nonempty_sampled_tiles': nonempty, 'observed_class_codes': sorted(classes), 'source_samples_checked': checked, 'source_sample_mismatches': int(mismatches), 'source_comparison_tolerance_pixels': 2}


def main():
    tracts = gpd.read_file(f"zip://{BASE / 'boundaries/tl_2024_12_tract.zip'}")
    tracts = tracts[tracts.COUNTYFP == '086']
    county = tracts.to_crs(METRIC).geometry.union_all()
    prepare(county)
    bounds = tracts.to_crs('EPSG:4326').total_bounds
    report = {}
    for name in ['sea-level-rise-4ft', 'storm-surge-category-3', 'elevation']:
        print(f'Validating {name}…', flush=True)
        report[name] = validate_geojson(county, bounds) if name == 'sea-level-rise-4ft' else validate_tiles(name, bounds)
        print(json.dumps(report[name]), flush=True)
    (OUT / 'validation-report.json').write_text(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
