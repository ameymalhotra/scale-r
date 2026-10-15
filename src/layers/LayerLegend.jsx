import React from 'react';
import { legendItems } from './layerConfig.js';
import { symbolPath } from './layerSymbols.js';

/** One legend glyph: a filled swatch, a line, or a point symbol. */
export function LegendGlyph({ kind, color, symbol, outlineColor, size = 16 }) {
  if (kind === 'line') {
    return (
      <svg width={size} height={size} viewBox="0 0 16 16" aria-hidden="true" style={{ flexShrink: 0 }}>
        <path d="M1 12C5 4 10 14 15 4" fill="none" stroke={color} strokeWidth="3" strokeLinecap="round" />
      </svg>
    );
  }
  if (kind === 'point') {
    return (
      <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true" style={{ flexShrink: 0 }}>
        <path d={symbolPath(symbol)} fill={color} fillRule="evenodd" stroke={outlineColor} strokeWidth="1" />
      </svg>
    );
  }
  return (
    <span
      aria-hidden="true"
      style={{
        display: 'inline-block',
        flexShrink: 0,
        width: size,
        height: size,
        borderRadius: 3,
        background: color,
        border: `1px solid ${outlineColor}`,
        boxSizing: 'border-box',
      }}
    />
  );
}

/** Legend rows for an uploaded layer, shared by /admin/layers and the public map. */
export default function LayerLegend({ layer, fontSize = '0.82em', textColor = '#1b3a4b' }) {
  const items = legendItems(layer);
  return (
    <ul style={{ listStyle: 'none', margin: 0, padding: 0 }}>
      {items.map((item) => (
        <li
          key={item.key}
          style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, fontSize, color: textColor }}
        >
          <LegendGlyph
            kind={item.kind}
            color={item.color}
            symbol={item.symbol}
            outlineColor={layer.style.outlineWidth > 0 ? layer.style.outlineColor : 'transparent'}
          />
          <span style={{ minWidth: 0, overflowWrap: 'anywhere' }}>{item.label}</span>
        </li>
      ))}
    </ul>
  );
}
