/**
 * Assigns an 11-digit census tract GEOID to a lon/lat point using the same
 * polygons as scripts/python/add_tract_geoid_conf1.py: public/censuscommunityresilience.geojson
 * (Esri JSON, Web Mercator rings). The 9.5 MB file is only fetched the first
 * time a new or moved row is saved.
 */

const TRACTS_URL = '/censuscommunityresilience.geojson';
const EARTH_HALF_CIRCUMFERENCE = 20037508.342789244;

let indexPromise = null;

export function lngLatToWebMercator(lng, lat) {
  const x = (lng * EARTH_HALF_CIRCUMFERENCE) / 180;
  const y =
    (Math.log(Math.tan(((90 + lat) * Math.PI) / 360)) / (Math.PI / 180)) * (EARTH_HALF_CIRCUMFERENCE / 180);
  return [x, y];
}

function needsProjection(spatialReference) {
  const wkid = spatialReference?.latestWkid ?? spatialReference?.wkid;
  return wkid != null && ![4326, 4269].includes(Number(wkid));
}

function ringsOf(feature) {
  const g = feature.geometry;
  if (!g) return [];
  if (Array.isArray(g.rings)) return g.rings;
  if (g.type === 'Polygon') return g.coordinates;
  if (g.type === 'MultiPolygon') return g.coordinates.flat();
  return [];
}

function geoidOf(feature) {
  const attrs = feature.attributes ?? feature.properties ?? {};
  const geoid = String(attrs.GEOID ?? '').trim();
  if (geoid) return geoid;
  const { STATE, COUNTY, TRACT } = attrs;
  if (STATE == null || COUNTY == null || TRACT == null) return '';
  return `${String(STATE).padStart(2, '0')}${String(COUNTY).padStart(3, '0')}${String(TRACT).padStart(6, '0')}`;
}

/** Builds a lookup from a parsed tract file. Exported for tests. */
export function buildTractIndex(collection) {
  const project = needsProjection(collection.spatialReference);
  const tracts = [];
  for (const feature of collection.features ?? []) {
    const geoid = geoidOf(feature);
    const rings = ringsOf(feature).filter((r) => r.length >= 4);
    if (!geoid || !rings.length) continue;
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    for (const ring of rings) {
      for (const [x, y] of ring) {
        if (x < minX) minX = x;
        if (y < minY) minY = y;
        if (x > maxX) maxX = x;
        if (y > maxY) maxY = y;
      }
    }
    tracts.push({ geoid, rings, bbox: [minX, minY, maxX, maxY] });
  }

  return function lookup(lng, lat) {
    if (!Number.isFinite(lng) || !Number.isFinite(lat)) return null;
    const [x, y] = project ? lngLatToWebMercator(lng, lat) : [lng, lat];
    for (const tract of tracts) {
      const [minX, minY, maxX, maxY] = tract.bbox;
      if (x < minX || x > maxX || y < minY || y > maxY) continue;
      // Even-odd rule over every ring treats holes correctly without
      // needing to know ring orientation.
      let inside = false;
      for (const ring of tract.rings) {
        for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
          const [xi, yi] = ring[i];
          const [xj, yj] = ring[j];
          if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
        }
      }
      if (inside) return tract.geoid;
    }
    return null;
  };
}

export function loadTractLookup(fetchImpl = fetch) {
  if (!indexPromise) {
    indexPromise = fetchImpl(TRACTS_URL)
      .then((res) => {
        if (!res.ok) throw new Error(`Could not load census tracts (${res.status})`);
        return res.json();
      })
      .then(buildTractIndex)
      .catch((err) => {
        indexPromise = null;
        throw err;
      });
  }
  return indexPromise;
}
