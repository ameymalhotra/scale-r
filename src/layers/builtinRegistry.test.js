import { describe, expect, it } from 'vitest';
import { builtinDefinition, modellingOptions, resilienceColorExpression } from './builtinRegistry.js';
import { applyOverlayStyle, overlayConfig } from './builtinMap.js';
import { cloneConfig, describeLayerChanges, normalizeLayerConfig, popupHtml, validateLayerConfig } from './layerConfig.js';

describe('published built-in layer controls', () => {
  it('supplies requested surfaces and overlay controls for old configs', () => {
    const config = normalizeLayerConfig({ layers: [] });
    expect(validateLayerConfig(config)).toEqual([]);
    expect(config.builtins).toHaveLength(13);
    expect(modellingOptions(config).map((l) => l.view)).toEqual(['none', 'risk', 'pred3pe', 'critical-infrastructure', 'custom:sea-level-rise-4ft', 'custom:storm-surge-category-3', 'custom:elevation']);
    expect(config.overlayOrder).toHaveLength(7);
  });
  it('preserves settings while locking sources and scientific classes', () => {
    const config = normalizeLayerConfig(null);
    const risk = config.builtins.find((l) => l.id === 'risk');
    risk.label = 'County Risk'; risk.visible = false; risk.style.opacity = 0.25;
    risk.file = 'layers/wrong.geojson'; risk.geometry = 'point'; risk.symbology.mode = 'single';
    risk.symbology.categories[0].color = '#123456'; risk.symbology.categories[0].label = 'Lowest risk';
    risk.popup.fields = ['__riskRating', 'not-an-attribute'];
    config.order = ['elevation', 'risk', 'elevation', 'unknown']; config.overlayOrder = ['overlay-military', 'risk'];
    const restored = normalizeLayerConfig(JSON.parse(JSON.stringify(config)));
    const saved = restored.builtins.find((l) => l.id === 'risk');
    expect(saved).toMatchObject({ label: 'County Risk', visible: false, geometry: 'polygon', file: builtinDefinition('risk').file, style: { opacity: 0.25 }, symbology: { mode: 'categorized' }, popup: { fields: ['__riskRating'] } });
    expect(saved.symbology.categories[0]).toEqual({ value: 'Very Low', label: 'Lowest risk', color: '#123456' });
    expect(modellingOptions(restored).map((l) => l.view)).not.toContain('risk');
    expect(modellingOptions(restored)[1].view).toBe('custom:elevation');
    expect(restored.overlayOrder[0]).toBe('overlay-military'); expect(restored.overlayOrder).not.toContain('risk');
  });
  it('includes built-in edits in publish diffs and restores versions exactly', () => {
    const live = normalizeLayerConfig(null), draft = cloneConfig(live);
    const elevation = draft.builtins.find((l) => l.id === 'elevation');
    elevation.visible = false; elevation.symbology.categories[0].color = '#000000'; draft.order.reverse();
    expect(describeLayerChanges(live, draft)).toContain('Hide the "Elevation" layer');
    expect(describeLayerChanges(live, draft)).toContain('Change modelling switch order');
    expect(normalizeLayerConfig(JSON.parse(JSON.stringify(draft)))).toEqual(draft);
  });
  it('retains scientific surge classifications and elevation references', () => {
    const config = normalizeLayerConfig(null), surge = config.builtins.find((l) => l.id === 'storm-surge-category-3');
    expect(surge.symbology.categories).toHaveLength(22);
    expect(surge.symbology.categories.at(-1).value).toContain('hazard not assessed');
    const elevation = config.builtins.find((l) => l.id === 'elevation');
    expect(popupHtml(elevation, { elevation_band: '2–4 ft', vertical_datum: 'NAVD88', units: 'feet' })).toContain('NAVD88');
  });
  it('recolors resilience interpolation without changing its data range', () => {
    const layer = normalizeLayerConfig(null).builtins.find((l) => l.id === 'pred3pe');
    layer.symbology.categories[0].color = '#000000';
    const expression = resilienceColorExpression(layer, { min: 8, max: 38 });
    expect(expression[2].slice(3, 5)).toEqual([8, '#000000']); expect(expression[2].at(-2)).toBe(38);
    expect(resilienceColorExpression(layer, { min: 8, max: 8 })[2]).toBe('#2d0045');
    expect(resilienceColorExpression(layer, { min: null })).toBe('#9e9e9e');
  });
  it('preserves legacy point symbols until edited and applies group opacity', () => {
    const settings = normalizeLayerConfig(null).builtins.find((l) => l.id === 'overlay-community-centers');
    const base = { id: settings.id, style: { type: 'symbol', iconImage: 'original-symbol', iconSize: 0.42 } };
    expect(overlayConfig(base, settings).style.iconImage).toBe('original-symbol');
    settings.style.opacity = 0.5; settings.symbology.color = '#123456';
    const rendered = overlayConfig(base, settings, 0.4);
    expect(rendered.style.paint).toMatchObject({ 'icon-opacity': 0.2, 'icon-color': '#123456' });
    const properties = {};
    applyOverlayStyle({ getLayer: () => true, setPaintProperty: (_, k, v) => { properties[k] = v; }, setLayoutProperty: (_, k, v) => { properties[k] = v; } }, rendered);
    expect(properties['icon-color']).toBe('#123456'); expect(properties['icon-image']).toBe('scaler-layer-symbol-people');
  });
  it('applies polygon outline width and color independently of its fill', () => {
    const settings = normalizeLayerConfig(null).builtins.find((l) => l.id === 'overlay-military');
    settings.style.outlineWidth = 4; settings.style.outlineColor = '#123456';
    const config = overlayConfig({ id: settings.id }, settings, 0.5);
    const paint = {};
    applyOverlayStyle({ getLayer: () => true, setPaintProperty: (id, key, value) => { paint[`${id}:${key}`] = value; } }, config);
    expect(paint['overlay-military-outline:line-width']).toBe(4);
    expect(paint['overlay-military-outline:line-color']).toBe('#123456');
    expect(paint['overlay-military-outline:line-opacity']).toBe(0.21);
  });
});
