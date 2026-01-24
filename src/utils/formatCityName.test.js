import { describe, it, expect } from 'vitest';

// Format city name to title case (first letter of each word capitalized)
const formatCityName = (cityName) => {
  if (!cityName || typeof cityName !== 'string') return cityName;
  return cityName
    .trim()
    .toLowerCase()
    .split(/\s+/)
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

describe('formatCityName', () => {
  it('should format city name to title case', () => {
    expect(formatCityName('miami beach')).toBe('Miami Beach');
    expect(formatCityName('coral gables')).toBe('Coral Gables');
    expect(formatCityName('MIAMI')).toBe('Miami');
  });

  it('should handle already formatted names', () => {
    expect(formatCityName('Miami Beach')).toBe('Miami Beach');
    expect(formatCityName('Coral Gables')).toBe('Coral Gables');
  });

  it('should trim whitespace', () => {
    expect(formatCityName('  miami beach  ')).toBe('Miami Beach');
    expect(formatCityName(' coral gables ')).toBe('Coral Gables');
  });

  it('should handle single word cities', () => {
    expect(formatCityName('miami')).toBe('Miami');
    expect(formatCityName('doral')).toBe('Doral');
  });

  it('should handle multiple words', () => {
    expect(formatCityName('north miami beach')).toBe('North Miami Beach');
    expect(formatCityName('key biscayne')).toBe('Key Biscayne');
  });

  it('should handle null input', () => {
    expect(formatCityName(null)).toBe(null);
  });

  it('should handle undefined input', () => {
    expect(formatCityName(undefined)).toBe(undefined);
  });

  it('should handle empty string', () => {
    expect(formatCityName('')).toBe('');
  });

  it('should handle non-string input', () => {
    expect(formatCityName(123)).toBe(123);
    expect(formatCityName({})).toEqual({});
  });

  it('should handle names with extra spaces', () => {
    expect(formatCityName('miami    beach')).toBe('Miami Beach');
    expect(formatCityName('coral   gables')).toBe('Coral Gables');
  });
});
