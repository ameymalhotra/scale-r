// @vitest-environment node
/**
 * Parity: the browser engine must reproduce the Python model (D-199, D-200).
 *  1. Baseline: expected yearly damage today for every exported building, within 0.1% in total.
 *  2. Projects: every Part 2 run in parity_fixture.json (Python Module C), damage avoided within 1%
 *     (within $1 where Python gives $0).
 *  3. Building counts (D-218): physical buildings (records at the same NSI point) must match Python exactly.
 * Needs the private export in "Modelling Data from Web/outputs/admin_data/what_if/" (git-ignored, D-095).
 * Where it is missing the tests are skipped, not failed.
 */
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { gunzipSync } from 'node:zlib';
import { buildingId, computeRows, elevate, makeContext, picksForIds, readTile, seawall, seawallReasons } from './whatIfEngine.js';

const DIR = path.resolve(__dirname, '../../../../Modelling Data from Web/outputs/admin_data/what_if');
const HAVE = existsSync(path.join(DIR, 'manifest.json')) && existsSync(path.join(DIR, 'parity_fixture.json'));
const d = HAVE ? describe : describe.skip;

let man; let ctx; let tiles; let fixture;

function load() {
  if (tiles) return;
  man = JSON.parse(readFileSync(path.join(DIR, 'manifest.json'), 'utf8'));
  ctx = makeContext(man, JSON.parse(readFileSync(path.join(DIR, 'curves.json'), 'utf8')));
  tiles = new Map();
  for (const t of man.tiles) {
    const b = gunzipSync(readFileSync(path.join(DIR, t.file)));
    tiles.set(`${t.ix}_${t.iy}`, readTile(b.buffer.slice(b.byteOffset, b.byteOffset + b.length)));
  }
  fixture = JSON.parse(readFileSync(path.join(DIR, 'parity_fixture.json'), 'utf8'));
}

d('What-If engine parity with Python', () => {
  it('reproduces expected yearly damage today for every exported building', () => {
    load();
    const tot = { low: [0, 0], mid: [0, 0], high: [0, 0] };
    let worst = 0;
    for (const tile of tiles.values()) {
      const rows = Array.from({ length: tile.n }, (_, i) => i);
      const r = computeRows(tile, rows, ctx);
      for (const k of ['low', 'mid', 'high']) {
        for (let i = 0; i < tile.n; i += 1) {
          tot[k][0] += r[k][i];
          tot[k][1] += tile.cols[`eyd_${k}`][i];
          worst = Math.max(worst, Math.abs(r[k][i] - tile.cols[`eyd_${k}`][i]));
        }
      }
    }
    for (const k of ['low', 'mid', 'high']) expect(Math.abs(tot[k][0] - tot[k][1]) / tot[k][1]).toBeLessThan(0.001);
    expect(worst).toBeLessThan(5);
  });

  it('reproduces damage avoided for every Part 2 run within 1%', () => {
    load();
    const report = [];
    let largest = 0;
    for (const run of fixture.runs) {
      const res = run.kind === 'seawall'
        ? seawall(tiles, run.line, run.crest_ft, ctx)
        : elevate(tiles, picksForIds(tiles, run.fd_ids), run.raise_ft, ctx);
      for (const k of ['low', 'mid', 'high']) {
        const py = run.avoided[k];
        const js = res.avoided[k];
        const diff = Math.abs(js - py);
        const rel = py > 0 ? diff / py : 0;
        if (py > 0) largest = Math.max(largest, rel);
        report.push({ id: run.id, case: k, python: py, browser: js, difference: diff, relative: rel, ms: res.ms });
        if (py > 0) expect(rel, `${run.id} ${k}: Python ${py}, browser ${js}`).toBeLessThan(0.01);
        else expect(diff, `${run.id} ${k}: Python 0, browser ${js}`).toBeLessThan(1);
      }
      // building counts are whole numbers and must match exactly (D-218)
      expect(res.buildingsAffected, `${run.id}: buildings affected`).toBe(run.buildings_affected_python);
      expect(res.recordsAffected, `${run.id}: records affected`).toBe(run.records_affected_python);
      expect(res.buildingsProtected, `${run.id}: buildings protected`).toBe(run.buildings_protected_python);
    }
    writeFileSync(path.join(DIR, 'parity_result.json'), JSON.stringify({ runs: fixture.runs.length, largest_relative: largest, rows: report }, null, 1));
  });

  it('gives every building near each Part 2 wall the same reason as Python (D-204)', () => {
    load();
    let checked = 0;
    const mismatches = [];
    for (const run of fixture.runs.filter((r) => r.kind === 'seawall')) {
      const { items, counts } = seawallReasons(tiles, run.line, run.crest_ft, ctx);
      for (const [reason, n] of Object.entries(run.building_reason_counts)) {
        if (counts[reason] !== n) mismatches.push(`${run.id}: ${reason} buildings Python ${n}, browser ${counts[reason]}`);
      }
      const js = new Map(items.map((q) => [tiles.get(q.key).cols.fd_id[q.i], q.reason]));
      const py = new Map(run.reasons);
      for (const [fd, reason] of py) {
        checked += 1;
        if (js.get(fd) !== reason) mismatches.push(`${run.id}: building ${fd} Python ${reason}, browser ${js.get(fd)}`);
      }
      for (const fd of js.keys()) if (!py.has(fd)) mismatches.push(`${run.id}: building ${fd} only in the browser (${js.get(fd)})`);
    }
    expect(mismatches.slice(0, 10)).toEqual([]);
    expect(checked).toBeGreaterThan(1000);
    writeFileSync(path.join(DIR, 'reason_parity.json'), JSON.stringify({ checked, mismatches: mismatches.length }));
  });

  it('groups records into the same physical buildings as Python, countywide (D-218)', () => {
    load();
    const seen = new Set();
    let records = 0;
    for (const [key, tile] of tiles) for (let i = 0; i < tile.n; i += 1) { seen.add(buildingId(key, tile, i)); records += 1; }
    expect(records).toBe(fixture.county.flooding_records);
    expect(seen.size).toBe(fixture.county.flooding_buildings);
  });
});
