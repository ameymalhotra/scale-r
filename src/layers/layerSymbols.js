/**
 * Point symbols for uploaded layers. Each symbol is one SVG path in a 24×24
 * box: the admin page and the map legend draw it as SVG, and the map registers
 * it as a signed-distance-field image so `icon-color` and `icon-halo-*` can
 * recolor it per feature.
 */

function polygonPath(points) {
  return `M${points.map(([x, y]) => `${x.toFixed(2)} ${y.toFixed(2)}`).join('L')}Z`;
}

function starPath(cx, cy, outer, inner, spikes = 5) {
  const points = [];
  for (let i = 0; i < spikes * 2; i += 1) {
    const r = i % 2 === 0 ? outer : inner;
    const a = (Math.PI * i) / spikes - Math.PI / 2;
    points.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]);
  }
  return polygonPath(points);
}

function regularPath(cx, cy, r, sides, rotation = 0) {
  return polygonPath(
    Array.from({ length: sides }, (_, i) => {
      const a = rotation + (2 * Math.PI * i) / sides;
      return [cx + r * Math.cos(a), cy + r * Math.sin(a)];
    }),
  );
}

export const LAYER_SYMBOLS = [
  { id: 'circle', label: 'Circle', path: 'M3 12a9 9 0 1 0 18 0a9 9 0 1 0 -18 0Z' },
  { id: 'square', label: 'Square', path: 'M4 4h16v16H4Z' },
  { id: 'triangle', label: 'Triangle', path: 'M12 2.5L21.5 20H2.5Z' },
  { id: 'diamond', label: 'Diamond', path: 'M12 2L22 12L12 22L2 12Z' },
  { id: 'star', label: 'Star', path: starPath(12, 12.6, 10.5, 4.4) },
  { id: 'hexagon', label: 'Hexagon', path: regularPath(12, 12, 9.8, 6, Math.PI / 6) },
  { id: 'cross', label: 'Medical cross', path: 'M9 3h6v6h6v6h-6v6H9v-6H3V9h6Z' },
  { id: 'x', label: 'X', path: 'M5.6 3.4L12 9.8l6.4-6.4l2.2 2.2L14.2 12l6.4 6.4l-2.2 2.2L12 14.2l-6.4 6.4l-2.2-2.2L9.8 12L3.4 5.6Z' },
  {
    id: 'pin',
    label: 'Pin',
    path: 'M12 1.5a7.5 7.5 0 0 0-7.5 7.5c0 5.6 7.5 13.5 7.5 13.5s7.5-7.9 7.5-13.5a7.5 7.5 0 0 0-7.5-7.5Zm0 4.6a2.9 2.9 0 1 1 0 5.8a2.9 2.9 0 1 1 0-5.8Z',
  },
  { id: 'house', label: 'Shelter (house)', path: 'M12 2.5L1.5 11.5h3V21h5.5v-6h4v6h5.5v-9.5h3Z' },
  {
    id: 'people',
    label: 'Community',
    path: 'M8 4a3 3 0 1 1 0 6a3 3 0 1 1 0-6Zm8 0a3 3 0 1 1 0 6a3 3 0 1 1 0-6ZM2.5 20v-3.5c0-2.5 2.5-4.5 5.5-4.5s5.5 2 5.5 4.5V20Zm11.5 0v-3.5c0-1.4-.5-2.6-1.4-3.6c1-.6 2.1-.9 3.4-.9c3 0 5.5 2 5.5 4.5V20Z',
  },
];

export const SYMBOL_IDS = LAYER_SYMBOLS.map((s) => s.id);
const BY_ID = new Map(LAYER_SYMBOLS.map((s) => [s.id, s]));
export const symbolPath = (id) => (BY_ID.get(id) ?? LAYER_SYMBOLS[0]).path;
export const symbolImageId = (id) => `scaler-layer-symbol-${BY_ID.has(id) ? id : 'circle'}`;

const IMAGE_SIZE = 64;
const PIXEL_RATIO = 64 / 24;
const PADDING = 8;
const SDF_RADIUS = 8;

/**
 * Renders a symbol as SDF image data: alpha 192 on the edge, rising inside and
 * falling outside by 24 per pixel, which is what Mapbox expects for sdf icons.
 */
function renderSdf(path) {
  if (typeof document === 'undefined' || typeof Path2D === 'undefined') return null;
  const canvas = document.createElement('canvas');
  canvas.width = IMAGE_SIZE;
  canvas.height = IMAGE_SIZE;
  let ctx;
  try {
    ctx = canvas.getContext('2d');
  } catch {
    return null;
  }
  if (!ctx) return null;
  const scale = (IMAGE_SIZE - PADDING * 2) / 24;
  ctx.translate(PADDING, PADDING);
  ctx.scale(scale, scale);
  ctx.fillStyle = '#000';
  ctx.fill(new Path2D(path), 'evenodd');
  const mask = ctx.getImageData(0, 0, IMAGE_SIZE, IMAGE_SIZE).data;
  const inside = (x, y) => mask[(y * IMAGE_SIZE + x) * 4 + 3] > 127;

  const out = new Uint8ClampedArray(IMAGE_SIZE * IMAGE_SIZE * 4);
  for (let y = 0; y < IMAGE_SIZE; y += 1) {
    for (let x = 0; x < IMAGE_SIZE; x += 1) {
      const self = inside(x, y);
      let best = SDF_RADIUS;
      for (let dy = -SDF_RADIUS; dy <= SDF_RADIUS; dy += 1) {
        const yy = y + dy;
        if (yy < 0 || yy >= IMAGE_SIZE) continue;
        for (let dx = -SDF_RADIUS; dx <= SDF_RADIUS; dx += 1) {
          const xx = x + dx;
          if (xx < 0 || xx >= IMAGE_SIZE || inside(xx, yy) === self) continue;
          const d = Math.sqrt(dx * dx + dy * dy);
          if (d < best) best = d;
        }
      }
      const signed = self ? best - 0.5 : -(best - 0.5);
      const i = (y * IMAGE_SIZE + x) * 4;
      out[i] = 255;
      out[i + 1] = 255;
      out[i + 2] = 255;
      out[i + 3] = Math.max(0, Math.min(255, 192 + signed * 24));
    }
  }
  return { width: IMAGE_SIZE, height: IMAGE_SIZE, data: out };
}

const imageCache = new Map();

/** Adds every layer symbol to a Mapbox map that does not have it yet. */
export function registerLayerSymbols(map) {
  for (const symbol of LAYER_SYMBOLS) {
    const id = symbolImageId(symbol.id);
    if (map.hasImage(id)) continue;
    if (!imageCache.has(symbol.id)) imageCache.set(symbol.id, renderSdf(symbol.path));
    const image = imageCache.get(symbol.id);
    if (!image) continue;
    try {
      map.addImage(id, image, { sdf: true, pixelRatio: PIXEL_RATIO });
    } catch (e) {
      console.warn('[Layers] addImage failed', id, e);
    }
  }
}
