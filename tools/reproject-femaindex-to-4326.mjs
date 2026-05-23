#!/usr/bin/env node
/**
 * Reproject public/femaindex.geojson from EPSG:3857 (Web Mercator) to EPSG:4326 (WGS84).
 *
 * Output: public/femaindex-4326.geojson (same folder, EPSG:4326 suffix in name)
 *
 * Usage:
 *   node tools/reproject-femaindex-to-4326.mjs
 *   npm run reproject-femaindex
 */

import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = join(__dirname, '..');
const INPUT_PATH = join(REPO_ROOT, 'public', 'femaindex.geojson');
const OUTPUT_PATH = join(REPO_ROOT, 'public', 'femaindex-4326.geojson');

const ORIGIN_SHIFT = 20037508.34;

/** @param {[number, number]} coord */
function toWgs84Coordinate([x, y]) {
  const lon = (x / ORIGIN_SHIFT) * 180;
  let lat = (y / ORIGIN_SHIFT) * 180;
  lat = (180 / Math.PI) * (2 * Math.atan(Math.exp((lat * Math.PI) / 180)) - Math.PI / 2);
  return [lon, lat];
}

function transformToWgs84(coords) {
  if (!Array.isArray(coords)) return coords;
  if (typeof coords[0] === 'number' && typeof coords[1] === 'number') {
    return toWgs84Coordinate(coords);
  }
  return coords.map(transformToWgs84);
}

function reprojectFeatureCollection(featureCollection) {
  return {
    type: 'FeatureCollection',
    features: featureCollection.features.map((feature) => {
      if (!feature?.geometry) return feature;
      return {
        ...feature,
        geometry: {
          ...feature.geometry,
          coordinates: transformToWgs84(feature.geometry.coordinates),
        },
      };
    }),
  };
}

function main() {
  console.log(`Reading ${INPUT_PATH}`);
  const raw = readFileSync(INPUT_PATH, 'utf8');
  const geojson = JSON.parse(raw);

  if (!geojson?.features?.length) {
    console.error('No features found in input GeoJSON.');
    process.exit(1);
  }

  const crsName = geojson.crs?.properties?.name ?? '(none)';
  console.log(`Input CRS: ${crsName}`);
  console.log(`Features: ${geojson.features.length}`);

  const firstRing = geojson.features[0]?.geometry?.coordinates?.[0]?.[0];
  if (firstRing) {
    console.log(`Sample input coordinate: [${firstRing[0]}, ${firstRing[1]}]`);
  }

  const reprojected = reprojectFeatureCollection(geojson);
  reprojected.crs = {
    type: 'name',
    properties: { name: 'EPSG:4326' },
  };

  const outRing = reprojected.features[0]?.geometry?.coordinates?.[0]?.[0];
  if (outRing) {
    console.log(`Sample output coordinate: [${outRing[0]}, ${outRing[1]}]`);
  }

  writeFileSync(OUTPUT_PATH, JSON.stringify(reprojected));
  console.log(`Wrote ${OUTPUT_PATH}`);
}

main();
