import { describe, expect, it } from 'vitest';
import { rowHasErrors, validateRows } from './validation.js';

const validRow = (overrides = {}) => ({
  id: 1,
  implementa: 'SCALER-0001',
  project_na: 'Emergency generator',
  latitude: 25.95,
  longitude: -80.14,
  infrastruc: 'Gray Infrastructure',
  disaster_f: 'Flooding',
  project_status: 'Completed',
  additional: 'Parcel',
  estimated_cost: 550000,
  ...overrides,
});

describe('validateRows', () => {
  it('accepts a complete row inside Miami-Dade', () => {
    const result = validateRows([validRow()]);
    expect(result.errorRows).toBe(0);
    expect(result.warningRows).toBe(0);
    expect(result.byId.size).toBe(0);
  });

  it('requires a project name and project ID', () => {
    const result = validateRows([validRow({ project_na: '  ', implementa: null })]);
    expect(result.byId.get(1).errors).toMatchObject({
      project_na: expect.any(String),
      implementa: expect.any(String),
    });
  });

  it('flags duplicate project IDs case-insensitively on every copy', () => {
    const result = validateRows([validRow({ id: 1 }), validRow({ id: 2, implementa: 'scaler-0001 ' })]);
    expect(rowHasErrors(result, 1)).toBe(true);
    expect(rowHasErrors(result, 2)).toBe(true);
    expect(result.byId.get(2).errors.implementa).toMatch(/already uses/);
  });

  it('rejects coordinates outside the county and non-numeric input', () => {
    const outside = validateRows([validRow({ latitude: 27.9, longitude: -82.4 })]);
    expect(outside.byId.get(1).errors.latitude).toMatch(/outside Miami-Dade/);
    expect(outside.byId.get(1).errors.longitude).toMatch(/outside Miami-Dade/);

    const text = validateRows([validRow({ latitude: '25.9x', estimated_cost: 'about a million' })]);
    expect(text.byId.get(1).errors.latitude).toMatch(/must be a number/);
    expect(text.byId.get(1).errors.estimated_cost).toMatch(/must be a number/);
  });

  it('warns (without blocking) when the map would hide the row or a filter value is new', () => {
    const result = validateRows([
      validRow({ estimated_cost: 0, infrastruc: 'Nature-based', additional: 'Block' }),
    ]);
    const issues = result.byId.get(1);
    expect(Object.keys(issues.errors)).toHaveLength(0);
    expect(issues.warnings.estimated_cost).toMatch(/hides/);
    expect(issues.warnings.infrastruc).toMatch(/Live tool page/);
    expect(issues.warnings.additional).toMatch(/not one of the usual values/);
    expect(result.errorRows).toBe(0);
    expect(result.warningRows).toBe(1);
  });
});
