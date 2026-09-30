import { describe, expect, it } from 'vitest';
import { diffCount, diffRows, valuesEqual } from './diff.js';

describe('valuesEqual', () => {
  it('treats blank, whitespace and null as the same value', () => {
    expect(valuesEqual(null, '')).toBe(true);
    expect(valuesEqual('  ', undefined)).toBe(true);
    expect(valuesEqual(' Miami ', 'Miami')).toBe(true);
    expect(valuesEqual(10, 10)).toBe(true);
    expect(valuesEqual(10, 11)).toBe(false);
  });
});

describe('diffRows', () => {
  const base = [
    { id: 1, project_na: 'Seawall', estimated_cost: 100, city: 'Miami' },
    { id: 2, project_na: 'Pump station', estimated_cost: 200 },
    { id: 3, project_na: 'Bioswale', estimated_cost: 300 },
  ];

  it('reports added, removed and field-level edits by id', () => {
    const next = [
      { id: 1, project_na: 'Seawall', estimated_cost: 150, city: 'Miami Beach' },
      { id: 3, project_na: 'Bioswale', estimated_cost: 300 },
      { id: 4, project_na: 'Living shoreline', estimated_cost: 50 },
    ];
    const diff = diffRows(base, next);

    expect(diff.added.map((r) => r.id)).toEqual([4]);
    expect(diff.removed.map((r) => r.id)).toEqual([2]);
    expect(diff.modified).toHaveLength(1);
    expect(diff.modified[0]).toMatchObject({ id: 1, fields: ['city', 'estimated_cost'] });
    expect(diffCount(diff)).toBe(3);
  });

  it('ignores columns outside the field schema (e.g. updated_at)', () => {
    const next = base.map((r) => ({ ...r, updated_at: '2026-09-29T00:00:00Z', updated_by: 'someone' }));
    expect(diffCount(diffRows(base, next))).toBe(0);
  });
});
