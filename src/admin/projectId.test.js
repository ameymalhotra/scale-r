import { describe, expect, it } from 'vitest';
import { nextProjectId } from './projectId.js';

describe('nextProjectId', () => {
  it('returns one above the highest SCALER id', () => {
    expect(nextProjectId(['SCALER-0001', 'SCALER-1664', 'SCALER-0020'])).toBe('SCALER-1665');
  });

  it('ignores blanks, other formats and case', () => {
    expect(nextProjectId([null, '', 'LMS-9999', ' scaler-0007 '])).toBe('SCALER-0008');
  });

  it('starts the series when there are no ids', () => {
    expect(nextProjectId([])).toBe('SCALER-0001');
  });

  it('grows past four digits', () => {
    expect(nextProjectId(['SCALER-9999'])).toBe('SCALER-10000');
  });
});
