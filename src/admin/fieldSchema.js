/**
 * One entry per project column shown in /admin, in display order.
 *
 *   key       column in projects_draft / projects_merged_conf1 (original
 *             shapefile-style names, kept as published)
 *   csv       header in SCALE-R_Database.csv (used for CSV export)
 *   type      'text' | 'longtext' | 'number' | 'url' | 'enum'
 *   options   known values for columns that drive a map filter. The editor
 *             offers them but accepts new text; new values are flagged because
 *             the map will not have a filter button for them yet.
 *   readOnly  derived columns the editor never writes directly
 */
export const FIELDS = [
  { key: 'implementa', csv: 'Project_ID', label: 'Project ID', type: 'text', width: 130, required: true },
  { key: 'project_na', csv: 'Project_Name', label: 'Project name', type: 'text', width: 280, required: true },
  { key: 'latitude', csv: 'Latitude', label: 'Latitude', type: 'number', width: 110, required: true },
  { key: 'longitude', csv: 'Longitude', label: 'Longitude', type: 'number', width: 110, required: true },
  { key: 'city', csv: 'Jurisdiction', label: 'Jurisdiction', type: 'text', width: 170 },
  { key: 'link_to_da', csv: 'Data_Source', label: 'Data source', type: 'url', width: 220 },
  {
    key: 'infrastruc',
    csv: 'Infrastructure_Type',
    label: 'Infrastructure type',
    type: 'enum',
    width: 170,
    filter: true,
    options: ['Blue Infrastructure', 'Green Infrastructure', 'Gray Infrastructure', 'Hybrid'],
  },
  {
    key: 'disaster_f',
    csv: 'Hazard_Focus',
    label: 'Hazard focus',
    type: 'enum',
    width: 170,
    filter: true,
    options: [
      'Flooding',
      'Storms & Hurricanes',
      'Coastal Hazards',
      'Extreme Heat',
      'Multi-Hazard',
      'Infrastructure Failure',
    ],
  },
  { key: 'new_15_25_', csv: 'Project_Description', label: 'Description', type: 'longtext', width: 320 },
  {
    key: 'project_status',
    csv: 'Project_Status',
    label: 'Status',
    type: 'enum',
    width: 120,
    filter: true,
    options: ['Completed', 'Ongoing', 'Funded', 'Planned'],
  },
  { key: 'status_category', csv: 'Status_Category', label: 'Status category', type: 'text', width: 140 },
  { key: 'estimated_cost', csv: 'Estimated_Cost', label: 'Estimated cost ($)', type: 'number', width: 140 },
  { key: 'project_st', csv: 'Reported_Year', label: 'Reported year', type: 'text', width: 110 },
  {
    key: 'additional',
    csv: 'Spatial_Resolution',
    label: 'Spatial resolution',
    type: 'enum',
    width: 140,
    options: ['Parcel', 'Corridor', 'Neighborhood', 'Municipality', 'County'],
  },
  { key: 'tract_geoid', csv: 'TRACT_GEOID', label: 'Census tract', type: 'text', width: 130, readOnly: true },
];

export const FIELD_BY_KEY = Object.fromEntries(FIELDS.map((f) => [f.key, f]));

export const EDITABLE_KEYS = FIELDS.filter((f) => !f.readOnly).map((f) => f.key);

/** Columns persisted to the database (everything in FIELDS plus the row id). */
export const ROW_KEYS = ['id', ...FIELDS.map((f) => f.key)];

export const DRAFT_SELECT = ROW_KEYS.join(', ');

export function emptyRow() {
  return Object.fromEntries(FIELDS.map((f) => [f.key, null]));
}

/** Converts raw editor input to the stored value for a field. */
export function parseFieldInput(field, raw) {
  if (raw == null) return null;
  const text = String(raw).trim();
  if (text === '') return null;
  if (field.type === 'number') {
    const n = Number(text.replace(/[$,\s]/g, ''));
    return Number.isFinite(n) ? n : text;
  }
  return text;
}

export function formatFieldValue(field, value) {
  if (value == null || value === '') return '';
  if (field.key === 'estimated_cost' && typeof value === 'number') {
    return value.toLocaleString('en-US', { maximumFractionDigits: 2 });
  }
  return String(value);
}

/** True when `value` is set but not one of the field's known options. */
export function isNewOption(field, value) {
  if (!field.options || value == null || value === '') return false;
  return !field.options.some((o) => o.toLowerCase() === String(value).trim().toLowerCase());
}
