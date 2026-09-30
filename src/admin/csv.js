import { FIELDS } from './fieldSchema.js';

function escapeCell(value) {
  if (value == null) return '';
  const text = String(value);
  return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

/** Rows as CSV using the SCALE-R_Database.csv headers (plus Status_Category and TRACT_GEOID). */
export function rowsToCsv(rows) {
  const header = FIELDS.map((f) => f.csv).join(',');
  const lines = rows.map((row) => FIELDS.map((f) => escapeCell(row[f.key])).join(','));
  return [header, ...lines].join('\n');
}

export function downloadCsv(filename, rows) {
  const blob = new Blob([rowsToCsv(rows)], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
