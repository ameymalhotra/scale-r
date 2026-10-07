import { FIELDS, isNewOption } from './fieldSchema.js';

/** Generous Miami-Dade County envelope (includes Biscayne Bay and the Keys edge). */
export const MIAMI_DADE_BOUNDS = { minLat: 25.1, maxLat: 26.0, minLng: -80.95, maxLng: -80.0 };

const isBlank = (v) => v == null || String(v).trim() === '';

function checkRow(row, duplicateIds) {
  const errors = {};
  const warnings = {};

  if (isBlank(row.project_na)) errors.project_na = 'Project name is required.';

  if (isBlank(row.implementa)) {
    errors.implementa = 'Project ID is required.';
  } else if (duplicateIds.has(String(row.implementa).trim().toLowerCase())) {
    errors.implementa = 'Another row already uses this Project ID.';
  }

  const lat = row.latitude;
  const lng = row.longitude;
  if (isBlank(lat)) errors.latitude = 'Latitude is required.';
  else if (typeof lat !== 'number' || !Number.isFinite(lat)) errors.latitude = 'Latitude must be a number.';
  else if (lat < MIAMI_DADE_BOUNDS.minLat || lat > MIAMI_DADE_BOUNDS.maxLat) {
    errors.latitude = 'Latitude is outside Miami-Dade County.';
  }
  if (isBlank(lng)) errors.longitude = 'Longitude is required.';
  else if (typeof lng !== 'number' || !Number.isFinite(lng)) errors.longitude = 'Longitude must be a number.';
  else if (lng < MIAMI_DADE_BOUNDS.minLng || lng > MIAMI_DADE_BOUNDS.maxLng) {
    errors.longitude = 'Longitude is outside Miami-Dade County.';
  }

  const cost = row.estimated_cost;
  if (!isBlank(cost)) {
    if (typeof cost !== 'number' || !Number.isFinite(cost)) {
      errors.estimated_cost = 'Estimated cost must be a number.';
    } else if (cost <= 0) {
      warnings.estimated_cost = 'The map hides projects whose cost is not above $0.';
    }
  } else {
    warnings.estimated_cost = 'The map hides projects without an estimated cost.';
  }

  for (const field of FIELDS) {
    if (isNewOption(field, row[field.key])) {
      warnings[field.key] = field.filter
        ? `"${row[field.key]}" is a new value. Once published it appears in the map filter; set its label and color on the Live tool page.`
        : `"${row[field.key]}" is not one of the usual values.`;
    }
  }

  return { errors, warnings };
}

function findDuplicateIds(rows) {
  const counts = new Map();
  for (const row of rows) {
    if (isBlank(row.implementa)) continue;
    const key = String(row.implementa).trim().toLowerCase();
    counts.set(key, (counts.get(key) ?? 0) + 1);
  }
  return new Set([...counts].filter(([, n]) => n > 1).map(([k]) => k));
}

/**
 * Validates every row. Returns a Map keyed by row id containing only rows that
 * have at least one error or warning, plus totals.
 */
export function validateRows(rows) {
  const duplicateIds = findDuplicateIds(rows);
  const byId = new Map();
  let errorRows = 0;
  let warningRows = 0;
  for (const row of rows) {
    const result = checkRow(row, duplicateIds);
    const hasErrors = Object.keys(result.errors).length > 0;
    const hasWarnings = Object.keys(result.warnings).length > 0;
    if (hasErrors) errorRows += 1;
    if (hasWarnings) warningRows += 1;
    if (hasErrors || hasWarnings) byId.set(row.id, result);
  }
  return { byId, errorRows, warningRows };
}

export function rowHasErrors(validation, id) {
  const result = validation.byId.get(id);
  return Boolean(result && Object.keys(result.errors).length);
}
