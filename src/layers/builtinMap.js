import { builtinDefinition, resilienceColorExpression } from './builtinRegistry.js';
import { colorExpression, normalizeLayerConfig } from './layerConfig.js';
import { symbolImageId } from './layerSymbols.js';

const defaults = normalizeLayerConfig(null);

export function builtinVectorSource(definition, origin) {
  return { type: 'vector', tiles: [`${origin.replace(/\/$/, '')}${definition.tiles}`], minzoom: definition.minzoom, maxzoom: definition.maxzoom, bounds: [-80.9, 25, -80.1, 26] };
}

export function overlayConfig(base, settings, groupOpacity = 1) {
  const initial = defaults.builtins.find((l) => l.id === settings.id);
  const originalSymbol = settings.geometry === 'point' && settings.style.symbol === initial.style.symbol && settings.symbology.color === initial.symbology.color && settings.style.outlineColor === initial.style.outlineColor && settings.style.outlineWidth === initial.style.outlineWidth;
  const color = colorExpression(settings);
  const opacity = settings.style.opacity * groupOpacity;
  let style;
  if (settings.geometry === 'point') {
    style = { type: 'symbol', iconImage: originalSymbol ? base.style.iconImage : symbolImageId(settings.style.symbol), iconSize: originalSymbol ? base.style.iconSize * settings.style.pointSize / initial.style.pointSize : settings.style.pointSize / 18,
      paint: originalSymbol ? { 'icon-opacity': opacity } : { 'icon-color': color, 'icon-opacity': opacity, 'icon-halo-color': settings.style.outlineColor, 'icon-halo-width': settings.style.outlineWidth } };
  } else if (settings.geometry === 'line') {
    style = { type: 'line', paint: { 'line-color': color, 'line-width': settings.style.lineWidth, 'line-opacity': opacity } };
  } else {
    style = { type: 'fill', paint: { 'fill-color': color, 'fill-opacity': opacity, 'fill-outline-color': 'transparent' } };
  }
  const outlinePaint = settings.geometry === 'polygon' ? { 'line-color': settings.style.outlineColor, 'line-width': settings.style.outlineWidth, 'line-opacity': opacity } : null;
  return { ...base, label: settings.label, settings, originalSymbol, style, outlinePaint };
}

export function applyOverlayStyle(map, config) {
  const id = `${config.id}-layer`;
  if (!map.getLayer(id)) return;
  for (const [key, value] of Object.entries(config.style.paint)) map.setPaintProperty(id, key, value);
  if (config.outlinePaint && map.getLayer(`${config.id}-outline`)) {
    for (const [key, value] of Object.entries(config.outlinePaint)) map.setPaintProperty(`${config.id}-outline`, key, value);
  }
  if (config.style.type === 'symbol') {
    map.setLayoutProperty(id, 'icon-image', config.style.iconImage);
    map.setLayoutProperty(id, 'icon-size', config.style.iconSize);
  }
}

export function builtinPreviewStats(layer, data) {
  if (layer.id !== 'pred3pe') return null;
  const values = data.features.map((f) => f.properties.__pred3PE).filter((v) => typeof v === 'number' && Number.isFinite(v));
  return values.length ? { min: Math.min(...values), max: Math.max(...values) } : null;
}

export function builtinColor(layer, stats) {
  return builtinDefinition(layer.id)?.id === 'pred3pe' ? resilienceColorExpression(layer, stats) : colorExpression(layer);
}
