"""Build Miami-Dade parcel and building footprint tiles for the dashboard's Parcels and Buildings toggles.

The county files (~600,000 parcels and ~860,000 buildings, ~500 MB of GeoJSON each) are far too large
to load in a browser, so each is published as zoom-14 vector tiles. Mapbox only requests tiles at zoom
14 and above and overzooms them when zoomed further in, so each view downloads a few small tiles.
Only a few small attributes are kept.

Usage: python scripts/python/prepare_footprint_tiles.py parcels path/to/Parcel.geojson
       python scripts/python/prepare_footprint_tiles.py buildings path/to/BuildingFootprint2D.geojson
       (the source files are not committed; keep them in "Modelling Data from Web/boundaries/", which git ignores)
"""
import json
import shutil
import sys

import geopandas as gpd
import mapbox_vector_tile
import mercantile
import numpy as np
from shapely import STRtree, clip_by_rect, make_valid
from shapely.geometry import box

from prepare_map_surfaces import OUT, polygonal

ZOOM = 14
EXTENT = 8192  # ~0.3 m per unit at zoom 14, so outlines stay crisp when overzoomed to zoom 18+
BUFFER = 64  # tile units of geometry kept beyond each edge, so outlines meet cleanly across tiles


def parcel_props(row):
    return {'folio': row.FOLIO or '', **({'water': 1} if str(row.WATERFLAG) == '1' else {})}


def building_props(row):
    props = {}
    if row.TYPE in ('S', 'L'):
        props['size'] = 'small' if row.TYPE == 'S' else 'large'
    if row.HEIGHT == row.HEIGHT and row.HEIGHT is not None:  # skips NaN
        props['height_ft'] = round(float(row.HEIGHT), 1)
    return props


LAYERS = {
    'parcels': {'columns': ['FOLIO', 'WATERFLAG'], 'props': parcel_props,
                'source': 'Miami-Dade County parcel polygons (Parcel.geojson)', 'properties': ['folio', 'water']},
    'buildings': {'columns': ['TYPE', 'HEIGHT'], 'props': building_props,
                  'source': 'Miami-Dade County 2D building footprints (BuildingFootprint2D)', 'properties': ['size', 'height_ft']},
}


def main():
    name, source = sys.argv[1], sys.argv[2]
    layer = LAYERS[name]
    print(f'Reading {source}…', flush=True)
    data = gpd.read_file(source, columns=layer['columns'], engine='pyogrio').to_crs('EPSG:3857')
    data = data[data.geometry.notna() & ~data.geometry.is_empty].reset_index(drop=True)
    data['geometry'] = make_valid(data.geometry.values)
    print(f'{len(data):,} {name}', flush=True)
    props = [layer['props'](row) for row in data.itertuples()]
    geoms = data.geometry.values
    tree = STRtree(geoms)

    west, south, east, north = data.to_crs('EPSG:4326').total_bounds
    tiles = list(mercantile.tiles(west, south, east, north, zooms=[ZOOM]))
    shutil.rmtree(OUT / name, ignore_errors=True)
    total_bytes = max_bytes = written = 0
    for i, tile in enumerate(tiles):
        b = mercantile.xy_bounds(tile)
        pad = (b.right - b.left) * BUFFER / EXTENT
        bounds = (b.left - pad, b.bottom - pad, b.right + pad, b.top + pad)
        features = []
        for j in np.sort(tree.query(box(*bounds))):
            geom = polygonal(clip_by_rect(geoms[j], *bounds))
            if geom is not None:
                features.append({'geometry': geom, 'properties': props[j]})
        if i % 200 == 0:
            print(f'{name}: {i}/{len(tiles)} tiles', flush=True)
        if not features:
            continue
        payload = mapbox_vector_tile.encode({'name': name, 'features': features},
                                            default_options={'quantize_bounds': tuple(b), 'extents': EXTENT})
        target = OUT / name / str(tile.z) / str(tile.x) / f'{tile.y}.pbf'
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        written += 1
        total_bytes += len(payload)
        max_bytes = max(max_bytes, len(payload))
    # Tiles with nothing in them are not written; the dashboard treats a missing tile as empty.
    metadata = {'source': layer['source'], 'format': 'vector-tiles', 'source_layer': name,
                'bounds': [round(float(v), 4) for v in (west, south, east, north)], 'minzoom': ZOOM, 'maxzoom': ZOOM,
                'features': len(data), 'tiles': written, 'bytes': total_bytes, 'max_tile_bytes': max_bytes,
                'extent': EXTENT, 'properties': layer['properties']}
    (OUT / f'{name}.json').write_text(json.dumps(metadata, indent=2))
    print(f'{name}: {written} tiles, {total_bytes / 1048576:.2f} MiB total; largest tile {max_bytes} bytes', flush=True)


if __name__ == '__main__':
    main()
