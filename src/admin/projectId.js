const PROJECT_ID_PATTERN = /^SCALER-(\d+)$/i;
const PREFIX = 'SCALER-';
const MIN_DIGITS = 4;

/** Next id in the SCALER-0001 series, one above the highest id in `ids`. */
export function nextProjectId(ids) {
  let max = 0;
  for (const id of ids) {
    if (id == null) continue;
    const match = PROJECT_ID_PATTERN.exec(String(id).trim());
    if (match) max = Math.max(max, Number(match[1]));
  }
  return `${PREFIX}${String(max + 1).padStart(MIN_DIGITS, '0')}`;
}
