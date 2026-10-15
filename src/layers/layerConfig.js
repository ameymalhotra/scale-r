/**
 * Uploaded modelling layers, edited on /admin/layers and published to
 * project-data/layers_config.json. Each layer's GeoJSON lives in the same
 * bucket under layers/; the config only holds its path, its attribute fields
 * and how to draw it (symbology).
 *
 * Shared by the admin page (editing, preview) and the public map (rendering,
 * legend), so both always draw a layer the same way.
 */

import { symbolImageId, SYMBOL_IDS } from './layerSymbols.js';
import { BUILTIN_LAYER_REGISTRY, DEFAULT_MODELLING_ORDER, builtinDefinition } from './builtinRegistry.js';

export const LAYERS_CONFIG_FILE = 'layers_config.json';
export const LAYER_FILE_PREFIX = 'layers/';
export const MAX_LAYER_FILE_BYTES = 25 * 1024 * 1024;
export const MAX_CATEGORIES = 50;
export const MAX_CLASSES = 9;

export const GEOMETRY_TYPES = ['polygon', 'line', 'point'];
export const SYMBOLOGY_MODES = ['single', 'categorized', 'graduated'];
export const CLASS_METHODS = ['quantile', 'equal', 'manual'];

export const GEOMETRY_LABELS = { polygon: 'Polygons', line: 'Lines', point: 'Points' };
export const MODE_LABELS = { single: 'Single color', categorized: 'Categorized', graduated: 'Graduated' };
export const METHOD_LABELS = { quantile: 'Quantile (equal count)', equal: 'Equal interval', manual: 'Manual breaks' };

/** Sequential and diverging ramps for graduated layers, light to dark. */
export const COLOR_RAMPS = {
  blues: { label: 'Blues', colors: ['#eff3ff', '#bdd7e7', '#6baed6', '#3182bd', '#08519c'] },
  greens: { label: 'Greens', colors: ['#edf8e9', '#bae4b3', '#74c476', '#31a354', '#006d2c'] },
  reds: { label: 'Reds', colors: ['#fee5d9', '#fcae91', '#fb6a4a', '#de2d26', '#a50f15'] },
  purples: { label: 'Purples', colors: ['#f2f0f7', '#cbc9e2', '#9e9ac8', '#756bb1', '#54278f'] },
  oranges: { label: 'Oranges', colors: ['#feedde', '#fdbe85', '#fd8d3c', '#e6550d', '#a63603'] },
  ylorrd: { label: 'Yellow to red', colors: ['#ffffb2', '#fecc5c', '#fd8d3c', '#f03b20', '#bd0026'] },
  viridis: { label: 'Viridis', colors: ['#fde725', '#5ec962', '#21918c', '#3b528b', '#440154'] },
  rdylgn: { label: 'Red to green', colors: ['#d7191c', '#fdae61', '#ffffbf', '#a6d96a', '#1a9641'] },
  spectral: { label: 'Spectral', colors: ['#d7191c', '#fdae61', '#ffffbf', '#abdda4', '#2b83ba'] },
};

/** Distinct colors for categorized layers, assigned in order. */
export const CATEGORY_PALETTE = [
  '#1f77b4',
  '#ff7f0e',
  '#2ca02c',
  '#d62728',
  '#9467bd',
  '#8c564b',
  '#e377c2',
  '#7f7f7f',
  '#bcbd22',
  '#17becf',
  '#393b79',
  '#e7ba52',
];

export const DEFAULT_STYLE = Object.freeze({
  opacity: 0.7,
  outlineColor: '#1b3a4b',
  outlineWidth: 0.5,
  lineWidth: 2,
  pointSize: 14,
  symbol: 'circle',
});

export const DEFAULT_SYMBOLOGY = Object.freeze({
  mode: 'single',
  label: '',
  color: '#3182bd',
  field: '',
  categories: [],
  otherColor: '#bdbdbd',
  showOther: false,
  method: 'quantile',
  classCount: 5,
  ramp: 'blues',
  classes: [],
});


const HEX_COLOR = /^#[0-9a-f]{6}$/i;
export const isHexColor = (value) => typeof value === 'string' && HEX_COLOR.test(value);

const LAYER_ID = /^[a-z0-9][a-z0-9-]{0,63}$/;
const LAYER_FILE = /^layers\/[A-Za-z0-9._-]+\.geojson$/;

const clean = (value) => (value == null ? '' : String(value).trim());
const clamp = (value, min, max, fallback) => {
  const n = Number(value);
  return Number.isFinite(n) ? Math.min(max, Math.max(min, n)) : fallback;
};
const color = (value, fallback) => (isHexColor(value) ? value.toLowerCase() : fallback);

export const cloneConfig = (config) => JSON.parse(JSON.stringify(config));

const sortedKeys = (value) => {
  if (Array.isArray(value)) return value.map(sortedKeys);
  if (!value || typeof value !== 'object') return value;
  return Object.fromEntries(Object.keys(value).sort().map((k) => [k, sortedKeys(value[k])]));
};

/** Deep equality that ignores key order. */
export const sameLayerSettings = (a, b) => JSON.stringify(sortedKeys(a)) === JSON.stringify(sortedKeys(b));

/** `custom:<id>`, the Modelling Layer switch value the public map uses for a layer. */
export const layerView = (id) => `custom:${id}`;
export const viewLayerId = (view) => (typeof view === 'string' && view.startsWith('custom:') ? view.slice(7) : null);

export function newLayerId() {
  const random =
    typeof crypto !== 'undefined' && crypto.randomUUID
      ? crypto.randomUUID().replace(/-/g, '').slice(0, 12)
      : Math.random().toString(36).slice(2, 14);
  return `layer-${random}`;
}

/** Public URL of a layer file in the project-data bucket. */
export function layerFileUrl(supabaseUrl, file) {
  const path = file.split('/').map(encodeURIComponent).join('/');
  return `${supabaseUrl}/storage/v1/object/public/project-data/${path}`;
}

// ── Normalizing ─────────────────────────────────────────────────────────────

function normalizeFields(raw) {
  const fields = [];
  const seen = new Set();
  for (const entry of Array.isArray(raw) ? raw : []) {
    const name = clean(entry?.name);
    if (!name || seen.has(name)) continue;
    seen.add(name);
    fields.push({ name, type: entry.type === 'number' ? 'number' : 'string' });
  }
  return fields;
}

function normalizeSymbology(raw, fieldNames) {
  const s = raw && typeof raw === 'object' ? raw : {};
  const mode = SYMBOLOGY_MODES.includes(s.mode) ? s.mode : 'single';
  const field = fieldNames.has(clean(s.field)) ? clean(s.field) : '';

  const categories = [];
  const seenValues = new Set();
  for (const c of Array.isArray(s.categories) ? s.categories : []) {
    if (!c || typeof c !== 'object' || c.value == null) continue;
    const value = String(c.value);
    if (seenValues.has(value)) continue;
    seenValues.add(value);
    const category = { value, color: color(c.color, DEFAULT_SYMBOLOGY.otherColor) };
    const label = clean(c.label);
    if (label) category.label = label;
    if (SYMBOL_IDS.includes(c.symbol)) category.symbol = c.symbol;
    categories.push(category);
    if (categories.length >= MAX_CATEGORIES) break;
  }

  const classes = [];
  for (const c of Array.isArray(s.classes) ? s.classes : []) {
    const min = Number(c?.min);
    const max = Number(c?.max);
    if (!Number.isFinite(min) || !Number.isFinite(max)) continue;
    const entry = { min, max, color: color(c.color, DEFAULT_SYMBOLOGY.color) };
    const label = clean(c.label);
    if (label) entry.label = label;
    classes.push(entry);
    if (classes.length >= MAX_CLASSES) break;
  }
  classes.sort((a, b) => a.min - b.min);

  return {
    mode,
    label: clean(s.label),
    color: color(s.color, DEFAULT_SYMBOLOGY.color),
    field,
    categories,
    otherColor: color(s.otherColor, DEFAULT_SYMBOLOGY.otherColor),
    showOther: s.showOther === true,
    method: CLASS_METHODS.includes(s.method) ? s.method : DEFAULT_SYMBOLOGY.method,
    classCount: Math.round(clamp(s.classCount, 2, MAX_CLASSES, DEFAULT_SYMBOLOGY.classCount)),
    ramp: COLOR_RAMPS[s.ramp] ? s.ramp : DEFAULT_SYMBOLOGY.ramp,
    classes,
  };
}

function normalizeStyle(raw) {
  const s = raw && typeof raw === 'object' ? raw : {};
  return {
    opacity: clamp(s.opacity, 0, 1, DEFAULT_STYLE.opacity),
    outlineColor: color(s.outlineColor, DEFAULT_STYLE.outlineColor),
    outlineWidth: clamp(s.outlineWidth, 0, 10, DEFAULT_STYLE.outlineWidth),
    lineWidth: clamp(s.lineWidth, 0.5, 20, DEFAULT_STYLE.lineWidth),
    pointSize: clamp(s.pointSize, 4, 48, DEFAULT_STYLE.pointSize),
    symbol: SYMBOL_IDS.includes(s.symbol) ? s.symbol : DEFAULT_STYLE.symbol,
  };
}

export function normalizeLayer(raw) {
  if (!raw || typeof raw !== 'object') return null;
  const id = clean(raw.id);
  const file = clean(raw.file);
  if (!LAYER_ID.test(id) || !LAYER_FILE.test(file)) return null;
  if (!GEOMETRY_TYPES.includes(raw.geometry)) return null;

  const fields = normalizeFields(raw.fields);
  const fieldNames = new Set(fields.map((f) => f.name));
  const popupRaw = raw.popup && typeof raw.popup === 'object' ? raw.popup : {};
  return {
    id,
    label: clean(raw.label),
    description: clean(raw.description),
    file,
    geometry: raw.geometry,
    featureCount: Math.max(0, Math.round(Number(raw.featureCount) || 0)),
    fields,
    visible: raw.visible !== false,
    popup: {
      titleField: fieldNames.has(clean(popupRaw.titleField)) ? clean(popupRaw.titleField) : '',
      fields: [...new Set((Array.isArray(popupRaw.fields) ? popupRaw.fields : []).map(clean))].filter((f) =>
        fieldNames.has(f),
      ),
    },
    style: normalizeStyle(raw.style),
    symbology: normalizeSymbology(raw.symbology, fieldNames),
  };
}

/** Turns anything (a fetched file, a database row, null) into a usable config. */
export function normalizeLayerConfig(raw) {
  if (!raw || typeof raw !== 'object') raw = {};
  const layers = [];
  const seen = new Set();
  for (const entry of Array.isArray(raw.layers) ? raw.layers : []) {
    const layer = normalizeLayer(entry);
    if (!layer || builtinDefinition(layer.id) || seen.has(layer.id)) continue;
    seen.add(layer.id);
    layers.push(layer);
  }
  const overrides = new Map((Array.isArray(raw.builtins) ? raw.builtins : []).map((l) => [l?.id, l]));
  const builtins = BUILTIN_LAYER_REGISTRY.map((definition) => {
    const saved = overrides.get(definition.id) ?? {};
    const symbology = { ...definition.symbology, ...saved.symbology, mode: definition.symbology.mode, field: definition.symbology.field };
    // Recolor/relabel scientific classes, never redefine their values.
    if (definition.symbology.categories) {
      symbology.categories = definition.symbology.categories.map((c) => ({ ...c, ...(saved.symbology?.categories?.find((s) => s.value === c.value) ?? {}), value: c.value }));
    }
    return normalizeLayer({ ...definition, ...saved, id: definition.id, file: definition.file, geometry: definition.geometry, fields: definition.fields, symbology, style: { ...definition.style, ...saved.style } });
  });
  const known = new Set([...DEFAULT_MODELLING_ORDER, ...layers.map((l) => l.id)]);
  const order = [...new Set([...(Array.isArray(raw.order) ? raw.order : []), ...DEFAULT_MODELLING_ORDER, ...layers.map((l) => l.id)])].filter((id) => known.has(id));
  const overlayOrder = [...new Set([...(Array.isArray(raw.overlayOrder) ? raw.overlayOrder : []), ...builtins.filter((l) => builtinDefinition(l.id)?.parent).map((l) => l.id)])].filter((id) => builtinDefinition(id)?.parent);
  return { layers, builtins, order, overlayOrder };
}

export const EMPTY_LAYER_CONFIG = Object.freeze(normalizeLayerConfig(null));

/** Problems that block saving or publishing. Empty when the config is fine. */
export function validateLayerConfig(config) {
  const errors = [];
  const labels = new Map();
  for (const layer of [...(config?.builtins ?? []), ...(config?.layers ?? [])]) {
    const label = clean(layer.label);
    const name = label || layer.id;
    if (!label) errors.push(`A layer (${layer.file}) has no name.`);
    else if (label.length > 60) errors.push(`"${name}" is longer than 60 characters.`);
    const key = label.toLowerCase();
    if (label && labels.has(key)) errors.push(`Two layers are named "${label}".`);
    labels.set(key, true);

    const s = layer.symbology;
    const field = layer.fields.find((f) => f.name === s.field);
    if (s.mode !== 'single' && !field) errors.push(`"${name}" needs an attribute to color by.`);
    if (s.mode === 'categorized' && field && s.categories.length === 0) {
      errors.push(`"${name}" has no categories. Pick the attribute again to load its values.`);
    }
    if (s.mode === 'graduated' && field) {
      if (field.type !== 'number') errors.push(`"${name}" can only be graduated by a numeric attribute.`);
      if (s.classes.length === 0) errors.push(`"${name}" has no classes.`);
      s.classes.forEach((c, i) => {
        if (c.min > c.max) errors.push(`A class in "${name}" starts above where it ends.`);
        if (i > 0 && c.min <= s.classes[i - 1].min) errors.push(`Two classes in "${name}" start at the same value.`);
      });
    }
  }
  return errors;
}

// ── Reading GeoJSON ─────────────────────────────────────────────────────────

const GEOMETRY_FAMILY = {
  Point: 'point',
  MultiPoint: 'point',
  LineString: 'line',
  MultiLineString: 'line',
  Polygon: 'polygon',
  MultiPolygon: 'polygon',
};

/**
 * Checks an uploaded GeoJSON and describes it. Throws an Error with a
 * plain-language message when it cannot be used as a layer.
 * Returns { geometry, featureCount, fields }.
 */
export function inspectGeojson(data) {
  if (!data || typeof data !== 'object') throw new Error('The file is not valid GeoJSON.');
  if (data.type !== 'FeatureCollection' || !Array.isArray(data.features)) {
    throw new Error('The file must be a GeoJSON FeatureCollection.');
  }
  const families = new Set();
  const types = new Map();
  let featureCount = 0;
  for (const feature of data.features) {
    if (!feature?.geometry) continue;
    const family = GEOMETRY_FAMILY[feature.geometry.type];
    if (!family) throw new Error(`Geometry type "${feature.geometry.type}" is not supported.`);
    families.add(family);
    featureCount += 1;
    for (const [name, value] of Object.entries(feature.properties ?? {})) {
      if (value == null || value === '') continue;
      const isNumber = typeof value === 'number' || (typeof value === 'string' && parseStrictNumber(value) != null);
      const prev = types.get(name);
      types.set(name, prev === 'string' || !isNumber ? 'string' : 'number');
    }
    for (const name of Object.keys(feature.properties ?? {})) {
      if (!types.has(name)) types.set(name, 'empty');
    }
  }
  if (featureCount === 0) throw new Error('The file has no features with a geometry.');
  if (families.size > 1) {
    throw new Error(
      `The file mixes ${[...families].map((f) => GEOMETRY_LABELS[f].toLowerCase()).join(' and ')}. Upload one geometry type per layer.`,
    );
  }
  const fields = [...types].map(([name, type]) => ({ name, type: type === 'number' ? 'number' : 'string' }));
  return { geometry: [...families][0], featureCount, fields };
}

function parseStrictNumber(value) {
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  if (typeof value !== 'string' || value.trim() === '') return null;
  const n = Number(value.replace(/,/g, ''));
  return Number.isFinite(n) ? n : null;
}

/** Distinct values of a field with feature counts, most common first. */
export function uniqueValues(data, field) {
  const counts = new Map();
  for (const feature of data?.features ?? []) {
    const value = feature?.properties?.[field];
    if (value == null || value === '') continue;
    const key = String(value);
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  return [...counts]
    .map(([value, count]) => ({ value, count }))
    .sort((a, b) => b.count - a.count || a.value.localeCompare(b.value, undefined, { numeric: true }));
}

export function numericValues(data, field) {
  const values = [];
  for (const feature of data?.features ?? []) {
    const n = parseStrictNumber(feature?.properties?.[field]);
    if (n != null) values.push(n);
  }
  return values;
}

/** [[west, south], [east, north]] of every coordinate, or null when there are none. */
export function geojsonBounds(data) {
  let west = Infinity;
  let south = Infinity;
  let east = -Infinity;
  let north = -Infinity;
  const visit = (coords) => {
    if (!Array.isArray(coords)) return;
    if (typeof coords[0] === 'number') {
      const [x, y] = coords;
      if (!Number.isFinite(x) || !Number.isFinite(y)) return;
      west = Math.min(west, x);
      east = Math.max(east, x);
      south = Math.min(south, y);
      north = Math.max(north, y);
      return;
    }
    coords.forEach(visit);
  };
  for (const feature of data?.features ?? []) visit(feature?.geometry?.coordinates);
  return Number.isFinite(west) ? [[west, south], [east, north]] : null;
}

// ── Symbology helpers ───────────────────────────────────────────────────────

const hexToRgb = (hex) => [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
const rgbToHex = (rgb) => `#${rgb.map((v) => Math.round(v).toString(16).padStart(2, '0')).join('')}`;

/** `count` colors evenly spread along a ramp. */
export function rampColors(rampId, count) {
  const stops = (COLOR_RAMPS[rampId] ?? COLOR_RAMPS.blues).colors.map(hexToRgb);
  if (count <= 1) return [rgbToHex(stops[stops.length - 1])];
  return Array.from({ length: count }, (_, i) => {
    const t = (i / (count - 1)) * (stops.length - 1);
    const lo = Math.floor(t);
    const hi = Math.min(stops.length - 1, lo + 1);
    const f = t - lo;
    return rgbToHex(stops[lo].map((v, k) => v + (stops[hi][k] - v) * f));
  });
}

export const categoryColor = (index) => CATEGORY_PALETTE[index % CATEGORY_PALETTE.length];

/** Categories for the given values, keeping colors, labels and symbols already chosen. */
export function buildCategories(values, existing = []) {
  const byValue = new Map(existing.map((c) => [c.value, c]));
  return values.slice(0, MAX_CATEGORIES).map(({ value }, i) => byValue.get(value) ?? { value, color: categoryColor(i) });
}

const roundBreak = (n) => Number(n.toPrecision(6));

/**
 * Class ranges for a graduated layer.
 *   quantile  about the same number of features per class
 *   equal     the same width per class
 * Returns [{ min, max }] sorted, possibly fewer than `count` when values repeat.
 */
export function computeClasses(values, method, count) {
  const sorted = values.filter(Number.isFinite).sort((a, b) => a - b);
  if (!sorted.length) return [];
  const min = sorted[0];
  const max = sorted[sorted.length - 1];
  const n = Math.max(1, Math.min(MAX_CLASSES, Math.round(count)));
  if (min === max) return [{ min, max }];

  let breaks;
  if (method === 'equal') {
    breaks = Array.from({ length: n - 1 }, (_, i) => roundBreak(min + ((max - min) * (i + 1)) / n));
  } else {
    breaks = Array.from({ length: n - 1 }, (_, i) => roundBreak(sorted[Math.floor((sorted.length * (i + 1)) / n)]));
  }
  const edges = [...new Set([min, ...breaks.filter((b) => b > min && b < max), max])];
  return edges.slice(0, -1).map((lo, i) => ({ min: lo, max: edges[i + 1] }));
}

const formatNumber = (n) =>
  Math.abs(n) >= 1000 ? n.toLocaleString('en-US', { maximumFractionDigits: 0 }) : String(roundBreak(n));

export const classLabel = (c) => c.label || `${formatNumber(c.min)} – ${formatNumber(c.max)}`;
export const categoryLabel = (c) => c.label || c.value;

/** Classes for `ranges` colored along the ramp, keeping custom labels where the range is unchanged. */
export function colorClasses(ranges, rampId, existing = []) {
  const colors = rampColors(rampId, ranges.length);
  return ranges.map((r, i) => {
    const same = existing.find((c) => c.min === r.min && c.max === r.max);
    const entry = { min: r.min, max: r.max, color: colors[i] };
    if (same?.label) entry.label = same.label;
    return entry;
  });
}

// ── Mapbox ──────────────────────────────────────────────────────────────────

const valueAsString = (field) => ['to-string', ['get', field]];

/** Mapbox expression (or constant) for a layer's color. */
export function colorExpression(layer) {
  const s = layer.symbology;
  if (s.mode === 'categorized' && s.field && s.categories.length) {
    return ['match', valueAsString(s.field), ...s.categories.flatMap((c) => [c.value, c.color]), s.otherColor];
  }
  if (s.mode === 'graduated' && s.field && s.classes.length) {
    const [first, ...rest] = s.classes;
    const value = ['to-number', ['get', s.field], first.min];
    const step = ['step', value, first.color, ...rest.flatMap((c) => [c.min, c.color])];
    return ['case', ['==', ['get', s.field], null], s.otherColor, step];
  }
  return s.color;
}

/** Mapbox expression (or constant) for a point layer's symbol image. */
export function symbolExpression(layer) {
  const s = layer.symbology;
  const base = symbolImageId(layer.style.symbol);
  if (s.mode === 'categorized' && s.field && s.categories.some((c) => c.symbol && c.symbol !== layer.style.symbol)) {
    return [
      'match',
      valueAsString(s.field),
      ...s.categories.flatMap((c) => [c.value, symbolImageId(c.symbol ?? layer.style.symbol)]),
      base,
    ];
  }
  return base;
}

/** A symbol's shape is this many CSS pixels wide at icon-size 1 (see layerSymbols.js). */
export const SYMBOL_BASE_SIZE = 18;

export const mapLayerIds = (layer) => {
  if (layer.geometry === 'polygon') return [`${layer.id}-fill`, `${layer.id}-outline`];
  if (layer.geometry === 'line') return [`${layer.id}-line`];
  return [`${layer.id}-symbol`];
};

/** Mapbox layer specs that draw `layer` from the source named `sourceId`. */
export function buildMapboxLayers(layer, sourceId = layer.id, visibility = 'visible') {
  const { style } = layer;
  const fillColor = colorExpression(layer);
  const layout = { visibility };
  const vector = builtinDefinition(layer.id)?.sourceType === 'vector' ? { 'source-layer': builtinDefinition(layer.id).sourceLayer } : {};
  if (layer.geometry === 'polygon') {
    const isPolygon = ['any', ['==', ['geometry-type'], 'Polygon'], ['==', ['geometry-type'], 'MultiPolygon']];
    return [
      {
        id: `${layer.id}-fill`,
        type: 'fill',
        ...vector,
        source: sourceId,
        filter: isPolygon,
        layout: { ...layout },
        paint: { 'fill-color': fillColor, 'fill-opacity': style.opacity },
      },
      {
        id: `${layer.id}-outline`,
        type: 'line',
        ...vector,
        source: sourceId,
        filter: isPolygon,
        layout: { ...layout },
        paint: {
          'line-color': style.outlineColor,
          'line-width': style.outlineWidth,
          'line-opacity': style.outlineWidth > 0 ? Math.min(1, style.opacity + 0.2) : 0,
        },
      },
    ];
  }
  if (layer.geometry === 'line') {
    return [
      {
        id: `${layer.id}-line`,
        type: 'line',
        source: sourceId,
        filter: ['any', ['==', ['geometry-type'], 'LineString'], ['==', ['geometry-type'], 'MultiLineString']],
        layout: { ...layout, 'line-cap': 'round', 'line-join': 'round' },
        paint: { 'line-color': fillColor, 'line-width': style.lineWidth, 'line-opacity': style.opacity },
      },
    ];
  }
  return [
    {
      id: `${layer.id}-symbol`,
      type: 'symbol',
      source: sourceId,
      filter: ['any', ['==', ['geometry-type'], 'Point'], ['==', ['geometry-type'], 'MultiPoint']],
      layout: {
        ...layout,
        'icon-image': symbolExpression(layer),
        'icon-size': style.pointSize / SYMBOL_BASE_SIZE,
        'icon-allow-overlap': true,
        'icon-anchor': 'center',
      },
      paint: {
        'icon-color': fillColor,
        'icon-opacity': style.opacity,
        'icon-halo-color': style.outlineColor,
        'icon-halo-width': style.outlineWidth,
      },
    },
  ];
}

/**
 * Legend rows for a layer: [{ key, label, color, symbol }].
 * `kind` tells the renderer whether to draw a swatch, a line or a symbol.
 */
export function legendItems(layer) {
  const s = layer.symbology;
  const kind = layer.geometry === 'polygon' ? 'fill' : layer.geometry;
  const symbol = layer.style.symbol;
  const row = (key, label, fill, sym = symbol) => ({ key, label, color: fill, symbol: sym, kind });
  if (s.mode === 'categorized' && s.categories.length) {
    const rows = s.categories.map((c, i) => row(`c${i}`, categoryLabel(c), c.color, c.symbol ?? symbol));
    if (s.showOther) rows.push(row('other', 'Other', s.otherColor));
    return rows;
  }
  if (s.mode === 'graduated' && s.classes.length) {
    return s.classes.map((c, i) => row(`g${i}`, classLabel(c), c.color));
  }
  return [row('single', s.label || layer.label || 'Layer', s.color)];
}

const escapeHtml = (value) =>
  String(value).replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch]);

/** Popup HTML for a clicked feature, or null when the layer shows no popup. */
export function popupHtml(layer, properties) {
  const { titleField, fields } = layer.popup;
  if (!titleField && !fields.length) return null;
  const title = (titleField && properties?.[titleField]) || layer.label;
  const rows = fields
    .map((f) => {
      const raw = properties?.[f];
      const value = raw == null || raw === '' ? '—' : raw;
      return (
        `<tr><td style="color:#34495e;font-weight:600;padding:3px 8px 3px 0;vertical-align:top">${escapeHtml(f)}</td>` +
        `<td style="color:#2c3e50;padding:3px 0">${escapeHtml(value)}</td></tr>`
      );
    })
    .join('');
  return (
    `<div style="max-width:340px">` +
    `<div style="font-size:1.05em;font-weight:700;color:#2c3e50;margin-bottom:8px">${escapeHtml(title)}</div>` +
    (rows ? `<table style="width:100%;border-collapse:collapse;font-size:0.9em"><tbody>${rows}</tbody></table>` : '') +
    `</div>`
  );
}

/** Plain-language list of what publishing `next` would change compared with `live`. */
export function describeLayerChanges(live, next) {
  live = normalizeLayerConfig(live);
  next = normalizeLayerConfig(next);
  const changes = [];
  const liveLayers = [...live.builtins, ...live.layers];
  const nextLayers = [...next.builtins, ...next.layers];
  const liveById = new Map(liveLayers.map((l) => [l.id, l]));
  const nextIds = new Set(nextLayers.map((l) => l.id));
  for (const l of liveLayers) {
    if (!nextIds.has(l.id)) changes.push(`Remove the "${l.label}" layer`);
  }
  for (const l of nextLayers) {
    const before = liveById.get(l.id);
    if (!before) {
      changes.push(`Add the "${l.label}" layer${l.visible ? '' : ' (hidden)'}`);
      continue;
    }
    if (before.label !== l.label) changes.push(`Rename "${before.label}" to "${l.label}"`);
    if (before.visible !== l.visible) changes.push(`${l.visible ? 'Show' : 'Hide'} the "${l.label}" layer`);
    if (before.file !== l.file) changes.push(`Replace the data of "${l.label}"`);
    if (!sameLayerSettings(before.symbology, l.symbology) || !sameLayerSettings(before.style, l.style)) {
      changes.push(`Change the symbology of "${l.label}"`);
    }
    if (!sameLayerSettings(before.popup, l.popup) || before.description !== l.description) {
      changes.push(`Change the details of "${l.label}"`);
    }
  }
  const order = (config) => config.layers.filter((l) => liveById.has(l.id) && nextIds.has(l.id)).map((l) => l.id);
  if (JSON.stringify(order(live)) !== JSON.stringify(order(next))) changes.push('Change the order of the layers');
  const sharedOrder = (config) => config.order.filter((id) => live.order.includes(id) && next.order.includes(id));
  if (!sameLayerSettings(sharedOrder(live), sharedOrder(next))) changes.push('Change modelling switch order');
  if (!sameLayerSettings(live.overlayOrder, next.overlayOrder)) changes.push('Change infrastructure overlay order');
  return changes;
}

/** A new layer for an inspected upload. */
export function createLayer({ id, file, label, description, info }) {
  const firstText = info.fields.find((f) => f.type === 'string')?.name ?? '';
  return normalizeLayer({
    id,
    file,
    label,
    description,
    geometry: info.geometry,
    featureCount: info.featureCount,
    fields: info.fields,
    visible: true,
    popup: { titleField: firstText, fields: info.fields.slice(0, 6).map((f) => f.name) },
    style: { ...DEFAULT_STYLE, opacity: info.geometry === 'polygon' ? 0.6 : 0.9 },
    symbology: { ...DEFAULT_SYMBOLOGY },
  });
}
