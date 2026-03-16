/**
 * Seed Supabase `projects_merged` table from MergedDataset_OurDB_plus_LMS.xlsx.
 * Does not touch the original `projects` table.
 *
 * Prerequisites:
 * - Create table projects_merged (same schema as projects) in Supabase SQL Editor.
 * - Set in .env: VITE_SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
 *
 * Run: npm run seed-merged
 */

import { createClient } from '@supabase/supabase-js';
import { readFileSync } from 'fs';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import * as XLSX from 'xlsx';

const __dirname = dirname(fileURLToPath(import.meta.url));

const supabaseUrl = process.env.VITE_SUPABASE_URL || process.env.SUPABASE_URL;
const supabaseKey =
  process.env.SUPABASE_SERVICE_ROLE_KEY ||
  process.env.VITE_SUPABASE_ANON_KEY ||
  process.env.SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseKey) {
  console.error(
    'Set VITE_SUPABASE_URL and either SUPABASE_SERVICE_ROLE_KEY (for seed) or VITE_SUPABASE_ANON_KEY'
  );
  process.exit(1);
}

const supabase = createClient(supabaseUrl, supabaseKey);

function trim(val) {
  if (val == null || val === '') return null;
  const s = String(val).trim();
  return s === '' ? null : s;
}

const INFRA_CANONICAL = {
  blue: 'Blue Infrastructure',
  'blue infrastructure': 'Blue Infrastructure',
  green: 'Green Infrastructure',
  'green infrastructure': 'Green Infrastructure',
  grey: 'Grey Infrastructure',
  'grey infrastructure': 'Grey Infrastructure',
  hybrid: 'Hybrid',
};

function normalizeInfrastruc(val) {
  const t = trim(val);
  if (!t) return null;
  return INFRA_CANONICAL[t.toLowerCase()] ?? t;
}

function parseNum(val) {
  if (val == null || val === '') return null;
  if (typeof val === 'number' && !Number.isNaN(val)) return val;
  const s = String(val).replace(/[$,]/g, '').trim();
  if (s === '') return null;
  const n = parseFloat(s);
  return Number.isFinite(n) ? n : null;
}

/**
 * Map one Excel row (object with Excel column names) to a row for projects_merged.
 * Returns null if row has invalid/missing coordinates (row is skipped).
 */
function mapExcelRowToDbRow(row) {
  const lat = parseNum(row.Latitude);
  const lng = parseNum(row.Longitude);
  if (lat == null || lng == null || !Number.isFinite(lat) || !Number.isFinite(lng)) {
    return null;
  }

  const projectEn = trim(row.Project_En);
  const projectEnNorm = projectEn === 'Null' || projectEn === 'null' ? null : projectEn;

  return {
    project_na: trim(row.Project_Na),
    name: trim(row.NAME),
    city: trim(row.City),
    latitude: lat,
    longitude: lng,
    infrastruc: normalizeInfrastruc(row.Infrastruc),
    categories: trim(row.Categories),
    disaster_f: trim(row.Disaster_F),
    new_15_25_: trim(row.New_15_25_),
    project_st: trim(row.Project_St),
    project_en: projectEnNorm,
    project_status: trim(row.Project__1),
    estimated_cost: parseNum(row.Estimated_),
    implementa: trim(row.Implementa),
    link_to_da: trim(row.Link_to_Da),
    additional: trim(row.Additional),
  };
}

async function seed() {
  const xlsxPath = join(__dirname, '..', '..', 'data', 'output', 'merged', 'MergedDataset_OurDB_plus_LMS.xlsx');
  const buf = readFileSync(xlsxPath);
  const workbook = XLSX.read(buf, { type: 'buffer' });

  const sheetName = workbook.SheetNames.find((n) => n === 'Projects') || workbook.SheetNames[0];
  const sheet = workbook.Sheets[sheetName];
  const rawRows = XLSX.utils.sheet_to_json(sheet, { defval: '' });

  const rows = rawRows.map(mapExcelRowToDbRow).filter(Boolean);
  const skipped = rawRows.length - rows.length;
  console.log(
    `Mapped ${rows.length} rows from ${rawRows.length} Excel rows (skipped ${skipped} without valid coordinates).`
  );

  if (rows.length === 0) {
    console.log('No rows to insert. Exiting.');
    return;
  }

  // Delete all existing rows so re-runs replace data instead of duplicating it
  const { error: delError } = await supabase
    .from('projects_merged')
    .delete()
    .neq('id', 0);
  if (delError) {
    console.error('Delete error:', delError);
    throw delError;
  }
  console.log('Cleared existing rows from projects_merged.');

  const BATCH = 50;
  for (let i = 0; i < rows.length; i += BATCH) {
    const chunk = rows.slice(i, i + BATCH);
    const { error } = await supabase.from('projects_merged').insert(chunk);
    if (error) {
      console.error('Insert error at batch', i, error);
      throw error;
    }
    console.log(`Inserted ${i + chunk.length}/${rows.length}`);
  }
  console.log('Seed done. Table: projects_merged');
}

seed().catch((e) => {
  console.error(e);
  process.exit(1);
});
