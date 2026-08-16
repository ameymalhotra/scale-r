/**
 * Pure geometry / data-shaping helpers shared between the Dashboard component
 * and the data-parsing Web Worker.
 *
 * Everything here was lifted verbatim out of Dashboard.jsx so that the worker
 * and the main thread cannot drift apart: the worker now performs the parsing,
 * but it must produce byte-for-byte the same result the main thread used to.
 * Nothing in this module may touch the DOM, `window`, or mapbox-gl.
 */

export const parseNumericValue = (value) => {
  if (value === null || value === undefined) return null;
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  const cleaned = String(value).replace(/[^0-9eE.+-]/g, '');
  const parsed = Number(cleaned);
  return Number.isFinite(parsed) ? parsed : null;
};

export const toWgs84Coordinate = ([x, y]) => {
  const originShift = 20037508.34;
  const lon = (x / originShift) * 180;
  let lat = (y / originShift) * 180;
  lat = (180 / Math.PI) * (2 * Math.atan(Math.exp((lat * Math.PI) / 180)) - Math.PI / 2);
  return [lon, lat];
};

export const transformToWgs84 = (coords) => {
  if (!Array.isArray(coords)) return coords;
  if (typeof coords[0] === 'number' && typeof coords[1] === 'number') {
    return toWgs84Coordinate(coords);
  }
  return coords.map(transformToWgs84);
};

export const walkCoordinates = (geometry, callback) => {
  if (!geometry || !geometry.coordinates) return;
  const traverse = (coords) => {
    if (!Array.isArray(coords)) return;
    if (typeof coords[0] === 'number' && typeof coords[1] === 'number') {
      callback(coords);
      return;
    }
    coords.forEach(traverse);
  };
  traverse(geometry.coordinates);
};

export const reprojectFeatureCollectionIfNeeded = (featureCollection) => {
  if (!featureCollection?.features?.length) return featureCollection;
  let firstCoord = null;
  for (const feature of featureCollection.features) {
    if (!feature?.geometry) continue;
    walkCoordinates(feature.geometry, (coord) => {
      if (!firstCoord) firstCoord = coord;
    });
    if (firstCoord) break;
  }
  if (!firstCoord) return featureCollection;
  const needsReprojection = Math.abs(firstCoord[0]) > 180 || Math.abs(firstCoord[1]) > 90;
  if (!needsReprojection) return featureCollection;
  return {
    ...featureCollection,
    features: featureCollection.features.map((feature) => {
      if (!feature?.geometry) return feature;
      return {
        ...feature,
        geometry: {
          ...feature.geometry,
          coordinates: transformToWgs84(feature.geometry.coordinates)
        }
      };
    })
  };
};

export const getRangeStats = (values) => {
  if (!values.length) return { min: null, mid: null, max: null };
  const min = Math.min(...values);
  const max = Math.max(...values);
  const mid = min + (max - min) / 2;
  return { min, mid, max };
};

/**
 * Spread co-located markers into a circle so every project is visible.
 * Returns a Map<featureIndex, [lng, lat]> (original position kept for singletons).
 */
export const computeSpiderOffsets = (features, radiusMeters = 40) => {
  const groups = new Map();
  features.forEach((feature, index) => {
    const coords = feature.geometry?.coordinates;
    if (!coords) return;
    const key = `${coords[0]},${coords[1]}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(index);
  });

  const offsets = new Map();
  groups.forEach((indices, key) => {
    const [lng, lat] = key.split(',').map(Number);
    if (indices.length === 1) {
      offsets.set(indices[0], [lng, lat]);
      return;
    }
    const n = indices.length;
    indices.forEach((featureIndex, i) => {
      const angle = (i * 2 * Math.PI) / n - Math.PI / 2;
      const latOffset = (radiusMeters * Math.sin(angle)) / 111000;
      const lngOffset = (radiusMeters * Math.cos(angle)) / (111000 * Math.cos((lat * Math.PI) / 180));
      offsets.set(featureIndex, [lng + lngOffset, lat + latOffset]);
    });
  });

  return offsets;
};

/** Create a small circle polygon around a point to use as a buffer zone. */
export const createCircleBuffer = (center, radiusInMeters = 50) => {
  const [lng, lat] = center;
  const points = 32; // Number of points in the circle
  const circle = [];

  for (let i = 0; i <= points; i++) {
    const angle = (i * 360) / points;
    const dx = radiusInMeters * Math.cos((angle * Math.PI) / 180);
    const dy = radiusInMeters * Math.sin((angle * Math.PI) / 180);

    // Approximate conversion: 1 degree latitude ≈ 111,000 meters
    // 1 degree longitude ≈ 111,000 * cos(latitude) meters
    const latOffset = dy / 111000;
    const lngOffset = dx / (111000 * Math.cos((lat * Math.PI) / 180));

    circle.push([lng + lngOffset, lat + latOffset]);
  }

  return circle;
};

/** Canonicalize stored infrastructure type values to American English "Gray". */
export const canonicalizeInfrastructureTypeValue = (type) => {
  if (!type || typeof type !== 'string') return type;
  const trimmed = type.trim();
  if (/^grey$/i.test(trimmed)) return 'Gray';
  if (/^grey\s+infrastructure$/i.test(trimmed)) return 'Gray Infrastructure';
  if (/^gray$/i.test(trimmed)) return 'Gray';
  if (/^gray\s+infrastructure$/i.test(trimmed)) return 'Gray Infrastructure';
  return trimmed;
};

export const getMarkerColor = (projectType) => {
  switch (projectType) {
    case 'Blue Infrastructure':
    case 'Blue':
      return '#3498db';
    case 'Green Infrastructure':
    case 'Green':
      return '#27ae60';
    case 'Grey Infrastructure':
    case 'Grey':
    case 'Gray Infrastructure':
    case 'Gray':
      return '#95a5a6';
    case 'Hybrid':
      return '#9b59b6'; // Purple for hybrid infrastructure
    default:
      return '#95a5a6';
  }
};
