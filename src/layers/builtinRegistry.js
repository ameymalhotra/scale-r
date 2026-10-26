// Source identities and scientific classes are fixed; presentation is published by admins.
const fields = (...names) => names.map((name) => ({ name, type: 'string' }));
const entry = (id, label, geometry, attributes, extra = {}) => ({
  id, label, geometry, file: `layers/builtin-${id}.geojson`, description: '',
  fields: fields(...attributes), featureCount: 0, visible: true,
  popup: { titleField: '', fields: attributes.slice(0, 6) },
  style: { opacity: 0.7, outlineColor: '#1b3a4b', outlineWidth: 0.5, lineWidth: 2, pointSize: 14, symbol: 'circle' },
  symbology: { mode: 'single', color: '#3182bd' }, ...extra,
});
const categorized = (field, values, colors) => ({
  mode: 'categorized', field, categories: values.map((value, i) => ({ value, label: value, color: colors[i] })),
  otherColor: '#9e9e9e', showOther: false,
});
export const RESILIENCE_COLORS = ['#e8d4f5', '#d4b3e8', '#c298db', '#a866c7', '#7a3fa8', '#5a1d85', '#2d0045'];
export const ELEVATION_BANDS = ['Below 0 ft', '0–2 ft', '2–4 ft', '4–6 ft', '6–10 ft', '10–20 ft', '20+ ft'];
const surgeValues = Array.from({ length: 21 }, (_, i) => i === 0 ? 'Less than 1 ft' : i === 20 ? 'Greater than 20 ft' : `${i}–${i + 1} ft`);
const surgeColors = surgeValues.map((_, i) => ['#d4eef9', '#92c5de', '#4393c3', '#2166ac', '#053061', '#762a83', '#c51b7d'][Math.min(6, Math.floor(i / 3))]);
const point = (id, label, filename, symbol) => entry(id, label, 'point', ['Name', 'Address', 'City', 'GEOID'], {
  sourcePath: filename, parent: 'critical-infrastructure',
  style: { opacity: 1, outlineColor: '#ffffff', outlineWidth: 0, pointSize: 14, symbol },
  symbology: { mode: 'single', color: '#111111' },
  popup: { titleField: 'Name', fields: ['Address', 'City'] },
});
export const BUILTIN_LAYER_REGISTRY = [
  entry('risk', 'FEMA Risk Rating', 'polygon', ['L0Census_Tracts.GEOID', '__riskRating', '__pred3PE', '__population'], {
    sourcePath: '/femaindex.geojson', census: true,
    style: { opacity: 0.5, outlineColor: '#777777', outlineWidth: 1 },
    symbology: categorized('__riskRating', ['Very Low', 'Relatively Low', 'Relatively Moderate', 'Relatively High', 'Very High'], ['#fff9c4', '#ffe082', '#ffb74d', '#ff8a65', '#e64a19']),
  }),
  entry('pred3pe', 'Resilience Index', 'polygon', ['L0Census_Tracts.GEOID', '__pred3PE', '__riskRating', '__population', '__resilienceColorStop'], {
    sourcePath: '/femaindex.geojson', census: true,
    style: { opacity: 0.6, outlineColor: '#777777', outlineWidth: 1 },
    symbology: categorized('__resilienceColorStop', ['Minimum (%)', '1/6 of range', '1/3 of range', 'Midpoint', '2/3 of range', '5/6 of range', 'Maximum (%)'], RESILIENCE_COLORS),
    popup: { titleField: '', fields: ['L0Census_Tracts.GEOID', '__pred3PE', '__riskRating', '__population'] },
  }),
  entry('critical-infrastructure', 'Critical Infrastructure', 'point', [], { group: true, style: { opacity: 1 }, description: 'Manage individual overlays below. Group opacity multiplies their opacity.' }),
  point('overlay-community-centers', 'Community Centers', 'Community Cent_FeaturesToJSO.geojson', 'people'),
  point('overlay-disaster-recovery', 'Disaster Recovery Centers', 'Disaster Recov_FeaturesToJSO.geojson', 'house'),
  point('overlay-emergency-medical', 'Emergency Medical', 'EmergencyMedical_FeaturesToJSO.geojson', 'cross'),
  point('overlay-emergency-ops', 'Emergency Operations Centers', 'Emergency Oper_FeaturesToJSO.geojson', 'cross'),
  entry('overlay-evacuation-routes', 'Evacuation Routes', 'line', ['NAME', 'GEOID', 'FEMAIndexR'], {
    sourcePath: 'Evacuation Rou_FeaturesToJSO.geojson', parent: 'critical-infrastructure',
    style: { opacity: 1, lineWidth: 3 }, symbology: { mode: 'single', color: '#34495e' },
  }),
  entry('overlay-military', 'Military Installations', 'polygon', ['NAME', 'GEOID', 'FEMAIndexR'], {
    sourcePath: 'MILITARY_FeaturesToJSO.geojson', parent: 'critical-infrastructure',
    style: { opacity: 0.42, outlineColor: '#111111', outlineWidth: 1 }, symbology: { mode: 'single', color: '#d9d9d9' },
    popup: { titleField: 'NAME', fields: ['GEOID', 'FEMAIndexR'] },
  }),
  point('overlay-risk-shelters', 'Risk Shelters', 'Risk Shelter I_FeaturesToJSO.geojson', 'house'),
  entry('sea-level-rise-4ft', 'Sea Level Rise — 4 ft', 'polygon', ['scenario', 'connection'], {
    sourcePath: '/layers/sea-level-rise-4ft.json', surface: true,
    sourceType: 'vector', tiles: '/layers/sea-level-rise-4ft/{z}/{x}/{y}.pbf', sourceLayer: 'surface', minzoom: 6, maxzoom: 14,
    description: 'NOAA ocean-connected inundation at 4 ft above Mean Higher High Water (MHHW). Unconnected low-lying areas are excluded.',
    style: { opacity: 0.65, outlineWidth: 0 }, symbology: { mode: 'single', color: '#2171b5' },
  }),
  entry('storm-surge-category-3', 'Storm Surge — Category 3', 'polygon', ['depth_range', 'scenario'], {
    sourcePath: '/layers/storm-surge-category-3.json', surface: true,
    sourceType: 'vector', tiles: '/layers/storm-surge-category-3/{z}/{x}/{y}.pbf', sourceLayer: 'surface', minzoom: 6, maxzoom: 14,
    description: 'NOAA/NHC SLOSH Category 3 maximum-of-maximums, high tide, June 2026. Depth above ground in feet; a composite scenario, not a single storm. Gray levee areas have no assessed hazard. Zoom in for finer surface detail.',
    style: { opacity: 0.7, outlineWidth: 0 },
    symbology: categorized('depth_range', [...surgeValues, 'Levee area — hazard not assessed'], [...surgeColors, '#9e9e9e']),
  }),
  entry('elevation', 'Elevation', 'polygon', ['elevation_band', 'vertical_datum', 'units'], {
    sourcePath: '/layers/elevation.json', surface: true,
    sourceType: 'vector', tiles: '/layers/elevation/{z}/{x}/{y}.pbf', sourceLayer: 'surface', minzoom: 6, maxzoom: 14,
    description: 'NOAA Southeast Florida 3 m DEM sampled on a ~6 m grid and displayed as smooth elevation bands in feet above NAVD88. NoData areas remain transparent. Zoom in for finer surface detail.',
    style: { opacity: 0.65, outlineWidth: 0 },
    symbology: categorized('elevation_band', ELEVATION_BANDS, ['#4575b4', '#91bfdb', '#e0f3f8', '#ffffbf', '#fee090', '#fc8d59', '#d73027']),
  }),
];
export const builtinDefinition = (id) => BUILTIN_LAYER_REGISTRY.find((layer) => layer.id === id);
export const builtinForFile = (file) => BUILTIN_LAYER_REGISTRY.find((layer) => layer.file === file);
export const DEFAULT_MODELLING_ORDER = BUILTIN_LAYER_REGISTRY.filter((layer) => !layer.parent).map((layer) => layer.id);

export function resilienceColorExpression(layer, stats) {
  const colors = layer.symbology.categories.map((c) => c.color);
  if (stats?.min == null || stats?.max == null) return layer.symbology.otherColor;
  const range = stats.max - stats.min;
  const color = range === 0 ? colors[colors.length - 1] : ['interpolate', ['linear'], ['get', '__pred3PE'], ...colors.flatMap((c, i) => [stats.min + range * i / (colors.length - 1), c])];
  return ['case', ['==', ['typeof', ['get', '__pred3PE']], 'number'], color, layer.symbology.otherColor];
}

export function modellingOptions(config) {
  const topLevel = [...config.builtins.filter((layer) => !builtinDefinition(layer.id)?.parent), ...config.layers];
  const byId = new Map(topLevel.map((layer) => [layer.id, layer]));
  return [{ view: 'none', label: 'No Layer', ariaLabel: 'No modelling layer' }, ...config.order.map((id) => byId.get(id)).filter((layer) => layer?.visible).map((layer) => ({
    view: builtinDefinition(layer.id)?.surface || !builtinDefinition(layer.id) ? `custom:${layer.id}` : layer.id,
    label: layer.label, ariaLabel: `${layer.label} layer`,
  }))];
}
