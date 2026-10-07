import { describe, expect, it } from 'vitest';
import {
  DEFAULT_FILTER_CONFIG,
  compactOptions,
  countFilterValues,
  mapOptions,
  normalizeFilterConfig,
  optionKey,
  resolveOptions,
  sameSettings,
  validateFilterConfig,
} from './filterConfig.js';

const infra = (options) => ({ id: 'infrastructure', label: 'Infrastructure Type', visible: true, options });

describe('optionKey', () => {
  it('matches values the map treats as the same option', () => {
    expect(optionKey('infrastructure', 'Blue Infrastructure')).toBe(optionKey('infrastructure', 'blue'));
    expect(optionKey('infrastructure', 'Grey')).toBe('gray');
    expect(optionKey('disaster', 'Storms')).toBe(optionKey('disaster', 'Storms & Hurricanes'));
    expect(optionKey('city', ' MIAMI BEACH ')).toBe('miami beach');
    expect(optionKey('status', '')).toBe('');
  });
});

describe('normalizeFilterConfig', () => {
  it('falls back to the defaults for anything unusable', () => {
    expect(normalizeFilterConfig(null)).toEqual(DEFAULT_FILTER_CONFIG);
    expect(normalizeFilterConfig({ filters: 'nope' })).toEqual(DEFAULT_FILTER_CONFIG);
  });

  it('keeps order, drops bad entries and re-adds missing built-in filters', () => {
    const config = normalizeFilterConfig({
      filters: [
        { id: 'disaster', label: 'Hazard', visible: false, options: [{ value: 'Flooding', label: 'Floods' }, { value: '' }] },
        { id: 'custom-1', label: 'Year', column: 'project_st', options: [] },
        { id: 'custom-2', label: 'Bad column', column: 'latitude', options: [] },
        { id: 'custom-3', label: 'Same column', column: 'project_st', options: [] },
        { id: 'status', options: [{ value: 'Completed', color: 'red' }, { value: 'completed' }] },
      ],
    });
    expect(config.filters.map((f) => f.id)).toEqual(['disaster', 'custom-1', 'status', 'city', 'infrastructure']);
    expect(config.filters[0]).toEqual({
      id: 'disaster',
      label: 'Hazard',
      visible: false,
      options: [{ value: 'Flooding', label: 'Floods', visible: true }],
    });
    expect(config.filters[1].column).toBe('project_st');
    expect(config.filters[2].label).toBe('Project Status');
    expect(config.filters[2].options).toEqual([{ value: 'Completed', visible: true }]);
  });
});

describe('resolveOptions', () => {
  const data = [
    { value: 'Blue Infrastructure', count: 10 },
    { value: 'Gray Infrastructure', count: 4 },
    { value: 'Living Shoreline', count: 1 },
  ];

  it('lists configured values in their order, then new values from the data', () => {
    const options = resolveOptions(
      infra([
        { value: 'Gray', label: 'Gray (engineered)', color: '#111111', visible: true },
        { value: 'Blue', visible: false },
        { value: 'Hybrid', visible: true },
      ]),
      data,
    );
    expect(options.map((o) => [o.label, o.visible, o.inData, o.configured, o.count])).toEqual([
      ['Gray (engineered)', true, true, true, 4],
      ['Blue', false, true, true, 10],
      ['Hybrid', true, false, true, 0],
      ['Living Shoreline', true, true, false, 1],
    ]);
    expect(options[0].value).toBe('Gray Infrastructure');
    expect(options[0].color).toBe('#111111');
    expect(options[3].color).toBe('#95a5a6');
  });

  it('mapOptions keeps only shown values that exist in the data', () => {
    const options = mapOptions(infra([{ value: 'Blue', visible: false }, { value: 'Hybrid' }]), data);
    expect(options.map((o) => o.label)).toEqual(['Gray', 'Living Shoreline']);
  });
});

describe('countFilterValues', () => {
  const row = (extra) => ({ latitude: 25.7, longitude: -80.2, estimated_cost: 100, ...extra });

  it('counts only projects the map shows, grouped like the map groups them', () => {
    const rows = [
      row({ infrastruc: 'Blue Infrastructure' }),
      row({ infrastruc: 'blue' }),
      row({ infrastruc: 'Hybrid' }),
      row({ infrastruc: 'Hybrid', estimated_cost: 0 }),
      row({ infrastruc: 'Green Infrastructure', latitude: 0, longitude: 0 }),
      row({ infrastruc: null }),
    ];
    expect(countFilterValues(infra([]), rows)).toEqual([
      { value: 'Blue Infrastructure', count: 2 },
      { value: 'Hybrid', count: 1 },
    ]);
  });

  it('treats a blank status as Ongoing and reads custom columns', () => {
    const rows = [row({ project_status: null }), row({ project_status: 'Completed', project_st: '2020' })];
    expect(countFilterValues({ id: 'status', options: [] }, rows)).toEqual([
      { value: 'Completed', count: 1 },
      { value: 'Ongoing', count: 1 },
    ]);
    expect(countFilterValues({ id: 'c', column: 'project_st', options: [] }, rows)).toEqual([
      { value: '2020', count: 1 },
    ]);
  });
});

describe('validateFilterConfig', () => {
  it('requires at least one shown filter and valid colors', () => {
    expect(validateFilterConfig(normalizeFilterConfig(null))).toEqual([]);
    const hidden = normalizeFilterConfig(null);
    hidden.filters.forEach((f) => (f.visible = false));
    expect(validateFilterConfig(hidden)).toContain('At least one filter must be shown on the map.');
    const badColor = normalizeFilterConfig(null);
    badColor.filters[1].options[0].color = 'green';
    expect(validateFilterConfig(badColor)[0]).toMatch(/invalid color/);
  });
});

describe('sameSettings', () => {
  it('ignores key order but not values', () => {
    expect(sameSettings({ value: 'Blue', visible: true, label: 'B' }, { label: 'B', value: 'Blue', visible: true })).toBe(true);
    expect(sameSettings([{ value: 'Blue', visible: true }], [{ value: 'Blue', visible: false }])).toBe(false);
    expect(sameSettings({ filters: [{ id: 'a' }, { id: 'b' }] }, { filters: [{ id: 'b' }, { id: 'a' }] })).toBe(false);
  });
});

describe('compactOptions', () => {
  const city = (options) => ({ id: 'city', label: 'City', visible: true, options });
  const data = [{ value: 'Doral', count: 1 }, { value: 'Hialeah', count: 1 }, { value: 'Miami', count: 1 }];

  it('drops trailing settings that change nothing', () => {
    const toggledBack = city([
      { value: 'Doral', visible: true },
      { value: 'Hialeah', visible: true },
    ]);
    expect(compactOptions(toggledBack, data).options).toEqual([]);
  });

  it('keeps settings that change the map or belong to the live filter', () => {
    const hidden = city([{ value: 'Doral', visible: true }, { value: 'Hialeah', visible: false }]);
    expect(compactOptions(hidden, data).options).toHaveLength(2);
    const moved = city([{ value: 'Miami', visible: true }]);
    expect(compactOptions(moved, data).options).toHaveLength(1);
    const live = city([{ value: 'Doral', visible: true }]);
    expect(compactOptions(live, data, new Set(['doral'])).options).toHaveLength(1);
  });
});
