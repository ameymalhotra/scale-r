import { FIELDS } from './fieldSchema.js';

const COMPARED_KEYS = FIELDS.map((f) => f.key);

function normalize(value) {
  if (value == null) return null;
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  const text = String(value).trim();
  return text === '' ? null : text;
}

export function valuesEqual(a, b) {
  return normalize(a) === normalize(b);
}

/**
 * Compares two row lists by `id`.
 * Returns { added: row[], removed: row[], modified: { id, before, after, fields: string[] }[] }.
 */
export function diffRows(baseRows, nextRows) {
  const base = new Map(baseRows.map((r) => [r.id, r]));
  const next = new Map(nextRows.map((r) => [r.id, r]));

  const added = [];
  const modified = [];
  for (const [id, after] of next) {
    const before = base.get(id);
    if (!before) {
      added.push(after);
      continue;
    }
    const fields = COMPARED_KEYS.filter((key) => !valuesEqual(before[key], after[key]));
    if (fields.length) modified.push({ id, before, after, fields });
  }

  const removed = [];
  for (const [id, before] of base) {
    if (!next.has(id)) removed.push(before);
  }

  return { added, removed, modified };
}

export function diffCount(diff) {
  return diff.added.length + diff.removed.length + diff.modified.length;
}
