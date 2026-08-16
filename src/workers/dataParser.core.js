/**
 * The data-parsing work itself, with no worker plumbing.
 *
 * Kept separate from dataParser.worker.js so the same code can run either
 * inside the worker (in the browser) or directly in-process (under jsdom in
 * the test suite, which has no Worker implementation). See
 * src/test/setup.js, which drives runTask through a Worker stub.
 */

import {
  parseNumericValue,
  reprojectFeatureCollectionIfNeeded,
  getRangeStats,
  computeSpiderOffsets,
  createCircleBuffer,
  canonicalizeInfrastructureTypeValue,
  getMarkerColor,
} from '../utils/geoProcessing.js';

const toBlobUrl = (value) =>
  URL.createObjectURL(new Blob([JSON.stringify(value)], { type: 'application/json' }));

/* ------------------------------------------------------------------ projects */

// (0,0) is the "null island" placeholder used for ungeocoded projects.
const hasValidCoordinates = (feature) => {
  const coords = feature?.geometry?.coordinates;
  if (!Array.isArray(coords) || coords.length < 2) return false;
  const lng = Number(coords[0]);
  const lat = Number(coords[1]);
  if (!Number.isFinite(lng) || !Number.isFinite(lat)) return false;
  if (lng === 0 && lat === 0) return false;
  return Math.abs(lat) <= 90 && Math.abs(lng) <= 180;
};

async function loadProjects({ url }) {
  const response = await fetch(url, { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`Failed to load project data: ${response.status}`);
  }

  const data = await response.json();
  const allFeatures = data.features || [];

  // Dashboard-level display filters:
  //  1. exclude projects without valid coordinates (missing or 0,0 placeholders)
  //  2. show only projects with an estimated cost greater than zero
  const costFilteredFeatures = allFeatures
    .filter((feature) => {
      if (!hasValidCoordinates(feature)) return false;
      const props = feature?.properties || {};
      const rawCost = props['Estimated_'] ?? props['Estimated Project Cost'];
      if (rawCost == null || rawCost === '') return false;
      const numericCost =
        typeof rawCost === 'string' ? parseFloat(rawCost.replace(/[$,]/g, '')) : parseFloat(rawCost);
      return Number.isFinite(numericCost) && numericCost > 0;
    })
    .map((feature) => {
      const props = feature?.properties;
      if (!props) return feature;
      const next = { ...props };
      for (const key of ['Infrastruc', 'Infrastructure Type', 'Type']) {
        if (next[key] != null && next[key] !== '') {
          next[key] = canonicalizeInfrastructureTypeValue(next[key]);
        }
      }
      return { ...feature, properties: next };
    });

  const filteredData = { ...data, features: costFilteredFeatures };

  // Spider offsets so co-located projects get distinct marker positions.
  const spiderOffsets = computeSpiderOffsets(costFilteredFeatures, 40);

  const bufferFeatures = costFilteredFeatures.map((feature, index) => {
    const coordinates = spiderOffsets.get(index) || feature.geometry.coordinates;
    return {
      type: 'Feature',
      id: `marker-buffer-${index}`,
      geometry: {
        type: 'Polygon',
        coordinates: [createCircleBuffer(coordinates, 30)], // 30 metre radius buffer
      },
      properties: { markerIndex: index },
    };
  });

  // One spec per marker the main thread must create. Mirrors the original loop:
  // features without a usable Point geometry are skipped, and NAME / City are
  // trimmed in place on the properties that end up in React state.
  const markerSpecs = [];
  const skipped = [];
  costFilteredFeatures.forEach((feature, featureIndex) => {
    const geometry = feature.geometry;
    const coordinates = geometry && geometry.coordinates;
    if (
      !geometry ||
      geometry.type !== 'Point' ||
      !Array.isArray(coordinates) ||
      coordinates.length < 2 ||
      typeof coordinates[0] !== 'number' ||
      typeof coordinates[1] !== 'number' ||
      !Number.isFinite(coordinates[0]) ||
      !Number.isFinite(coordinates[1])
    ) {
      skipped.push(feature.id);
      return;
    }

    const properties = feature.properties;

    // Normalize city property by trimming whitespace (use NAME field, fallback to City)
    const cityField = properties['NAME'] || properties['City'];
    if (cityField) {
      if (properties['NAME']) properties['NAME'] = properties['NAME'].trim();
      if (properties['City']) properties['City'] = properties['City'].trim();
    }

    markerSpecs.push({
      featureIndex,
      lngLat: spiderOffsets.get(featureIndex) || coordinates,
      color: getMarkerColor(
        properties['Infrastruc'] || properties['Infrastructure Type'] || properties['Type']
      ),
    });
  });

  return {
    filteredData,
    markerSpecs,
    skipped,
    totalFeatureCount: allFeatures.length,
    keptFeatureCount: costFilteredFeatures.length,
    // Consumed only as mapbox source `data`, so they stay off the main thread.
    projectsSourceUrl: toBlobUrl(filteredData),
    bufferSourceUrl: toBlobUrl({ type: 'FeatureCollection', features: bufferFeatures }),
  };
}

/* -------------------------------------------------------------------- census */

/** Simple CSV parser that handles quoted fields (lifted from Dashboard.jsx). */
const parseCSVLine = (line) => {
  const result = [];
  let current = '';
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === ',' && !inQuotes) {
      result.push(current.trim());
      current = '';
    } else {
      current += char;
    }
  }
  result.push(current.trim());
  return result;
};

async function loadPred3PE(url) {
  const csvResponse = await fetch(url);
  if (!csvResponse.ok) return {};

  const csvText = await csvResponse.text();
  const lines = csvText.split('\n').filter((line) => line.trim());

  const headers = parseCSVLine(lines[0]);
  const geoIdIndex = headers.indexOf('GEO_ID');
  const pred3PEIndex = headers.indexOf('PRED3_PE');

  const pred3PEMap = {};
  for (let i = 1; i < lines.length; i++) {
    if (!lines[i].trim()) continue;
    const values = parseCSVLine(lines[i]);
    if (values.length > Math.max(geoIdIndex, pred3PEIndex)) {
      const geoId = values[geoIdIndex]?.trim();
      const pred3PE = parseFloat(values[pred3PEIndex]?.trim());
      if (geoId && !isNaN(pred3PE)) {
        // Convert "1400000US12086000107" to "12086000107"
        pred3PEMap[geoId.replace('1400000US', '')] = pred3PE;
      }
    }
  }
  return pred3PEMap;
}

async function loadCensus({ censusUrl, creUrl }) {
  // Both requests start together, but the CSV must be applied first: every
  // tract's __pred3PE is looked up from it by GEOID.
  const censusPromise = fetch(censusUrl).then((r) => {
    if (!r.ok) throw new Error(`Failed to load census tract data: ${r.status}`);
    return r.json();
  });

  let pred3PEData = {};
  let creError = null;
  try {
    pred3PEData = await loadPred3PE(creUrl);
  } catch (err) {
    creError = String(err);
  }

  const rawGeojson = await censusPromise;
  const reprojected = reprojectFeatureCollectionIfNeeded(rawGeojson);

  const processedFeatures = (reprojected.features || []).map((feature, index) => {
    const properties = { ...(feature.properties || {}) };
    const riskRating = properties['T_FEMA_National_Risk_Index_$_.FEMAIndexRating'] || null;
    const populationValue = parseNumericValue(
      properties[
        'T_CENSUS_Community_Resilience_Est$_.Total_population__excludes_adult_correctional_juvenile_facilitie'
      ]
    );
    const geoid = properties['L0Census_Tracts.GEOID'];
    const pred3PE = geoid ? pred3PEData[geoid] : null;

    return {
      ...feature,
      id: feature.id ?? geoid ?? index,
      properties: {
        ...properties,
        __riskRating: riskRating,
        __population: populationValue,
        __pred3PE: pred3PE !== null && pred3PE !== undefined ? pred3PE : null,
      },
    };
  });

  const riskRatings = processedFeatures
    .map((feature) => feature.properties.__riskRating)
    .filter((value) => value !== null && value !== undefined);
  const populationValues = processedFeatures
    .map((feature) => feature.properties.__population)
    .filter((value) => Number.isFinite(value));
  const pred3PEValues = processedFeatures
    .map((feature) => feature.properties.__pred3PE)
    .filter((value) => value !== null && value !== undefined && Number.isFinite(value));

  const statsPayload = {
    risk: { ratings: [...new Set(riskRatings)], count: riskRatings.length },
    population: getRangeStats(populationValues),
    pred3PE: getRangeStats(pred3PEValues),
    counts: {
      total: processedFeatures.length,
      missingRisk: processedFeatures.length - riskRatings.length,
      missingPopulation: processedFeatures.length - populationValues.length,
      missingPred3PE: processedFeatures.length - pred3PEValues.length,
    },
  };

  return {
    // Handed straight to mapbox as source data; the main thread never parses it.
    censusSourceUrl: toBlobUrl({ ...reprojected, features: processedFeatures }),
    statsPayload,
    pred3PECount: Object.keys(pred3PEData).length,
    creError,
  };
}

/* ------------------------------------------------------------------ dispatch */

const HANDLERS = {
  projects: loadProjects,
  census: loadCensus,
};

/** Run one named task. Throws if the task name is unknown. */
export async function runTask(task, payload) {
  const handler = HANDLERS[task];
  if (!handler) throw new Error(`unknown task: ${task}`);
  return handler(payload);
}
