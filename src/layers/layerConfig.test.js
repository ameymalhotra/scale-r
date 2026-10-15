import { describe, expect, it } from 'vitest';
import {
  buildCategories,
  buildMapboxLayers,
  colorClasses,
  colorExpression,
  computeClasses,
  createLayer,
  describeLayerChanges,
  geojsonBounds,
  inspectGeojson,
  legendItems,
  normalizeLayerConfig,
  popupHtml,
  rampColors,
  symbolExpression,
  uniqueValues,
  validateLayerConfig,
} from './layerConfig.js';

const polygon = (props) => ({
  type: 'Feature',
  properties: props,
  geometry: { type: 'Polygon', coordinates: [[[-80.2, 25.7], [-80.1, 25.7], [-80.1, 25.8], [-80.2, 25.7]]] },
});

const point = (props, coords = [-80.19, 25.77]) => ({
  type: 'Feature',
  properties: props,
  geometry: { type: 'Point', coordinates: coords },
});

const fc = (features) => ({ type: 'FeatureCollection', features });

const baseLayer = (overrides = {}) =>
  createLayer({
    id: 'layer-abc',
    file: 'layers/layer-abc-x1.geojson',
    label: 'Flood depth',
    description: '',
    info: {
      geometry: 'polygon',
      featureCount: 3,
      fields: [
        { name: 'zone', type: 'string' },
        { name: 'depth', type: 'number' },
      ],
    },
    ...overrides,
  });

describe('inspectGeojson', () => {
  it('describes geometry, feature count and field types', () => {
    const info = inspectGeojson(
      fc([polygon({ zone: 'AE', depth: 2 }), polygon({ zone: 'X', depth: '3.5' }), polygon({ zone: 'VE', depth: null })]),
    );
    expect(info).toEqual({
      geometry: 'polygon',
      featureCount: 3,
      fields: [
        { name: 'zone', type: 'string' },
        { name: 'depth', type: 'number' },
      ],
    });
  });

  it('rejects files that are not one geometry type', () => {
    expect(() => inspectGeojson({ type: 'Feature' })).toThrow(/FeatureCollection/);
    expect(() => inspectGeojson(fc([]))).toThrow(/no features/);
    expect(() => inspectGeojson(fc([polygon({}), point({})]))).toThrow(/mixes polygons and points/);
    expect(() =>
      inspectGeojson(fc([{ type: 'Feature', properties: {}, geometry: { type: 'GeometryCollection', geometries: [] } }])),
    ).toThrow(/not supported/);
  });
});

describe('normalizeLayerConfig and validateLayerConfig', () => {
  it('drops malformed layers and unknown field references', () => {
    const layer = baseLayer();
    const config = normalizeLayerConfig({
      layers: [
        { ...layer, symbology: { ...layer.symbology, mode: 'graduated', field: 'missing' }, popup: { fields: ['zone', 'nope'] } },
        { ...layer, id: 'layer-abc' },
        { ...layer, id: 'bad id!' },
        { ...layer, id: 'layer-two', file: '../secret.geojson' },
      ],
    });
    expect(config.layers).toHaveLength(1);
    expect(config.layers[0].symbology.field).toBe('');
    expect(config.layers[0].popup.fields).toEqual(['zone']);
    expect(normalizeLayerConfig(null).layers).toEqual([]);
  });

  it('requires names, an attribute for data-driven modes, and numeric graduated fields', () => {
    const layer = baseLayer();
    const errors = validateLayerConfig({
      layers: [
        { ...layer, label: '' },
        { ...layer, id: 'layer-b', label: 'Same' },
        { ...layer, id: 'layer-c', label: 'same' },
        { ...layer, id: 'layer-d', label: 'Cat', symbology: { ...layer.symbology, mode: 'categorized', field: '' } },
        {
          ...layer,
          id: 'layer-e',
          label: 'Grad',
          symbology: { ...layer.symbology, mode: 'graduated', field: 'zone', classes: [{ min: 0, max: 1, color: '#000000' }] },
        },
      ],
    });
    expect(errors).toEqual([
      'A layer (layers/layer-abc-x1.geojson) has no name.',
      'Two layers are named "same".',
      '"Cat" needs an attribute to color by.',
      '"Grad" can only be graduated by a numeric attribute.',
    ]);
  });
});

describe('classes and colors', () => {
  it('computes quantile and equal-interval breaks', () => {
    const values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];
    expect(computeClasses(values, 'equal', 3)).toEqual([
      { min: 1, max: 4 },
      { min: 4, max: 7 },
      { min: 7, max: 10 },
    ]);
    expect(computeClasses(values, 'quantile', 2)).toEqual([
      { min: 1, max: 6 },
      { min: 6, max: 10 },
    ]);
    expect(computeClasses([5, 5, 5], 'quantile', 4)).toEqual([{ min: 5, max: 5 }]);
    expect(computeClasses([], 'equal', 4)).toEqual([]);
  });

  it('spreads ramp colors and keeps custom class labels', () => {
    expect(rampColors('blues', 2)).toEqual(['#eff3ff', '#08519c']);
    const classes = colorClasses([{ min: 0, max: 1 }, { min: 1, max: 2 }], 'reds', [{ min: 0, max: 1, label: 'Low' }]);
    expect(classes).toEqual([
      { min: 0, max: 1, color: '#fee5d9', label: 'Low' },
      { min: 1, max: 2, color: '#a50f15' },
    ]);
  });

  it('builds categories from values, keeping earlier choices', () => {
    const data = fc([polygon({ zone: 'AE' }), polygon({ zone: 'X' }), polygon({ zone: 'AE' })]);
    const values = uniqueValues(data, 'zone');
    expect(values).toEqual([
      { value: 'AE', count: 2 },
      { value: 'X', count: 1 },
    ]);
    const categories = buildCategories(values, [{ value: 'X', color: '#123456', label: 'Minimal' }]);
    expect(categories[1]).toEqual({ value: 'X', color: '#123456', label: 'Minimal' });
  });
});

describe('Mapbox output', () => {
  it('uses match for categorized and step for graduated colors', () => {
    const layer = baseLayer();
    const categorized = {
      ...layer,
      symbology: {
        ...layer.symbology,
        mode: 'categorized',
        field: 'zone',
        categories: [
          { value: 'AE', color: '#ff0000' },
          { value: 'X', color: '#00ff00' },
        ],
        otherColor: '#cccccc',
      },
    };
    expect(colorExpression(categorized)).toEqual([
      'match',
      ['to-string', ['get', 'zone']],
      'AE',
      '#ff0000',
      'X',
      '#00ff00',
      '#cccccc',
    ]);

    const graduated = {
      ...layer,
      symbology: {
        ...layer.symbology,
        mode: 'graduated',
        field: 'depth',
        classes: [
          { min: 0, max: 2, color: '#111111' },
          { min: 2, max: 5, color: '#222222' },
        ],
      },
    };
    expect(colorExpression(graduated)).toEqual([
      'case',
      ['==', ['get', 'depth'], null],
      graduated.symbology.otherColor,
      ['step', ['to-number', ['get', 'depth'], 0], '#111111', 2, '#222222'],
    ]);
  });

  it('builds fill and outline layers for polygons and symbol layers for points', () => {
    const layer = baseLayer();
    const specs = buildMapboxLayers(layer, 'src', 'none');
    expect(specs.map((s) => [s.id, s.type, s.layout.visibility])).toEqual([
      ['layer-abc-fill', 'fill', 'none'],
      ['layer-abc-outline', 'line', 'none'],
    ]);

    const pointLayer = {
      ...layer,
      geometry: 'point',
      style: { ...layer.style, symbol: 'star', pointSize: 18 },
      symbology: {
        ...layer.symbology,
        mode: 'categorized',
        field: 'zone',
        categories: [{ value: 'AE', color: '#ff0000', symbol: 'house' }],
      },
    };
    const [symbol] = buildMapboxLayers(pointLayer);
    expect(symbol.type).toBe('symbol');
    expect(symbol.layout['icon-size']).toBe(1);
    expect(symbolExpression(pointLayer)).toEqual([
      'match',
      ['to-string', ['get', 'zone']],
      'AE',
      'scaler-layer-symbol-house',
      'scaler-layer-symbol-star',
    ]);
  });

  it('lists legend rows for each mode', () => {
    const layer = baseLayer();
    expect(legendItems(layer)).toEqual([
      { key: 'single', label: 'Flood depth', color: layer.symbology.color, symbol: 'circle', kind: 'fill' },
    ]);
    const graduated = {
      ...layer,
      symbology: { ...layer.symbology, mode: 'graduated', field: 'depth', classes: [{ min: 0, max: 1500, color: '#111111' }] },
    };
    expect(legendItems(graduated)[0].label).toBe('0 – 1,500');
    const categorized = {
      ...layer,
      symbology: { ...layer.symbology, mode: 'categorized', field: 'zone', categories: [{ value: 'AE', color: '#ff0000', label: 'High risk' }], showOther: true },
    };
    expect(legendItems(categorized).map((r) => r.label)).toEqual(['High risk', 'Other']);
  });
});

describe('helpers', () => {
  it('escapes popup values', () => {
    const layer = { ...baseLayer(), popup: { titleField: 'zone', fields: ['depth'] } };
    const html = popupHtml(layer, { zone: '<b>AE</b>', depth: 3 });
    expect(html).toContain('&lt;b&gt;AE&lt;/b&gt;');
    expect(html).toContain('>3<');
    expect(popupHtml({ ...layer, popup: { titleField: '', fields: [] } }, {})).toBeNull();
  });

  it('computes bounds', () => {
    expect(geojsonBounds(fc([point({}, [-80, 25]), point({}, [-81, 26])]))).toEqual([
      [-81, 25],
      [-80, 26],
    ]);
    expect(geojsonBounds(fc([]))).toBeNull();
  });

  it('describes what a publish changes', () => {
    const live = { layers: [baseLayer()] };
    const next = {
      layers: [
        { ...live.layers[0], label: 'Depth', symbology: { ...live.layers[0].symbology, color: '#000000' } },
        { ...baseLayer({ id: 'layer-new' }), label: 'Surge' },
      ],
    };
    expect(describeLayerChanges(live, next)).toEqual([
      'Rename "Flood depth" to "Depth"',
      'Change the symbology of "Depth"',
      'Add the "Surge" layer',
    ]);
  });
});
