/**
 * Settings for the project filters on the public map, edited on /admin/live-tool
 * and published to project-data/filters_config.json.
 *
 * The settings never create options. Each filter's options are the distinct
 * values in the live data; the settings only control how those values are
 * shown (label, color, definition, order, hidden). A setting whose value is no
 * longer in the data is kept but has no effect until the value comes back.
 */

export const FILTERS_CONFIG_FILE = 'filters_config.json';

// Canonical project status values from the dataset `Project__1` column.
export const PROJECT_STATUS_OPTIONS = ['Completed', 'Ongoing', 'Funded', 'Planned'];

export const PROJECT_STATUS_COLORS = {
  Completed: '#27ae60',
  Ongoing: '#b45309',
  Funded: '#0f766e',
  Planned: '#2563eb',
};

/** Preferred Infrastructure Type filter order (2×2 grid). */
export const INFRASTRUCTURE_TYPE_ORDER = ['Blue', 'Green', 'Gray', 'Hybrid'];

/** Pin and chart colors, matching getMarkerColor in utils/geoProcessing.js. */
export const INFRASTRUCTURE_TYPE_COLORS = {
  Blue: '#3498db',
  Green: '#27ae60',
  Gray: '#95a5a6',
  Hybrid: '#9b59b6',
};

export const DEFAULT_INFRASTRUCTURE_COLOR = '#95a5a6';

/** Definitions for the Infrastructure Type info icons. */
export const INFRASTRUCTURE_TYPE_DEFINITIONS = {
  Blue:
    'Blue infrastructure encompasses natural and engineered water-based systems that mitigate flooding, support adaptation to sea-level rise, improve water quality, and sustain diverse aquatic ecosystems.',
  Green:
    'Green infrastructure integrates vegetation, soils, and ecological processes to mitigate urban heat, manage stormwater, improve air and water quality, and support biodiversity.',
  Gray:
    'Gray infrastructure comprises conventional engineered systems constructed with materials such as concrete and steel to deliver essential urban services, including stormwater conveyance, flood control, and transportation.',
  Hybrid:
    'Hybrid infrastructure integrates elements of blue, green, and gray systems to deliver adaptive, multi-functional solutions.',
};

/**
 * Folds pre-Stage4 disaster focus names onto the current taxonomy so archived
 * exports filter alongside the hosted dataset.
 */
export const DISASTER_FOCUS_ALIASES = {
  'storm surge': 'storms & hurricanes',
  storms: 'storms & hurricanes',
  'critical infrastructure': 'infrastructure failure',
  'multi-hazard': 'multi-hazard',
};

/** Canonical display label for a disaster focus key. */
export const DISASTER_FOCUS_LABELS = {
  flooding: 'Flooding',
  'storms & hurricanes': 'Storms & Hurricanes',
  'coastal hazards': 'Coastal Hazards',
  'extreme heat': 'Extreme Heat',
  'multi-hazard': 'Multi-Hazard',
  'infrastructure failure': 'Infrastructure Failure',
};

/** Preferred Disaster Focus filter order; hazard types first, compound/systems last. */
export const DISASTER_FOCUS_ORDER = [
  'Flooding',
  'Storms & Hurricanes',
  'Coastal Hazards',
  'Extreme Heat',
  'Multi-Hazard',
  'Infrastructure Failure',
];

/**
 * The map's own filters. They can be hidden, renamed and reordered, not deleted.
 *   column    projects_merged_conf1 column (what /admin counts)
 *   property  GeoJSON property the map reads
 */
export const BUILT_IN_FILTERS = [
  { id: 'city', label: 'City', kind: 'dropdown', column: 'city', property: 'NAME' },
  { id: 'status', label: 'Project Status', kind: 'checkbox', column: 'project_status', property: 'Project__1', colors: true },
  {
    id: 'infrastructure',
    label: 'Infrastructure Type',
    kind: 'checkbox',
    column: 'infrastruc',
    property: 'Infrastruc',
    colors: true,
    definitions: true,
  },
  { id: 'disaster', label: 'Disaster Focus', kind: 'checkbox', column: 'disaster_f', property: 'Disaster_F' },
];

const BUILT_IN_BY_ID = new Map(BUILT_IN_FILTERS.map((f) => [f.id, f]));

/** Columns a custom filter can use: categorical and present in the public GeoJSON. */
export const CUSTOM_FILTER_COLUMNS = [
  { column: 'status_category', property: 'Status_Category', label: 'Status category' },
  { column: 'project_st', property: 'Project_St', label: 'Reported year' },
  { column: 'project_en', property: 'Project_En', label: 'Project end' },
  { column: 'additional', property: 'Additional', label: 'Spatial resolution' },
];

const CUSTOM_BY_COLUMN = new Map(CUSTOM_FILTER_COLUMNS.map((c) => [c.column, c]));

export const isBuiltInFilter = (id) => BUILT_IN_BY_ID.has(id);

const HEX_COLOR = /^#[0-9a-f]{6}$/i;
export const isHexColor = (value) => typeof value === 'string' && HEX_COLOR.test(value);

const clean = (value) => (value == null ? '' : String(value).trim());

const titleCase = (text) =>
  text
    .toLowerCase()
    .split(/\s+/)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');

const shortInfrastructureType = (text) => {
  const short = text.replace(/\s+infrastructure$/i, '').trim() || text;
  return /^grey$/i.test(short) ? 'Gray' : short;
};

const disasterKey = (text) => {
  const key = text.toLowerCase();
  return DISASTER_FOCUS_ALIASES[key] ?? key;
};

/** The label the map shows for a value when no custom label is set. */
export function defaultOptionLabel(filterId, value) {
  const text = clean(value);
  if (!text) return '';
  if (filterId === 'city') return titleCase(text);
  if (filterId === 'infrastructure') return shortInfrastructureType(text);
  if (filterId === 'disaster') return DISASTER_FOCUS_LABELS[disasterKey(text)] ?? text;
  if (filterId === 'status') {
    return PROJECT_STATUS_OPTIONS.find((s) => s.toLowerCase() === text.toLowerCase()) ?? text;
  }
  return text;
}

/**
 * Case-insensitive identity of a value within a filter, so "Blue Infrastructure"
 * and "Blue", or "Storms" and "Storms & Hurricanes", share one setting.
 */
export function optionKey(filterId, value) {
  const text = clean(value);
  if (!text) return '';
  if (filterId === 'disaster') return disasterKey(text);
  return defaultOptionLabel(filterId, text).toLowerCase();
}

export function defaultOptionColor(filterId, value) {
  const label = defaultOptionLabel(filterId, value);
  if (filterId === 'infrastructure') return INFRASTRUCTURE_TYPE_COLORS[label] ?? DEFAULT_INFRASTRUCTURE_COLOR;
  if (filterId === 'status') return PROJECT_STATUS_COLORS[label] ?? PROJECT_STATUS_COLORS.Ongoing;
  return undefined;
}

/** Built-in metadata (kind, column, property, colors, definitions) merged into a filter. */
export function filterSpec(filter) {
  const builtIn = BUILT_IN_BY_ID.get(filter.id);
  if (builtIn) return { ...builtIn, ...filter, kind: builtIn.kind, column: builtIn.column, property: builtIn.property };
  const custom = CUSTOM_BY_COLUMN.get(filter.column);
  return { kind: 'checkbox', ...filter, property: custom?.property };
}

export const DEFAULT_FILTER_CONFIG = Object.freeze({
  filters: [
    { id: 'city', label: 'City', visible: true, options: [] },
    {
      id: 'status',
      label: 'Project Status',
      visible: true,
      options: PROJECT_STATUS_OPTIONS.map((value) => ({ value, color: PROJECT_STATUS_COLORS[value], visible: true })),
    },
    {
      id: 'infrastructure',
      label: 'Infrastructure Type',
      visible: true,
      options: INFRASTRUCTURE_TYPE_ORDER.map((value) => ({
        value,
        color: INFRASTRUCTURE_TYPE_COLORS[value],
        definition: INFRASTRUCTURE_TYPE_DEFINITIONS[value],
        visible: true,
      })),
    },
    {
      id: 'disaster',
      label: 'Disaster Focus',
      visible: true,
      options: DISASTER_FOCUS_ORDER.map((value) => ({ value, visible: true })),
    },
  ],
});

export const cloneConfig = (config) => JSON.parse(JSON.stringify(config));

const sortedKeys = (value) => {
  if (Array.isArray(value)) return value.map(sortedKeys);
  if (!value || typeof value !== 'object') return value;
  return Object.fromEntries(Object.keys(value).sort().map((k) => [k, sortedKeys(value[k])]));
};

/** Deep equality that ignores key order, so an edited-then-reverted option still matches. */
export const sameSettings = (a, b) => JSON.stringify(sortedKeys(a)) === JSON.stringify(sortedKeys(b));

function normalizeOption(filterId, raw) {
  if (!raw || typeof raw !== 'object') return null;
  const value = clean(raw.value);
  if (!value) return null;
  const option = { value, visible: raw.visible !== false };
  const label = clean(raw.label);
  if (label) option.label = label;
  if (isHexColor(raw.color)) option.color = raw.color.toLowerCase();
  if (typeof raw.definition === 'string') option.definition = raw.definition.trim();
  return option;
}

/**
 * Turns anything (a fetched file, a database row, null) into a usable config.
 * Unknown or malformed entries are dropped; missing built-in filters are added
 * back with their defaults, so the map always has its four filters.
 */
export function normalizeFilterConfig(raw) {
  if (!raw || typeof raw !== 'object' || !Array.isArray(raw.filters)) return cloneConfig(DEFAULT_FILTER_CONFIG);

  const filters = [];
  const seenIds = new Set();
  const seenColumns = new Set();
  for (const entry of raw.filters) {
    if (!entry || typeof entry !== 'object') continue;
    const id = clean(entry.id);
    if (!id || seenIds.has(id)) continue;
    const builtIn = BUILT_IN_BY_ID.get(id);
    const column = builtIn ? builtIn.column : clean(entry.column);
    if (!builtIn && !CUSTOM_BY_COLUMN.has(column)) continue;
    if (seenColumns.has(column)) continue;

    const options = [];
    const seenKeys = new Set();
    for (const rawOption of Array.isArray(entry.options) ? entry.options : []) {
      const option = normalizeOption(id, rawOption);
      if (!option) continue;
      const key = optionKey(id, option.value);
      if (seenKeys.has(key)) continue;
      seenKeys.add(key);
      options.push(option);
    }

    const filter = {
      id,
      label: clean(entry.label) || builtIn?.label || CUSTOM_BY_COLUMN.get(column).label,
      visible: entry.visible !== false,
      options,
    };
    if (!builtIn) filter.column = column;
    filters.push(filter);
    seenIds.add(id);
    seenColumns.add(column);
  }

  for (const fallback of DEFAULT_FILTER_CONFIG.filters) {
    if (!seenIds.has(fallback.id)) filters.push(cloneConfig(fallback));
  }
  return { filters };
}

/** Problems that block publishing. Empty when the config is fine. */
export function validateFilterConfig(config) {
  const errors = [];
  const filters = config?.filters ?? [];
  if (!filters.some((f) => f.visible)) errors.push('At least one filter must be shown on the map.');
  for (const filter of filters) {
    const name = clean(filter.label) || filter.id;
    if (!clean(filter.label)) errors.push(`A filter (${filter.id}) has no name.`);
    if (filter.label && filter.label.length > 60) errors.push(`"${name}" is longer than 60 characters.`);
    for (const option of filter.options ?? []) {
      if (option.color != null && !isHexColor(option.color)) {
        errors.push(`"${option.value}" in "${name}" has an invalid color.`);
      }
      if (option.label && option.label.length > 80) {
        errors.push(`The label for "${option.value}" in "${name}" is longer than 80 characters.`);
      }
    }
  }
  return errors;
}

/**
 * Merges a filter's settings with the values found in the data.
 *   dataValues  [{ value, count }] in the order the map would list them when
 *               nothing is configured
 * Returns configured options first (in their saved order), then values that
 * have no settings yet. `inData` is false for settings whose value is gone.
 */
export function resolveOptions(filter, dataValues = []) {
  const byKey = new Map();
  for (const entry of dataValues) {
    const key = optionKey(filter.id, entry.value);
    if (key && !byKey.has(key)) byKey.set(key, entry);
  }

  const resolved = [];
  const seen = new Set();
  const build = (key, option, data) => {
    const value = data ? data.value : option.value;
    return {
      key,
      value,
      label: option?.label || defaultOptionLabel(filter.id, value),
      color: option?.color ?? defaultOptionColor(filter.id, value),
      definition: option?.definition ?? '',
      visible: option ? option.visible !== false : true,
      configured: Boolean(option),
      inData: Boolean(data),
      count: data?.count ?? 0,
    };
  };

  for (const option of filter.options ?? []) {
    const key = optionKey(filter.id, option.value);
    if (!key || seen.has(key)) continue;
    seen.add(key);
    resolved.push(build(key, option, byKey.get(key)));
  }
  for (const [key, data] of byKey) {
    if (seen.has(key)) continue;
    seen.add(key);
    resolved.push(build(key, null, data));
  }
  return resolved;
}

/** True when a setting only pins the value's place: shown, with no label, color or definition. */
export const isPlainOption = (option) =>
  option.visible !== false && Object.keys(option).every((k) => k === 'value' || k === 'visible');

/**
 * Drops trailing settings that change nothing (shown, no label, color or
 * definition, and in the place the value would take anyway), so switching a
 * value off and on again leaves the filter as it was. Settings whose key is in
 * `keep` (the live filter's) are left alone.
 */
export function compactOptions(filter, dataValues = [], keep = new Set()) {
  const order = (f) => resolveOptions(f, dataValues).map((o) => o.key).join('\n');
  const target = order(filter);
  let options = filter.options;
  while (options.length) {
    const last = options[options.length - 1];
    if (!isPlainOption(last) || keep.has(optionKey(filter.id, last.value))) break;
    const shorter = options.slice(0, -1);
    if (order({ ...filter, options: shorter }) !== target) break;
    options = shorter;
  }
  return options === filter.options ? filter : { ...filter, options };
}

/** Options the public map lists: shown and present in the data. */
export const mapOptions = (filter, dataValues) =>
  resolveOptions(filter, dataValues).filter((o) => o.visible && o.inData);

const orderIndex = (list, label) => {
  const i = list.findIndex((item) => item.toLowerCase() === label.toLowerCase());
  return i === -1 ? list.length : i;
};

/** Sort used for values that have no saved order, matching the map's own sort. */
export function compareDefaultOrder(filterId, a, b) {
  const la = defaultOptionLabel(filterId, a);
  const lb = defaultOptionLabel(filterId, b);
  const list =
    filterId === 'infrastructure'
      ? INFRASTRUCTURE_TYPE_ORDER
      : filterId === 'disaster'
        ? DISASTER_FOCUS_ORDER
        : filterId === 'status'
          ? PROJECT_STATUS_OPTIONS
          : null;
  if (list) {
    const diff = orderIndex(list, la) - orderIndex(list, lb);
    if (diff) return diff;
  }
  return la.localeCompare(lb, undefined, { sensitivity: 'base', numeric: true });
}

/** Plain-language list of what publishing `next` would change compared with `live`. */
export function describeFilterChanges(live, next) {
  const changes = [];
  const liveById = new Map(live.filters.map((f) => [f.id, f]));
  const nextIds = new Set(next.filters.map((f) => f.id));
  for (const f of live.filters) {
    if (!nextIds.has(f.id)) changes.push(`Remove the "${f.label}" filter`);
  }
  for (const f of next.filters) {
    const before = liveById.get(f.id);
    if (!before) {
      changes.push(`Add the "${f.label}" filter${f.visible ? '' : ' (hidden)'}`);
      continue;
    }
    if (before.label !== f.label) changes.push(`Rename "${before.label}" to "${f.label}"`);
    if (before.visible !== f.visible) changes.push(`${f.visible ? 'Show' : 'Hide'} the "${f.label}" filter`);
    if (!sameSettings(before.options, f.options)) {
      changes.push(`Change the values of "${f.label}"`);
    }
  }
  const order = (config) => config.filters.filter((f) => liveById.has(f.id) && nextIds.has(f.id)).map((f) => f.id);
  if (JSON.stringify(order(live)) !== JSON.stringify(order(next))) changes.push('Change the order of the filters');
  return changes;
}

/** Same rule as the map's loader: valid coordinates and a cost above zero. */
export function isShownOnMap(row) {
  const lat = Number(row.latitude);
  const lng = Number(row.longitude);
  if (row.latitude == null || row.longitude == null) return false;
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return false;
  if (lat === 0 && lng === 0) return false;
  if (Math.abs(lat) > 90 || Math.abs(lng) > 180) return false;
  const raw = row.estimated_cost;
  if (raw == null || raw === '') return false;
  const cost = typeof raw === 'string' ? parseFloat(raw.replace(/[$,]/g, '')) : Number(raw);
  return Number.isFinite(cost) && cost > 0;
}

function rowValue(spec, row) {
  if (spec.id === 'city') return clean(row.city || row.name);
  if (spec.id === 'status') return clean(row.project_status) || 'Ongoing';
  return clean(row[spec.column]);
}

/**
 * Distinct values of a filter's column among the rows the map shows, with
 * project counts, in default order. Used by /admin.
 */
export function countFilterValues(filter, rows) {
  const spec = filterSpec(filter);
  const counts = new Map();
  for (const row of rows) {
    if (!isShownOnMap(row)) continue;
    const value = rowValue(spec, row);
    if (!value || value === 'Null') continue;
    const key = optionKey(spec.id, value);
    const entry = counts.get(key);
    if (entry) entry.count += 1;
    else counts.set(key, { value, count: 1 });
  }
  return [...counts.values()].sort((a, b) => compareDefaultOrder(spec.id, a.value, b.value));
}
