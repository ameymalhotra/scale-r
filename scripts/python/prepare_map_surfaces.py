"""Build county-clipped display surfaces; never modifies analytical source data.

Run with a Python environment containing geopandas, rasterio, numpy and shapely.
Elevation is read through HTTP range requests from NOAA's cloud optimized TIFF.
"""
import json
import math
import os
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.features import shapes
from rasterio.enums import Resampling
from rasterio.windows import from_bounds
from shapely.geometry import shape, mapping
from shapely import prepare, transform as transform_geometry, get_num_coordinates, clip_by_rect, make_valid, set_precision, union_all
from pyproj import Transformer

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'Modelling Data from Web'
OUT = ROOT / 'public/layers'
METRIC = 'EPSG:6346'
DEM_URL = 'https://coast.noaa.gov/slrdata/DEMs/FL/FL_SE_GCS_3m_NAVDm_v3.tif'
ELEVATION_LABELS = ['Below 0 ft', '0–2 ft', '2–4 ft', '4–6 ft', '6–10 ft', '10–20 ft', '20+ ft']


def transform(transformer, geom):
    return transform_geometry(geom, transformer, interleaved=False)


def write_surface(name, features, metadata):
    # Combine equal-class pieces in small batches. This preserves the surface and
    # avoids repeating identical popup attributes thousands of times in GeoJSON.
    groups = {}
    for item in features:
        key = json.dumps(item['properties'], sort_keys=True)
        groups.setdefault(key, []).append(shape(item['geometry']))
    merged = []
    for key, geometries in groups.items():
        for i in range(0, len(geometries), 64):
            geom = set_precision(union_all(geometries[i:i + 64]), 0.000001)
            geometry = json.loads(json.dumps(mapping(geom)), parse_float=lambda n: round(float(n), 6))
            merged.append({'type': 'Feature', 'properties': json.loads(key), 'geometry': geometry})
    features = merged
    metadata = {**metadata, 'coordinate_precision_degrees': 0.000001}
    document = {'type': 'FeatureCollection', 'metadata': metadata, 'features': features}
    payload = json.dumps(document, separators=(',', ':'), ensure_ascii=False)
    size = len(payload.encode())
    if not features or size > 25 * 1024 * 1024:
        raise ValueError(f'{name}: empty surface or exceeds 25 MiB ({len(features)} features, {size} bytes)')
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f'{name}.geojson').write_text(payload)
    print(f'{name}: {len(features)} features, {size / 1048576:.2f} MiB', flush=True)
    stats = {'features': len(features), 'bytes': size, **metadata}
    report_path = OUT / 'surface-metadata.json'
    report = json.loads(report_path.read_text()) if report_path.exists() else {}
    report[name] = stats
    report_path.write_text(json.dumps(report, indent=2))
    return stats


def display_pieces(geom):
    """Spatially subdivide before simplification to bound coastal polygon complexity."""
    if geom.is_empty:
        return
    if geom.geom_type in ('MultiPolygon', 'GeometryCollection'):
        for part in geom.geoms:
            yield from display_pieces(part)
        return
    if geom.geom_type != 'Polygon':
        return
    if get_num_coordinates(geom) > 2000:
        west, south, east, north = geom.bounds
        if east - west >= north - south:
            mid = (west + east) / 2
            boxes = [(west - 1, south - 1, mid, north + 1), (mid, south - 1, east + 1, north + 1)]
        else:
            mid = (south + north) / 2
            boxes = [(west - 1, south - 1, east + 1, mid), (west - 1, mid, east + 1, north + 1)]
        for bounds in boxes:
            yield from display_pieces(make_valid(clip_by_rect(geom, *bounds)))
        return
    simplified = geom.simplify(3, preserve_topology=True)
    if not simplified.is_empty:
        yield simplified


def feature(geom, props, county, to_metric, to_lonlat):
    geom = transform(to_metric, geom)
    if not county.intersects(geom):
        return []
    if not county.covers(geom):
        geom = geom.intersection(county)
    if geom.is_empty:
        return []
    result = []
    for piece in display_pieces(geom):
        # Snap while retaining validity, then serialize short decimal coordinates.
        display = transform(to_lonlat, piece)
        if not display.is_valid:
            display = make_valid(display, method='structure')
        if display.geom_type == 'GeometryCollection':
            display = union_all([part for part in display.geoms if part.geom_type in ('Polygon', 'MultiPolygon')])
        display = set_precision(display, 0.000001)
        if display.is_empty:
            continue
        geometry = json.loads(json.dumps(mapping(display)), parse_float=lambda n: round(float(n), 6))
        result.append({'type': 'Feature', 'properties': props, 'geometry': geometry})
    return result


def raster_surface(path, elevation, county, bounds, as_tiles=None):
    import hashlib
    from affine import Affine
    key = hashlib.sha256(json.dumps([str(path), elevation, list(bounds)], default=float).encode()).hexdigest()[:16]
    cache_dir = Path('/private/tmp/scale-r-map-surfaces')
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache = cache_dir / f'{key}.npz'
    if cache.exists():
        with np.load(cache) as saved:
            codes, valid = saved['codes'], saved['valid']
            affine = Affine(*saved['affine'][:6])
            crs = str(saved['crs'])
        print('Using cached county raster window…', flush=True)
    else:
        env = {'GDAL_DISABLE_READDIR_ON_OPEN': 'EMPTY_DIR', 'CPL_VSIL_CURL_ALLOWED_EXTENSIONS': '.tif'}
        with rasterio.Env(**env), rasterio.open(path) as src:
            bbox = rasterio.warp.transform_bounds('EPSG:4326', src.crs, *bounds)
            window = from_bounds(*bbox, src.transform).round_offsets().round_lengths()
            factor = 10 / 3 if elevation else 1
            height, width = math.ceil(window.height / factor), math.ceil(window.width / factor)
            values = src.read(1, window=window, out_shape=(height, width), masked=True, resampling=Resampling.nearest)
            affine = src.window_transform(window) * src.transform.scale(window.width / width, window.height / height)
            valid = ~np.ma.getmaskarray(values)
            if elevation:
                feet = values.filled(np.nan) * 3.280839895013123
                codes = np.digitize(feet, [0, 2, 4, 6, 10, 20]).astype('uint8')
                valid &= np.isfinite(feet)
            else:
                codes = values.filled(255).astype('uint8')
                valid &= np.isin(codes, list(range(1, 22)) + [99])
            crs = str(src.crs)
        np.savez_compressed(cache, codes=codes, valid=valid, affine=tuple(affine), crs=crs)
    if as_tiles:
        return write_raster_tiles(as_tiles, codes, valid, affine, crs, county, str(path))
    print(f'Polygonizing {codes.shape[1]} × {codes.shape[0]} pixels…', flush=True)
    to_metric = Transformer.from_crs(crs, METRIC, always_xy=True).transform
    to_lonlat = Transformer.from_crs(METRIC, 'EPSG:4326', always_xy=True).transform
    features = []
    for i, (geom, value) in enumerate(shapes(codes, mask=valid, transform=affine)):
        if i % 5000 == 0:
            print(f'Processed {i} raster polygons…', flush=True)
        code = int(value)
        if elevation:
            props = {'elevation_band': ELEVATION_LABELS[code], 'vertical_datum': 'NAVD88', 'units': 'feet'}
        else:
            label = 'Levee area — hazard not assessed' if code == 99 else ('Less than 1 ft' if code == 1 else ('Greater than 20 ft' if code == 21 else f'{code - 1}–{code} ft'))
            props = {'depth_class': code, 'depth_range': label, 'scenario': 'Category 3, high tide'}
        features.extend(feature(shape(geom), props, county, to_metric, to_lonlat))
    return features


def write_raster_tiles(name, codes, valid, affine, crs, county, source):
    """Publish XYZ vector tiles with native-depth classes and nearest-neighbor LOD."""
    import mercantile
    import mapbox_vector_tile
    from rasterio.transform import from_bounds as tile_transform
    from shapely.geometry import box
    source_codes = np.where(valid, codes, 255).astype('uint8')
    projected_county = transform(Transformer.from_crs(METRIC, 'EPSG:3857', always_xy=True).transform, county)
    prepare(projected_county)
    tile_bounds = [-80.9, 25, -80.1, 26]
    tiles = list(mercantile.tiles(*tile_bounds, zooms=range(6, 15)))
    total_bytes = max_bytes = feature_count = 0
    for i, tile in enumerate(tiles):
        bounds = mercantile.xy_bounds(tile)
        footprint = box(*bounds)
        features = []
        if projected_county.intersects(footprint):
            pixels = np.full((256, 256), 255, dtype='uint8')
            dest_transform = tile_transform(*bounds, 256, 256)
            rasterio.warp.reproject(source_codes, pixels, src_transform=affine, src_crs=crs, dst_transform=dest_transform, dst_crs='EPSG:3857', src_nodata=255, dst_nodata=255, resampling=Resampling.nearest)
            full_tile = projected_county.covers(footprint)
            for geometry, value in shapes(pixels, mask=pixels != 255, transform=dest_transform):
                geom = shape(geometry)
                if not geom.is_valid:
                    geom = make_valid(geom, method='structure')
                if not full_tile:
                    geom = geom.intersection(projected_county)
                if geom.is_empty:
                    continue
                if geom.geom_type == 'GeometryCollection':
                    geom = union_all([g for g in geom.geoms if g.geom_type in ('Polygon', 'MultiPolygon')])
                if geom.is_empty or geom.geom_type not in ('Polygon', 'MultiPolygon'):
                    continue
                code = int(value)
                if name == 'elevation':
                    props = {'elevation_band': ELEVATION_LABELS[code], 'vertical_datum': 'NAVD88', 'units': 'feet'}
                else:
                    label = 'Levee area — hazard not assessed' if code == 99 else ('Less than 1 ft' if code == 1 else ('Greater than 20 ft' if code == 21 else f'{code - 1}–{code} ft'))
                    props = {'depth_class': code, 'depth_range': label, 'scenario': 'Category 3, high tide'}
                features.append({'geometry': geom, 'properties': props})
        payload = mapbox_vector_tile.encode({'name': 'surface', 'features': features}, default_options={'quantize_bounds': tuple(bounds), 'extents': 4096})
        target = OUT / name / str(tile.z) / str(tile.x) / f'{tile.y}.pbf'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        total_bytes += len(payload)
        max_bytes = max(max_bytes, len(payload))
        feature_count += len(features)
        if i % 100 == 0:
            print(f'{name}: {i}/{len(tiles)} tiles', flush=True)
    public_source = source if source.startswith('https://') else Path(source).relative_to(ROOT).as_posix()
    metadata = {'source': public_source, 'format': 'vector-tiles', 'source_layer': 'surface', 'bounds': tile_bounds, 'minzoom': 6, 'maxzoom': 14, 'tiles': len(tiles), 'bytes': total_bytes, 'max_tile_bytes': max_bytes, 'features_across_zooms': feature_count, 'resampling': 'nearest', 'tile_pixels': 256, 'extent': 4096}
    metadata.update({'units': 'feet', 'datum': 'NAVD88', 'display_resolution_m': 10, 'source_resolution_m': 3} if name == 'elevation' else {'category': 3, 'tide': 'high', 'source_resolution_m': 10, 'units': 'feet above ground'})
    (OUT / f'{name}.json').write_text(json.dumps(metadata, indent=2))
    report_path = OUT / 'surface-metadata.json'
    report = json.loads(report_path.read_text()) if report_path.exists() else {}
    report[name] = metadata
    report_path.write_text(json.dumps(report, indent=2))
    print(f'{name}: {len(tiles)} tiles, {total_bytes / 1048576:.2f} MiB total; largest tile {max_bytes} bytes', flush=True)
    return metadata


def main():
    import rasterio.warp
    print('Loading county boundary…', flush=True)
    tracts = gpd.read_file(f"zip://{BASE / 'boundaries/tl_2024_12_tract.zip'}")
    tracts = tracts[tracts.COUNTYFP == '086']
    county = tracts.to_crs(METRIC).geometry.union_all()
    prepare(county)
    bounds = tracts.to_crs('EPSG:4326').total_bounds
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--only', choices=['sea-level-rise-4ft', 'storm-surge-category-3', 'elevation'])
    args = parser.parse_args()
    to_lonlat = Transformer.from_crs(METRIC, 'EPSG:4326', always_xy=True).transform
    if args.only in (None, 'sea-level-rise-4ft'):
        slr_path = BASE / 'tract-level/Physical Indicators/FL_SE_slr_data_dist/FL_SE_slr_final_dist.gpkg'
        print('Reading 4-ft sea-level-rise polygons…', flush=True)
        slr = gpd.read_file(slr_path, layer='FL_SE_slr_4_0ft', bbox=tuple(bounds)).to_crs(METRIC)
        features = []
        for i, geom in enumerate(slr.geometry):
            if i % 500 == 0:
                print(f'Clipping SLR: {i}/{len(slr)}', flush=True)
            f = feature(geom, {'scenario': '4 ft above MHHW', 'connection': 'Ocean-connected inundation'}, county, lambda x, y, z=None: (x, y), to_lonlat)
            if f:
                features.extend(f)
        write_surface('sea-level-rise-4ft', features, {'source': 'NOAA OCM FL_SE_slr_4_0ft', 'scenario_ft': 4, 'datum': 'MHHW', 'simplification_m': 3})
    if args.only in (None, 'storm-surge-category-3'):
        surge = BASE / 'tract-level/Physical Indicators/US_SLOSH_MOM_Inundation_v4_20260617/us_Category3_MOM_Inundation_HIGH.tif'
        print('Polygonizing Category 3 surge…', flush=True)
        raster_surface(surge, False, county, bounds, as_tiles='storm-surge-category-3')
    if args.only in (None, 'elevation'):
        print('Reading NOAA elevation through HTTP range requests…', flush=True)
        raster_surface(os.environ.get('MAP_DEM_SOURCE', DEM_URL), True, county, bounds, as_tiles='elevation')



if __name__ == '__main__':
    main()
